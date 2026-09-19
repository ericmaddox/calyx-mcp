"""
Unit tests for Calyx MCP Universal Installer & Workspace Initializer.
"""

import json
from pathlib import Path
import pytest
from calyx_mcp.installer import (
    get_system_paths,
    inspect_targets,
    install_to_target,
    install_all_detected,
    init_agents_md,
    build_calyx_entry
)


def test_system_paths_definitions(tmp_path):
    """Verifies target discovery maps correctly for Windows, macOS, and Linux"""
    for sys_name in ["Windows", "Darwin", "Linux"]:
        paths = get_system_paths(system=sys_name, base_dir=tmp_path)
        assert "claude" in paths
        assert "cursor" in paths
        assert "antigravity" in paths
        assert "windsurf" in paths
        assert "roo" in paths
        assert "cline" in paths
        assert "zed" in paths
        assert paths["zed"]["schema"] == "zed"
        assert paths["claude"]["schema"] == "standard"


def test_install_creates_new_config_and_preserves_structure(tmp_path):
    """Test installing to an unconfigured target creates valid JSON"""
    success, msg = install_to_target("antigravity", mode="python", system="Windows", base_dir=tmp_path)
    assert success
    paths = get_system_paths(system="Windows", base_dir=tmp_path)
    cfg_file = paths["antigravity"]["path"]
    assert cfg_file.exists()

    with open(cfg_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "mcpServers" in data
    assert "calyx" in data["mcpServers"]
    assert data["mcpServers"]["calyx"]["command"] == "python"
    assert data["mcpServers"]["calyx"]["args"] == ["-m", "calyx_mcp.server"]


def test_install_preserves_existing_mcp_servers_and_creates_backup(tmp_path):
    """Verifies that existing MCP servers are NOT overwritten and a .bak backup is created"""
    paths = get_system_paths(system="Windows", base_dir=tmp_path)
    cfg_file = paths["claude"]["path"]
    cfg_file.parent.mkdir(parents=True, exist_ok=True)

    initial_config = {
        "mcpServers": {
            "github": {"command": "github-mcp", "args": ["--token", "xyz"]},
            "gitkraken": {"command": "gk", "args": ["mcp"]}
        }
    }
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(initial_config, f, indent=2)

    # Perform install with uvx mode
    success, msg = install_to_target("claude", mode="uvx", system="Windows", base_dir=tmp_path)
    assert success

    # Verify backup exists
    bak_file = cfg_file.with_suffix(cfg_file.suffix + ".bak")
    assert bak_file.exists()
    with open(bak_file, "r", encoding="utf-8") as f:
        bak_data = json.load(f)
    assert "github" in bak_data["mcpServers"]
    assert "calyx" not in bak_data["mcpServers"]

    # Verify merged file
    with open(cfg_file, "r", encoding="utf-8") as f:
        merged_data = json.load(f)

    assert "github" in merged_data["mcpServers"]
    assert "gitkraken" in merged_data["mcpServers"]
    assert "calyx" in merged_data["mcpServers"]
    assert merged_data["mcpServers"]["calyx"]["command"] == "uvx"
    assert merged_data["mcpServers"]["calyx"]["args"] == ["calyx-mcp"]


def test_install_zed_schema(tmp_path):
    """Verifies Zed context_servers structure"""
    success, msg = install_to_target("zed", mode="python", system="Linux", base_dir=tmp_path)
    assert success
    paths = get_system_paths(system="Linux", base_dir=tmp_path)
    cfg_file = paths["zed"]["path"]
    assert cfg_file.exists()

    with open(cfg_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "context_servers" in data
    assert "calyx" in data["context_servers"]


def test_unknown_target_returns_error(tmp_path):
    """Unknown target returns clean error without crashing"""
    success, msg = install_to_target("non_existent_ide", base_dir=tmp_path)
    assert not success
    assert "Unknown target" in msg


def test_inspect_targets_and_install_all(tmp_path):
    """Test target inspection and batch install"""
    # Create fake parent folders for cursor and windsurf
    paths = get_system_paths(system="Windows", base_dir=tmp_path)
    paths["cursor"]["path"].parent.mkdir(parents=True, exist_ok=True)
    paths["windsurf"]["path"].parent.mkdir(parents=True, exist_ok=True)

    targets = inspect_targets(system="Windows", base_dir=tmp_path)
    detected_ids = [t.id for t in targets if t.detected]
    assert "cursor" in detected_ids
    assert "windsurf" in detected_ids

    # Install all detected
    results = install_all_detected(mode="python", system="Windows", base_dir=tmp_path)
    assert len(results) >= 2
    for name, success, msg in results:
        assert success


def test_init_agents_md(tmp_path):
    """Test generating AGENTS.md in a workspace"""
    created, dest = init_agents_md(target_dir=tmp_path)
    assert created
    assert dest.exists()
    content = dest.read_text(encoding="utf-8")
    assert "check_code_reflex" in content
    assert "remember_code_outcome" in content

    # Should not overwrite unless requested
    created_again, _ = init_agents_md(target_dir=tmp_path, overwrite=False)
    assert not created_again

    # Overwrite true
    dest.write_text("custom", encoding="utf-8")
    created_overwrite, _ = init_agents_md(target_dir=tmp_path, overwrite=True)
    assert created_overwrite
    assert "Calyx MCP Agent Directives" in dest.read_text(encoding="utf-8")


def test_install_target_aliases(tmp_path):
    """Test alias names like 'gemini', 'codeium', and 'vscode' map correctly"""
    success_gemini, _ = install_to_target("gemini", base_dir=tmp_path)
    assert success_gemini

    paths = get_system_paths(base_dir=tmp_path)
    assert paths["antigravity"]["path"].exists()

    success_codeium, _ = install_to_target("codeium", base_dir=tmp_path)
    assert success_codeium
    assert paths["windsurf"]["path"].exists()

    success_vscode, _ = install_to_target("vscode", base_dir=tmp_path)
    assert success_vscode
    assert paths["roo"]["path"].exists()

