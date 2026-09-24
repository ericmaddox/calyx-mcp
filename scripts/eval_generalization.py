#!/usr/bin/env python3
"""
Generalization Evaluation Harness for Calyx MCP.
Measures generalization, false-positive resistance, and contradiction guards across
diverse code mutations and languages in strictly isolated storage environments.

================================================================================
PRE-REGISTERED EVALUATION TARGETS (Defined prior to Phase 1 test run):
  * Variant Recall Target:              >= 80.0%  (Variants triggering 'avoid')
  * Fixed-Code False-Positive Rate:     <= 10.0%  (Fixed code triggering 'avoid')
  * Unrelated-Snippet False-Positive:   <=  5.0%  (Unrelated code triggering 'avoid')
================================================================================
"""

import sys
import os
import json
import time
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, List
import numpy as np

# Ensure src is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from calyx_mcp.config import CalyxConfig
from calyx_mcp.server import CalyxMCPServer

# Pre-registered evaluation criteria
PRE_REGISTERED_TARGETS = {
    "variant_recall_min": 0.80,
    "fixed_fpr_max": 0.10,
    "unrelated_fpr_max": 0.05,
}


async def evaluate_single_case(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates a single bug-fix case in a dedicated, isolated temporary storage directory.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        cfg = CalyxConfig()
        cfg.storage.storage_dir = tmp_dir
        server = CalyxMCPServer(cfg)

        # 1. Train negative valence on bug
        bug_train_res = await server.execute_tool(
            "remember_code_outcome",
            {
                "code": case["bug_code"],
                "outcome": "failure",
                "error_message": case.get("description", "Vulnerability pattern"),
            },
        )

        # 2. Train positive valence on fix
        fix_train_res = await server.execute_tool(
            "remember_code_outcome",
            {
                "code": case["fix_code"],
                "outcome": "success",
            },
        )

        # 3. Evaluate each variant (measuring recall of 'avoid')
        variant_evals = []
        variant_labels = ["rename", "reorder", "restructure"]
        for idx, var_code in enumerate(case["variants"]):
            t0 = time.perf_counter()
            reflex = await server.execute_tool("check_code_reflex", {"code": var_code})
            latency_ms = (time.perf_counter() - t0) * 1000.0

            label = variant_labels[idx] if idx < len(variant_labels) else f"variant_{idx+1}"
            variant_evals.append({
                "label": label,
                "status": reflex["status"],
                "valence": reflex["valence"],
                "similarity": reflex["similarity_with_past_bugs"],
                "confidence": reflex["confidence"],
                "latency_ms": latency_ms,
            })

        # 4. Evaluate fixed code (measuring FPR - should NOT be 'avoid')
        t0 = time.perf_counter()
        fix_reflex = await server.execute_tool("check_code_reflex", {"code": case["fix_code"]})
        fix_latency_ms = (time.perf_counter() - t0) * 1000.0
        fix_eval = {
            "status": fix_reflex["status"],
            "valence": fix_reflex["valence"],
            "similarity": fix_reflex["similarity_with_past_bugs"],
            "confidence": fix_reflex["confidence"],
            "latency_ms": fix_latency_ms,
        }

        # 5. Evaluate unrelated negative controls (measuring FPR - should NOT be 'avoid')
        unrelated_evals = []
        for un_code in case.get("unrelated_snippets", []):
            t0 = time.perf_counter()
            un_reflex = await server.execute_tool("check_code_reflex", {"code": un_code})
            un_latency_ms = (time.perf_counter() - t0) * 1000.0
            unrelated_evals.append({
                "status": un_reflex["status"],
                "valence": un_reflex["valence"],
                "similarity": un_reflex["similarity_with_past_bugs"],
                "confidence": un_reflex["confidence"],
                "latency_ms": un_latency_ms,
            })

        return {
            "id": case["id"],
            "language": case.get("language", "unknown"),
            "cwe_or_tag": case.get("cwe_or_tag", "UNKNOWN"),
            "description": case.get("description", ""),
            "variants": variant_evals,
            "fix": fix_eval,
            "unrelated": unrelated_evals,
        }


async def run_full_evaluation(dataset_path: Path, output_dir: Path) -> Dict[str, Any]:
    print("=" * 80)
    print("Calyx MCP Generalization & Contradiction Evaluation Runner")
    print(f"Dataset: {dataset_path}")
    print(f"Pre-registered Targets: Recall >= {PRE_REGISTERED_TARGETS['variant_recall_min']*100:.1f}%, "
          f"Fix FPR <= {PRE_REGISTERED_TARGETS['fixed_fpr_max']*100:.1f}%, "
          f"Unrelated FPR <= {PRE_REGISTERED_TARGETS['unrelated_fpr_max']*100:.1f}%")
    print("=" * 80)

    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(cases)} test cases.")

    case_results = []
    for idx, case in enumerate(cases, 1):
        res = await evaluate_single_case(case)
        case_results.append(res)
        if idx % 10 == 0 or idx == len(cases):
            print(f"Processed {idx}/{len(cases)} cases...")

    output_dir.mkdir(parents=True, exist_ok=True)
    results_jsonl = output_dir / "generalization_results.jsonl"
    with open(results_jsonl, "w", encoding="utf-8") as f:
        for r in case_results:
            f.write(json.dumps(r) + "\n")

    # Aggregate Statistics
    total_variants = sum(len(c["variants"]) for c in case_results)
    avoid_variants = sum(sum(1 for v in c["variants"] if v["status"] == "avoid") for c in case_results)
    variant_recall = avoid_variants / float(total_variants) if total_variants > 0 else 0.0

    total_fixes = len(case_results)
    avoid_fixes = sum(1 for c in case_results if c["fix"]["status"] == "avoid")
    fixed_fpr = avoid_fixes / float(total_fixes) if total_fixes > 0 else 0.0

    total_unrelated = sum(len(c["unrelated"]) for c in case_results)
    avoid_unrelated = sum(sum(1 for u in c["unrelated"] if u["status"] == "avoid") for c in case_results)
    unrelated_fpr = avoid_unrelated / float(total_unrelated) if total_unrelated > 0 else 0.0

    # Variant types breakdown
    by_variant_type = {"rename": {"total": 0, "avoid": 0},
                       "reorder": {"total": 0, "avoid": 0},
                       "restructure": {"total": 0, "avoid": 0}}
    for c in case_results:
        for v in c["variants"]:
            lbl = v["label"]
            if lbl in by_variant_type:
                by_variant_type[lbl]["total"] += 1
                if v["status"] == "avoid":
                    by_variant_type[lbl]["avoid"] += 1

    # Language breakdown
    by_lang = {}
    for c in case_results:
        lang = c["language"]
        if lang not in by_lang:
            by_lang[lang] = {"total_v": 0, "avoid_v": 0, "total_fix": 0, "avoid_fix": 0}
        for v in c["variants"]:
            by_lang[lang]["total_v"] += 1
            if v["status"] == "avoid":
                by_lang[lang]["avoid_v"] += 1
        by_lang[lang]["total_fix"] += 1
        if c["fix"]["status"] == "avoid":
            by_lang[lang]["avoid_fix"] += 1

    # Latencies
    all_latencies = []
    for c in case_results:
        for v in c["variants"]:
            all_latencies.append(v["latency_ms"])
        all_latencies.append(c["fix"]["latency_ms"])
        for u in c["unrelated"]:
            all_latencies.append(u["latency_ms"])

    lat_p50 = float(np.percentile(all_latencies, 50))
    lat_p90 = float(np.percentile(all_latencies, 90))
    lat_p99 = float(np.percentile(all_latencies, 99))

    # Similarities
    var_sims = [v["similarity"] for c in case_results for v in c["variants"]]
    fix_sims = [c["fix"]["similarity"] for c in case_results]
    un_sims = [u["similarity"] for c in case_results for u in c["unrelated"]]

    print("\n" + "=" * 80)
    print("GENERALIZATION EVALUATION RESULTS")
    print("=" * 80)
    print(f"Total Cases:                   {len(case_results)}")
    print(f"Total Variant Snippets:        {total_variants}")
    print(f"Total Negative Controls:       {total_unrelated}")
    print("-" * 80)
    print(f"Variant Recall (Avoid Rate):   {variant_recall*100:.2f}%  (Target: >= {PRE_REGISTERED_TARGETS['variant_recall_min']*100:.1f}%)"
          f" [{'PASS' if variant_recall >= PRE_REGISTERED_TARGETS['variant_recall_min'] else 'FAIL'}]")
    print(f"Fixed Code FPR:                {fixed_fpr*100:.2f}%  (Target: <= {PRE_REGISTERED_TARGETS['fixed_fpr_max']*100:.1f}%)"
          f" [{'PASS' if fixed_fpr <= PRE_REGISTERED_TARGETS['fixed_fpr_max'] else 'FAIL'}]")
    print(f"Unrelated Snippet FPR:         {unrelated_fpr*100:.2f}%  (Target: <= {PRE_REGISTERED_TARGETS['unrelated_fpr_max']*100:.1f}%)"
          f" [{'PASS' if unrelated_fpr <= PRE_REGISTERED_TARGETS['unrelated_fpr_max'] else 'FAIL'}]")

    print("\nVariant Paraphrase Breakdown:")
    for vtype, stats in by_variant_type.items():
        rate = (stats["avoid"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"  * {vtype:<12}: {stats['avoid']}/{stats['total']} ({rate:.1f}% avoid)")

    print("\nLanguage Breakdown:")
    for lang, stats in by_lang.items():
        v_rate = (stats["avoid_v"] / stats["total_v"]) * 100 if stats["total_v"] > 0 else 0
        f_rate = (stats["avoid_fix"] / stats["total_fix"]) * 100 if stats["total_fix"] > 0 else 0
        print(f"  * {lang:<12}: Recall {stats['avoid_v']}/{stats['total_v']} ({v_rate:.1f}%), Fix FPR {stats['avoid_fix']}/{stats['total_fix']} ({f_rate:.1f}%)")

    print("\nSimilarity Distributions (Jaccard):")
    print(f"  * Variants:   mean={np.mean(var_sims):.3f}, med={np.median(var_sims):.3f}, p25={np.percentile(var_sims, 25):.3f}, p75={np.percentile(var_sims, 75):.3f}, max={np.max(var_sims):.3f}")
    print(f"  * Fixed Code: mean={np.mean(fix_sims):.3f}, med={np.median(fix_sims):.3f}, p25={np.percentile(fix_sims, 25):.3f}, p75={np.percentile(fix_sims, 75):.3f}, max={np.max(fix_sims):.3f}")
    print(f"  * Unrelated:  mean={np.mean(un_sims):.3f}, med={np.median(un_sims):.3f}, max={np.max(un_sims):.3f}")

    print("\nLatency (ms):")
    print(f"  * p50: {lat_p50:.3f} ms | p90: {lat_p90:.3f} ms | p99: {lat_p99:.3f} ms")

    # README Scenarios Check
    print("\n" + "=" * 80)
    print("README Claim Reproduction Check:")
    print("=" * 80)
    readme_ids = ["cwe-89-sqli-py-01", "cwe-775-fd-leak-py-02", "cwe-835-spinlock-py-03"]
    readme_results = []
    for c in case_results:
        if c["id"] in readme_ids:
            readme_results.append(c)
            print(f"Scenario: {c['id']} - {c['description']}")
            print(f"  Fix: status={c['fix']['status']}, valence={c['fix']['valence']}, sim={c['fix']['similarity']:.3f}")
            for v in c["variants"]:
                print(f"  Variant [{v['label']}]: status={v['status']}, valence={v['valence']}, sim={v['similarity']:.3f}, lat={v['latency_ms']:.3f}ms")

    summary = {
        "dataset": str(dataset_path),
        "total_cases": len(case_results),
        "total_variants": total_variants,
        "total_unrelated": total_unrelated,
        "variant_recall": variant_recall,
        "fixed_fpr": fixed_fpr,
        "unrelated_fpr": unrelated_fpr,
        "targets": PRE_REGISTERED_TARGETS,
        "by_variant_type": by_variant_type,
        "by_lang": by_lang,
        "latencies": {"p50": lat_p50, "p90": lat_p90, "p99": lat_p99},
        "similarities": {
            "variant_mean": float(np.mean(var_sims)),
            "fix_mean": float(np.mean(fix_sims)),
            "unrelated_mean": float(np.mean(un_sims)),
        },
        "readme_scenarios": readme_results,
    }

    summary_file = output_dir / "eval_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote results to {results_jsonl} and summary to {summary_file}")

    return summary


def main():
    dataset_path = Path("tests/eval/generalization_cases.jsonl")
    output_dir = Path("benchmarks/2026-09-eval")
    asyncio.run(run_full_evaluation(dataset_path, output_dir))


if __name__ == "__main__":
    main()
