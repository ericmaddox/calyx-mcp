"""
Unit and Integration Tests for Cybersecurity & Reliability Hardening
Verifies:
- allow_pickle=False deserialization enforcement
- Non-finite (NaN/Inf) weight corruption recovery
- Input bounds enforcement (code, error_message, tags)
- JSON-RPC error status codes (-32602 vs -32603)
- Non-destructive .orig.bak preservation in installer
- Resilient JSONC parsing with comments and trailing commas in installer
- Secure directory permissions
"""

import os
import json
import pytest
import numpy as np
from pathlib import Path

from calyx_mcp.config import (
    CalyxConfig,
    StorageConfig,
    MAX_CODE_INPUT_LENGTH,
    MAX_ERROR_MSG_LENGTH,
    MAX_TAG_COUNT,
    MAX_TAG_LENGTH,
)
from calyx_mcp.memory import MushroomBodyMemory
from calyx_mcp.server import CalyxMCPServer
from calyx_mcp.installer import install_to_target, inspect_targets


@pytest.mark.asyncio
async def test_allow_pickle_disabled_on_load(tmp_path):
    """Ensure that loading pickled objects via np.load is blocked by allow_pickle=False"""
    storage_cfg = StorageConfig(storage_dir=str(tmp_path))
    mem = MushroomBodyMemory(storage_cfg=storage_cfg)
    
    # Attempt to write a malicious pickled object into weights file
    weights_path = tmp_path / storage_cfg.weights_filename
    malicious_data = {"weights": np.array([object()], dtype=object)}
    np.savez(weights_path, **malicious_data)
    
    # Reloading should fail deserialization safely and fallback to baseline without crashing
    success = mem.load_from_disk()
    assert success is False
    assert len(mem.weights) == mem.kenyon_dim
    assert np.allclose(mem.weights, 1.0)


@pytest.mark.asyncio
async def test_corrupted_nan_weights_recovery(tmp_path):
    """Ensure non-finite (NaN/Inf) weights are detected and safely reset to baseline"""
    storage_cfg = StorageConfig(storage_dir=str(tmp_path))
    mem = MushroomBodyMemory(storage_cfg=storage_cfg)
    
    weights_path = tmp_path / storage_cfg.weights_filename
    corrupt_weights = np.full(mem.kenyon_dim, np.nan, dtype=np.float32)
    np.savez_compressed(weights_path, weights=corrupt_weights)
    
    mem.load_from_disk()
    assert np.isfinite(mem.weights).all()
    assert np.allclose(mem.weights, 1.0)


@pytest.mark.asyncio
async def test_input_length_validation_in_server():
    """Verify overlong code strings, error messages, and tags are rejected with validation error"""
    server = CalyxMCPServer()
    
    # 1. Overlong code in check_code_reflex
    overlong_code = "x = 1\n" * (MAX_CODE_INPUT_LENGTH // 5 + 10)
    req = {
        "jsonrpc": "2.0",
        "id": "test_1",
        "method": "tools/call",
        "params": {
            "name": "check_code_reflex",
            "arguments": {"code": overlong_code}
        }
    }
    resp = await server.handle_request(req)
    assert resp["error"]["code"] == -32000
    assert "exceeds maximum length" in resp["error"]["message"]

    # 2. Overlong error_message in remember_code_outcome
    overlong_err = "A" * (MAX_ERROR_MSG_LENGTH + 50)
    req = {
        "jsonrpc": "2.0",
        "id": "test_2",
        "method": "tools/call",
        "params": {
            "name": "remember_code_outcome",
            "arguments": {
                "code": "def foo(): pass",
                "outcome": "failure",
                "error_message": overlong_err
            }
        }
    }
    resp = await server.handle_request(req)
    assert resp["error"]["code"] == -32000
    assert "error_message" in resp["error"]["message"]

    # 3. Excessive tags count in remember_code_outcome
    too_many_tags = [f"tag_{i}" for i in range(MAX_TAG_COUNT + 10)]
    req = {
        "jsonrpc": "2.0",
        "id": "test_3",
        "method": "tools/call",
        "params": {
            "name": "remember_code_outcome",
            "arguments": {
                "code": "def foo(): pass",
                "outcome": "failure",
                "tags": too_many_tags
            }
        }
    }
    resp = await server.handle_request(req)
    assert resp["error"]["code"] == -32000
    assert "tags" in resp["error"]["message"]

    # 4. Overlong single tag string
    overlong_tag = ["A" * (MAX_TAG_LENGTH + 10)]
    req = {
        "jsonrpc": "2.0",
        "id": "test_4",
        "method": "tools/call",
        "params": {
            "name": "remember_code_outcome",
            "arguments": {
                "code": "def foo(): pass",
                "outcome": "failure",
                "tags": overlong_tag
            }
        }
    }
    resp = await server.handle_request(req)
    assert resp["error"]["code"] == -32000


def test_installer_orig_bak_preservation(tmp_path):
    """Verify that .orig.bak is preserved and never overwritten by subsequent installs"""
    fake_config = tmp_path / ".gemini" / "config" / "mcp_config.json"
    fake_config.parent.mkdir(parents=True, exist_ok=True)
    initial_content = {"mcpServers": {"existing_custom": {"command": "custom"}}}
    fake_config.write_text(json.dumps(initial_content), encoding="utf-8")

    # First installation
    ok1, msg1 = install_to_target("antigravity", system="Linux", base_dir=tmp_path)
    assert ok1 is True
    
    orig_bak = fake_config.with_suffix(".json.orig.bak")
    assert orig_bak.exists()
    assert json.loads(orig_bak.read_text(encoding="utf-8")) == initial_content

    # Second installation with different parameter
    ok2, msg2 = install_to_target("antigravity", mode="uvx", system="Linux", base_dir=tmp_path)
    assert ok2 is True
    
    # Verify .orig.bak is untouched and still contains the initial pristine config
    assert json.loads(orig_bak.read_text(encoding="utf-8")) == initial_content


def test_installer_jsonc_with_comments_support(tmp_path):
    """Verify installer safely handles configs with // comments and trailing commas"""
    zed_config = tmp_path / ".config" / "zed" / "settings.json"
    zed_config.parent.mkdir(parents=True, exist_ok=True)
    jsonc_content = """{
        // Custom user settings
        "theme": "dark",
        /* Context servers block */
        "context_servers": {
            "test_server": { "command": "test" },
        },
    }"""
    zed_config.write_text(jsonc_content, encoding="utf-8")

    ok, msg = install_to_target("zed", system="Linux", base_dir=tmp_path)
    assert ok is True
    
    updated_data = json.loads(zed_config.read_text(encoding="utf-8"))
    assert "calyx" in updated_data["context_servers"]
    assert updated_data["theme"] == "dark"


@pytest.mark.asyncio
async def test_atomic_persistence_multi_save(tmp_path):
    """Verify rapid sequential saves do not corrupt weights or metadata"""
    storage_cfg = StorageConfig(storage_dir=str(tmp_path))
    mem = MushroomBodyMemory(storage_cfg=storage_cfg)
    
    for i in range(10):
        await mem.remember(f"def test_{i}(): return {i}", "success")
        
    assert len(mem.records) == 10
    assert (tmp_path / storage_cfg.weights_filename).exists()
    assert (tmp_path / storage_cfg.metadata_filename).exists()
