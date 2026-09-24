"""
Typed configuration management for Calyx MCP
"""

import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional


@dataclass
class HasherConfig:
    """Fly-LSH Tokenizer and Hash Dimensions"""
    dense_dim: int = 64
    kenyon_cells: int = 2048
    active_k: int = 102  # ~5% sparsity
    seed: int = 42
    ngram_min: int = 2
    ngram_max: int = 4


@dataclass
class PlasticityConfig:
    """Mushroom Body Dopamine Plasticity Settings"""
    learning_rate: float = 0.15
    baseline_weight: float = 1.0
    min_weight: float = 0.0
    max_weight: float = 5.0
    decay_rate: float = 0.9999
    enable_weight_decay: bool = False
    reward_multiplier: float = 1.0
    punishment_multiplier: float = 1.5


# Security & Denial of Service Bounds
MAX_CODE_INPUT_LENGTH: int = 250_000      # 250 KB max code string size
MAX_ERROR_MSG_LENGTH: int = 10_000        # 10 KB max error message size
MAX_TAG_COUNT: int = 50                   # Max 50 metadata tags per record
MAX_TAG_LENGTH: int = 100                 # Max 100 chars per tag string


@dataclass
class StorageConfig:
    """Persistent Storage Configuration"""
    storage_dir: str = field(default_factory=lambda: str(Path.home() / ".calyx"))
    weights_filename: str = "mushroom_body_weights.npz"
    metadata_filename: str = "memory_registry.json"
    auto_save_interval: int = 1  # save after every learning event
    max_records: int = 500  # maximum episodic memory records to maintain in FIFO ring buffer


@dataclass
class ServerConfig:
    """MCP Server Settings"""
    server_name: str = "calyx-mcp"
    version: str = "1.0.8"
    log_level: str = "INFO"
    transport: str = "stdio"


@dataclass
class ReflexConfig:
    """Reflex Decision Engine Thresholds"""
    avoid_valence_floor: float = 0.85
    safe_valence_ceiling: float = 1.15
    failure_override_similarity: float = 0.65
    contradiction_guard_similarity: float = 0.50
    bug_reason_floor_similarity: float = 0.35


@dataclass
class CalyxConfig:
    """Master Configuration"""
    hasher: HasherConfig = field(default_factory=HasherConfig)
    plasticity: PlasticityConfig = field(default_factory=PlasticityConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    reflex: ReflexConfig = field(default_factory=ReflexConfig)

    @classmethod
    def from_env(cls) -> "CalyxConfig":
        cfg = cls()
        if os.getenv("CALYX_STORAGE_DIR"):
            cfg.storage.storage_dir = os.getenv("CALYX_STORAGE_DIR")
        if os.getenv("CALYX_LOG_LEVEL"):
            cfg.server.log_level = os.getenv("CALYX_LOG_LEVEL")
        return cfg

    @classmethod
    def from_file(cls, path: str) -> "CalyxConfig":
        p = Path(path)
        if not p.exists():
            return cls.from_env()
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = cls.from_env()
        if "hasher" in data:
            for k, v in data["hasher"].items():
                if hasattr(cfg.hasher, k):
                    setattr(cfg.hasher, k, v)
        if "plasticity" in data:
            for k, v in data["plasticity"].items():
                if hasattr(cfg.plasticity, k):
                    setattr(cfg.plasticity, k, v)
        if "storage" in data:
            for k, v in data["storage"].items():
                if hasattr(cfg.storage, k):
                    setattr(cfg.storage, k, v)
        if "server" in data:
            for k, v in data["server"].items():
                if hasattr(cfg.server, k):
                    setattr(cfg.server, k, v)
        if "reflex" in data:
            for k, v in data["reflex"].items():
                if hasattr(cfg.reflex, k):
                    setattr(cfg.reflex, k, v)
        return cfg


def get_default_config() -> CalyxConfig:
    return CalyxConfig.from_env()
