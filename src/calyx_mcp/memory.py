"""
Mushroom Body Synaptic Weight Tensor & Persistent Storage Engine
Thread-safe, atomic disk persistence for learned code patterns.
"""

import os
import json
import asyncio
import logging
from contextlib import contextmanager
import numpy as np
from pathlib import Path
from typing import Dict, Any, Iterator, List, Optional, Tuple
from datetime import datetime

from .config import PlasticityConfig, StorageConfig
from .hasher import FlyLSHHasher, KenyonSparseRepresentation

logger = logging.getLogger("calyx_mcp.memory")


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
        self._record_seq: int = 0
        self._lock = asyncio.Lock()
        
        # Ensure storage directory exists and load weights
        self.storage_dir = Path(self.storage_cfg.storage_dir)
        self._ensure_secure_dir(self.storage_dir)
        self.weights_path = self.storage_dir / self.storage_cfg.weights_filename
        self.metadata_path = self.storage_dir / self.storage_cfg.metadata_filename
        self._save_seq = 0
        
        self.load_from_disk()

    @staticmethod
    def _ensure_secure_dir(directory: Path) -> None:
        """Create directory if needed and enforce 0700 permissions on POSIX systems."""
        directory.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            try:
                os.chmod(directory, 0o700)
            except OSError:
                pass

    @staticmethod
    def _ensure_secure_file(filepath: Path) -> None:
        """Enforce 0600 permissions on POSIX systems."""
        if os.name != "nt" and filepath.exists():
            try:
                os.chmod(filepath, 0o600)
            except OSError:
                pass

    def load_from_disk(self) -> bool:
        """Load synaptic weights and memory metadata from disk with strict deserialization guards"""
        with self._disk_lock():
            return self._load_from_disk()

    @contextmanager
    def _disk_lock(self) -> Iterator[None]:
        """Serialize cooperating processes; the OS releases locks on process exit."""
        self._ensure_secure_dir(self.storage_dir)
        lock_path = self.storage_dir / ".calyx.lock"
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(descriptor, "r+b") as lock_file:
            self._ensure_secure_file(lock_path)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _load_from_disk(self) -> bool:
        """Read one snapshot while the caller holds the disk lock."""
        self.weights = np.full(self.kenyon_dim, self.plasticity_cfg.baseline_weight, dtype=np.float32)
        self.records = []
        self._record_seq = 0
        try:
            if self.weights_path.exists():
                with np.load(self.weights_path, allow_pickle=False) as data:
                    if "weights" in data:
                        loaded = data["weights"].astype(np.float32)
                        if loaded.shape == (self.kenyon_dim,) and np.isfinite(loaded).all():
                            self.weights = loaded
                        else:
                            logger.warning("Invalid weight shape or non-finite values; resetting to baseline.")
            if self.metadata_path.exists():
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    raw_records = json.load(f)
                    if isinstance(raw_records, list):
                        self.records = raw_records[-self.storage_cfg.max_records:]
                        # Recover highest record sequence number
                        seqs = []
                        for r in self.records:
                            rec_id = r.get("id", "")
                            if rec_id.startswith("rec_"):
                                try:
                                    seqs.append(int(rec_id.split("_")[1]))
                                except ValueError:
                                    pass
                        self._record_seq = max(seqs) if seqs else len(self.records)
            return True
        except Exception as e:
            logger.warning(f"Error loading Calyx memory state from disk: {e}; falling back to baseline.")
            self.weights = np.full(self.kenyon_dim, self.plasticity_cfg.baseline_weight, dtype=np.float32)
            self.records = []
            self._record_seq = 0
            return False

    def save_to_disk(self) -> None:
        """Explicitly replace the disk snapshot with this instance's state.

        Use remember/reset for read-modify-write operations shared across clients.
        """
        with self._disk_lock():
            self._save_to_disk()

    def _save_to_disk(self) -> None:
        """Replace each state file while the caller holds the disk lock."""
        try:
            self._ensure_secure_dir(self.storage_dir)
            self._save_seq += 1
            unique_tag = f"{os.getpid()}_{id(self)}_{self._save_seq}"
            
            # 1. Atomic weights save (.tmp_<pid>_<seq> -> replace)
            tmp_weights = self.storage_dir / f".tmp_{unique_tag}_{self.storage_cfg.weights_filename}"
            # A file object prevents NumPy from appending .npz to custom names.
            with open(tmp_weights, "wb") as f:
                np.savez_compressed(f, weights=self.weights)
            self._ensure_secure_file(tmp_weights)
            tmp_weights.replace(self.weights_path)
            self._ensure_secure_file(self.weights_path)
                
            # 2. Atomic metadata save (.tmp_<pid>_<seq> -> replace)
            tmp_meta = self.storage_dir / f".tmp_{unique_tag}_{self.storage_cfg.metadata_filename}"
            with open(tmp_meta, "w", encoding="utf-8") as f:
                json.dump(self.records[-self.storage_cfg.max_records:], f, indent=2)
            self._ensure_secure_file(tmp_meta)
            tmp_meta.replace(self.metadata_path)
            self._ensure_secure_file(self.metadata_path)
        except Exception as e:
            logger.error(f"Failed to persist Calyx memory to disk: {e}")
            raise OSError(
                "Failed to persist Calyx memory; in-memory changes or partial disk "
                "writes may already exist. Inspect state before retrying."
            ) from e

    def apply_decay(self) -> None:
        """Applies passive synaptic weight decay towards baseline (1.0)"""
        self.weights = self.plasticity_cfg.baseline_weight + (self.weights - self.plasticity_cfg.baseline_weight) * self.plasticity_cfg.decay_rate

    async def remember(self, code: str, outcome: str, error_message: Optional[str] = None, 
                       tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Applies dopamine reward (+1.0 PAM) or punishment (-1.0 PPL1) to active Kenyon Cell synapses.
        """
        async with self._lock:
            with self._disk_lock():
                self._load_from_disk()
                return self._remember(code, outcome, error_message, tags)

    def _remember(self, code: str, outcome: str, error_message: Optional[str],
                  tags: Optional[List[str]]) -> Dict[str, Any]:
        """Apply and persist one outcome while both instance and disk locks are held."""
        rep = self.hasher.hash_code(code)
        lr = self.plasticity_cfg.learning_rate

        # Apply passive decay towards baseline if enabled
        if self.plasticity_cfg.enable_weight_decay:
            self.apply_decay()

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
        self._record_seq += 1
        record = {
            "id": f"rec_{self._record_seq}",
            "timestamp": datetime.now().isoformat(),
            "outcome": outcome,
            "valence_type": valence_type,
            "error_message": error_message or "",
            "tags": tags or [],
            "active_indices": rep.active_indices.tolist(),
            "code_snippet": code[:200]
        }
        self.records.append(record)

        # Maintain bounded memory capacity
        if len(self.records) > self.storage_cfg.max_records:
            self.records = self.records[-self.storage_cfg.max_records:]

        self._save_to_disk()

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

    async def query_similarity(self, query_code: str, top_k: int = 5,
                               *, failures_only: bool = False) -> List[Dict[str, Any]]:
        """Find nearest records, optionally filtering failures before truncation."""
        async with self._lock:
            self.load_from_disk()
            if not self.records:
                return []
            
            query_rep = self.hasher.hash_code(query_code)
            query_set = set(query_rep.active_indices.tolist())
            
            scored_records = []
            for idx, rec in enumerate(self.records):
                if failures_only and rec["outcome"].lower() not in ("failure", "failed", "bug", "error"):
                    continue
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
                    "code_snippet": rec["code_snippet"],
                    "_rec_order": idx
                })

            # Sort descending by similarity first, then by recency (_rec_order) for tie-breaking
            scored_records.sort(key=lambda x: (x["similarity"], x["_rec_order"]), reverse=True)
            return [{k: v for k, v in r.items() if k != "_rec_order"} for r in scored_records[:top_k]]

    async def get_state_metrics(self) -> Dict[str, Any]:
        """Inspect synaptic weight distribution and health metrics"""
        async with self._lock:
            self.load_from_disk()
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
            with self._disk_lock():
                self._load_from_disk()
                return self._reset(backup)

    def _reset(self, backup: bool) -> Dict[str, Any]:
        """Back up and reset the latest snapshot while both locks are held."""
        backup_file = None
        if backup and self.weights_path.exists():
            backup_path = self.storage_dir / f"backup_{int(datetime.now().timestamp())}.npz"
            np.savez_compressed(backup_path, weights=self.weights)
            self._ensure_secure_file(backup_path)
            backup_file = str(backup_path)

        self.weights = np.full(self.kenyon_dim, self.plasticity_cfg.baseline_weight, dtype=np.float32)
        self.records = []
        self._record_seq = 0
        self._save_to_disk()
        return {
            "status": "reset_complete",
            "backup_created": backup_file is not None,
            "backup_path": backup_file
        }
