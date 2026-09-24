#!/usr/bin/env python3
"""
Phase 5(a) Tokenizer Reform Experiment.
Tests whether identifier abstraction improves variant recall without blowing unrelated FPR.
"""

import sys
import json
import re
import ast
import zlib
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from calyx_mcp.hasher import FlyLSHHasher, KenyonSparseRepresentation
from calyx_mcp.config import HasherConfig

COMMON_SINKS_AND_KEYWORDS = {
    "def", "class", "return", "if", "else", "elif", "for", "while", "in", "is",
    "try", "except", "finally", "with", "as", "import", "from", "lambda",
    "async", "await", "yield", "pass", "raise", "break", "continue",
    "true", "false", "none", "null", "undefined",
    "select", "from", "where", "insert", "update", "delete", "join", "table",
    "execute", "executesql", "query", "raw", "open", "read", "write", "close",
    "system", "popen", "check_output", "exec", "eval", "spawn",
    "socket", "connect", "listen", "send", "recv",
    "function", "const", "let", "var", "fn", "let", "mut", "func",
}

class AbstractedFlyLSHHasher(FlyLSHHasher):
    def extract_features(self, code: str) -> np.ndarray:
        tokens = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                node_type = type(node).__name__
                tokens.append((f"ast:{node_type}", 2.0))
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        tokens.append((f"call:{node.func.id}", 2.5))
                    elif isinstance(node.func, ast.Attribute):
                        tokens.append((f"call_attr:{node.func.attr}", 2.5))
        except Exception:
            pass

        raw_words = re.findall(r'[A-Za-z_][A-Za-z0-9_]*|==|!=|<=|>=|&&|\|\||->|\+=|-=', code)
        clean_words = []
        var_map = {}
        
        for w in raw_words:
            w_lower = w.lower()
            if w_lower in COMMON_SINKS_AND_KEYWORDS:
                clean_words.append(w_lower)
                tokens.append((f"kw:{w_lower}", 1.5))
            else:
                if w_lower not in var_map:
                    var_map[w_lower] = f"var_{len(var_map)}"
                placeholder = var_map[w_lower]
                clean_words.append(placeholder)
                tokens.append((f"sym:{placeholder}", 1.0))

        for n in range(self.config.ngram_min, self.config.ngram_max + 1):
            if n < 2:
                continue
            weight = 1.2 if n == 2 else 0.8
            prefix = "bi" if n == 2 else f"ng{n}"
            for i in range(len(clean_words) - n + 1):
                ngram = f"{prefix}:" + "_".join(clean_words[i:i + n])
                tokens.append((ngram, weight))

        if not tokens:
            tokens = [("empty:code", 1.0)]

        dense_vec = np.zeros(self.dense_dim, dtype=np.float32)
        for tok_str, weight in tokens:
            h = zlib.crc32(tok_str.encode('utf-8'))
            bucket = h % self.dense_dim
            sign = 1.0 if (h // self.dense_dim) % 2 == 0 else -1.0
            dense_vec[bucket] += sign * weight

        norm = np.linalg.norm(dense_vec)
        if norm > 1e-6:
            dense_vec /= norm
        return dense_vec


def main():
    cases_path = Path("tests/eval/generalization_cases.jsonl")
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    standard_hasher = FlyLSHHasher()
    abstract_hasher = AbstractedFlyLSHHasher()

    def eval_with_hasher(h, name):
        variant_avoid = 0
        total_variants = 0
        fix_avoid = 0
        total_fixes = 0
        unrelated_avoid = 0
        total_unrelated = 0

        sim_variants = []
        sim_fixes = []
        sim_unrelated = []

        for c in cases:
            rep_bug = h.hash_code(c["bug_code"])
            bug_indices = set(rep_bug.active_indices)

            for v in c["variants"]:
                rep_v = h.hash_code(v)
                v_indices = set(rep_v.active_indices)
                inter = len(bug_indices.intersection(v_indices))
                sim = inter / (204 - inter)
                sim_variants.append(sim)
                total_variants += 1
                if sim >= 0.65:
                    variant_avoid += 1

            rep_f = h.hash_code(c["fix_code"])
            f_indices = set(rep_f.active_indices)
            inter_f = len(bug_indices.intersection(f_indices))
            sim_f = inter_f / (204 - inter_f)
            sim_fixes.append(sim_f)
            total_fixes += 1
            if sim_f >= 0.65:
                fix_avoid += 1

            for u in c.get("unrelated_snippets", []):
                rep_u = h.hash_code(u)
                u_indices = set(rep_u.active_indices)
                inter_u = len(bug_indices.intersection(u_indices))
                sim_u = inter_u / (204 - inter_u)
                sim_unrelated.append(sim_u)
                total_unrelated += 1
                if sim_u >= 0.65:
                    unrelated_avoid += 1

        print(f"=== Results for {name} ===")
        print(f"Variant Avoid (Recall):    {variant_avoid}/{total_variants} ({variant_avoid/total_variants*100:.2f}%)")
        print(f"Fix Avoid (FPR):           {fix_avoid}/{total_fixes} ({fix_avoid/total_fixes*100:.2f}%)")
        print(f"Unrelated Avoid (FPR):     {unrelated_avoid}/{total_unrelated} ({unrelated_avoid/total_unrelated*100:.2f}%)")
        print(f"Mean Variant Sim:          {np.mean(sim_variants):.3f}")
        print(f"Mean Fix Sim:              {np.mean(sim_fixes):.3f}")
        print(f"Mean Unrelated Sim:        {np.mean(sim_unrelated):.3f}")
        print()

    eval_with_hasher(standard_hasher, "Standard Hasher (Baseline)")
    eval_with_hasher(abstract_hasher, "Abstracted Identifiers Hasher")

if __name__ == "__main__":
    main()
