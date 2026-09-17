"""
E2E tests for Calyx MCP CLI installer and init subcommands.
"""

import sys
import json
import subprocess
from pathlib import Path
import pytest
from calyx_mcp.installer import init_agents_md, get_system_paths


def test_cli_help():
    """Verify calyx-mcp runs cleanly and displays help"""
    res = subprocess.run([sys.executable, "-m", "calyx_mcp.server", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Calyx MCP Server" in res.stdout or "calyx" in res.stdout.lower()


def test_cli_install_status():
    """Verify calyx-mcp install --status executes and lists targets"""
    res = subprocess.run([sys.executable, "-m", "calyx_mcp.server", "install", "--status"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Calyx MCP Target Discovery" in res.stdout
    assert "Claude Desktop" in res.stdout
    assert "Google Antigravity" in res.stdout
    assert "Cursor" in res.stdout


def test_cli_init_workspace(tmp_path):
    """Verify calyx-mcp init creates AGENTS.md in target directory"""
    res = subprocess.run([sys.executable, "-m", "calyx_mcp.server", "init", "--path", str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Created Calyx agent directives" in res.stdout
    assert (tmp_path / "AGENTS.md").exists()

    # Repeat without --force
    res2 = subprocess.run([sys.executable, "-m", "calyx_mcp.server", "init", "--path", str(tmp_path)], capture_output=True, text=True)
    assert "already exists" in res2.stdout

    # Repeat with --force
    res3 = subprocess.run([sys.executable, "-m", "calyx_mcp.server", "init", "--path", str(tmp_path), "--force"], capture_output=True, text=True)
    assert "Created Calyx agent directives" in res3.stdout
