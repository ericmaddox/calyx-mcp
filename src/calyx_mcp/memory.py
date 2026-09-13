"""
Mushroom Body Synaptic Weight Tensor & Persistent Storage Engine
Thread-safe, atomic disk persistence for learned code patterns.
"""

import os
import json
import asyncio
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .config import PlasticityConfig, StorageConfig
from .hasher import FlyLSHHasher, KenyonSparseRepresentation


class MushroomBodyMemory:
    """
    Manages Kenyon Cell -> MBON synaptic connection weights and associative memory metadata.
    """

    def __init__(self, plasticity_cfg: Optional[PlasticityConfig] = None, storage_cfg: Optional[StorageConfig] = None):
        self.plasticity_cfg = plasticity_cfg or PlasticityConfig()
        self.storage_cfg = storage_cfg or StorageConfig()
        self.hasher = FlyLSHHasher()
        self.kenyon_dim = self.hasher.kenyon_cells

        # Synaptic Weights Array: W in R^D (initialized to baseline 1.0)
        self.weights = np.full(self.kenyon_dim, self.plasticity_cfg.baseline_weight, dtype=np.float32)
        
        # Associative Record Store (for semantic queries)
        self.records: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        
        # Ensure storage directory exists and load weights
        self.storage_dir = Path(self.storage_cfg.storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.weights_path = self.storage_dir / self.storage_cfg.weights_filename
        self.metadata_path = self.storage_dir / self.storage_cfg.metadata_filename
        
        self.load_from_disk()

    def load_from_disk(self) -> bool:
        """Load synaptic weights and memory metadata from disk"""
        try:
            if self.weights_path.exists():
                data = np.load(self.weights_path)
                if "weights" in data and len(data["weights"]) == self.kenyon_dim:
                    self.weights = data["weights"].astype(np.float32)
            if self.metadata_path.exists():
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
            return True
        except Exception:
            # Fallback to pristine initialized state on corrupt file
            self.weights = np.full(self.kenyon_dim, self.plasticity_cfg.baseline_weight, dtype=np.float32)
            self.records = []
            return False

    def save_to_disk(self) -> None:
        """Atomic file save to prevent mid-write corruption"""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            # 1. Atomic weights save (.tmp -> replace)
            tmp_weights = self.weights_path.with_suffix(".tmp.npz")
            np.savez_compressed(tmp_weights, weights=self.weights)
            if tmp_weights.exists():
                tmp_weights.replace(self.weights_path)
                
            # 2. Atomic metadata save (.tmp -> replace)
            tmp_meta = self.metadata_path.with_suffix(".tmp.json")
            with open(tmp_meta, "w", encoding="utf-8") as f:
                json.dump(self.records[-500:], f, indent=2)  # Cap metadata store to latest 500 records
            if tmp_meta.exists():
                tmp_meta.replace(self.metadata_path)
        except Exception:
            pass

    async def remember(self, code: str, outcome: str, error_message: Optional[str] = None, 
                       tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Applies dopamine reward (+1.0 PAM) or punishment (-1.0 PPL1) to active Kenyon Cell synapses.
        """
        async with self._lock:
            rep = self.hasher.hash_code(code)
            lr = self.plasticity_cfg.learning_rate
            
            # Determine valence direction
            if outcome.lower() in ["success", "passed", "reward"]:
                valence_delta = lr * self.plasticity_cfg.reward_multiplier
                valence_type = "reward"
            else:
                valence_delta = -lr * self.plasticity_cfg.punishment_multiplier
                valence_type = "punishment"

            # Apply plastic update to active Kenyon synapses: W_i += delta
            self.weights[rep.active_indices] += valence_delta
            
            # Clamp weights to bounded range [min_weight, max_weight]
            self.weights = np.clip(self.weights, self.plasticity_cfg.min_weight, self.plasticity_cfg.max_weight)

            # Record associative entry for future nearest-neighbor lookup
            record = {
                "id": f"rec_{len(self.records)+1}",
                "timestamp": datetime.now().isoformat(),
                "outcome": outcome,
                "valence_type": valence_type,
                "error_message": error_message or "",
                "tags": tags or [],
                "active_indices": rep.active_indices.tolist(),
                "code_snippet": code[:200]
            }
            self.records.append(record)

            self.save_to_disk()

            # Compute current pattern valence
            current_valence = float(np.mean(self.weights[rep.active_indices]))

            return {
                "status": "recorded",
                "outcome": outcome,
                "valence_type": valence_type,
                "pattern_valence": round(current_valence, 4),
                "active_synapses_updated": len(rep.active_indices),
                "total_memories_stored": len(self.records)
            }

    async def query_similarity(self, query_code: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Finds closest previously stored code patterns using Fly-LSH Hamming distance"""
        async with self._lock:
            if not self.records:
                return []
            
            query_rep = self.hasher.hash_code(query_code)
            query_set = set(query_rep.active_indices.tolist())
            
            scored_records = []
            for rec in self.records:
                rec_set = set(rec["active_indices"])
                intersection = len(query_set.intersection(rec_set))
                union = len(query_set.union(rec_set))
                similarity = float(intersection) / float(union) if union > 0 else 0.0
                scored_records.append({
                    "id": rec["id"],
                    "similarity": round(similarity, 4),
                    "outcome": rec["outcome"],
                    "error_message": rec["error_message"],
                    "tags": rec["tags"],
                    "code_snippet": rec["code_snippet"]
                })

            # Sort descending by similarity
            scored_records.sort(key=lambda x: x["similarity"], reverse=True)
            return scored_records[:top_k]

    async def get_state_metrics(self) -> Dict[str, Any]:
        """Inspect synaptic weight distribution and health metrics"""
        async with self._lock:
            return {
                "total_memories_stored": len(self.records),
                "total_kenyon_cells": self.kenyon_dim,
                "active_sparsity_pct": round(self.hasher.config.active_k / self.kenyon_dim * 100, 2),
                "weights_avg": round(float(np.mean(self.weights)), 4),
                "weights_min": round(float(np.min(self.weights)), 4),
                "weights_max": round(float(np.max(self.weights)), 4),
                "depressed_synapses_count": int(np.sum(self.weights < 0.85)),
                "potentiated_synapses_count": int(np.sum(self.weights > 1.15)),
                "storage_location": str(self.storage_dir)
            }

    async def reset(self, backup: bool = True) -> Dict[str, Any]:
        """Reset weights to baseline"""
        async with self._lock:
            backup_file = None
            if backup and self.weights_path.exists():
                backup_file = str(self.storage_dir / f"backup_{int(datetime.now().timestamp())}.npz")
                np.savez_compressed(backup_file, weights=self.weights)
            
            self.weights = np.full(self.kenyon_dim, self.plasticity_cfg.baseline_weight, dtype=np.float32)
            self.records = []
            self.save_to_disk()
            return {
                "status": "reset_complete",
                "backup_created": backup_file is not None,
                "backup_path": backup_file
            }
