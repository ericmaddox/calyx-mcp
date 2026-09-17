"""
Universal 1-Click MCP Installer & Workspace Initializer for Calyx MCP.
Supports automatic discovery and configuration across Claude Desktop, Cursor,
Google Antigravity, Windsurf, Roo Code, Cline, and Zed.
"""

import os
import sys
import json
import shutil
import platform
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class TargetInfo:
    id: str
    name: str
    config_path: Path
    detected: bool
    configured: bool
    schema_type: str = "standard"  # "standard" (mcpServers) or "zed" (context_servers)


DEFAULT_AGENTS_MD = """# Calyx MCP Agent Directives

When interacting with this codebase or when Calyx MCP is active in your environment, follow the bio-inspired code reflex loop below.

## Calyx Associative Memory Policy

You have access to the Calyx Mushroom Body code reflex server over MCP. Use the following 2-step verification and learning loop:

### 1. Pre-Flight Reflex Check (Before Modifying or Generating Code)
- Before writing, replacing, or proposing significant code diffs, call `check_code_reflex(code=...)`.
- **Interpreting Reflex Outcomes**:
  - `status: "avoid"`: **Do NOT proceed** with that implementation. The code has high structural resemblance to a previously punished bug pattern or negative synaptic valence. Inspect the `warning` and `recommendation` to choose an alternative approach.
  - `status: "safe"`: Proceed with confidence. The code matches previously rewarded implementations.
  - `status: "neutral"`: Novel or unverified code pattern. Proceed normally.

### 2. Post-Execution Synaptic Learning (After Testing Code)
- After executing tests, build scripts, or terminal verification:
  - If a test fails or a runtime error occurs, call `remember_code_outcome(code=..., outcome="failure", error_message=...)` with the failing snippet and error reason.
  - If tests pass and the implementation is verified, call `remember_code_outcome(code=..., outcome="success")` to reinforce the active synapses.

### 3. Associative Retrieval
- Use `query_associative_memory(query_code=..., top_k=5, compact=True)` when searching for past related bug patterns or past lessons in the repository.
"""


def get_system_paths(system: Optional[str] = None, base_dir: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """
    Returns platform-specific target definitions and config file locations.
    Supports base_dir override for deterministic multi-platform testing.
    """
    sys_name = system or platform.system()
    home = base_dir if base_dir is not None else Path.home()

    if sys_name == "Windows":
        appdata = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
        if base_dir is not None:
            appdata = base_dir / "AppData" / "Roaming"

        return {
            "claude": {
                "name": "Claude Desktop",
                "path": appdata / "Claude" / "claude_desktop_config.json",
                "schema": "standard"
            },
            "cursor": {
                "name": "Cursor",
                "path": appdata / "Cursor" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json",
                "schema": "standard"
            },
            "antigravity": {
                "name": "Google Antigravity",
                "path": home / ".gemini" / "config" / "mcp_config.json",
                "schema": "standard"
            },
            "windsurf": {
                "name": "Windsurf (Codeium)",
                "path": home / ".codeium" / "windsurf" / "mcp_config.json",
                "schema": "standard"
            },
            "roo": {
                "name": "Roo Code (VS Code)",
                "path": appdata / "Code" / "User" / "globalStorage" / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json",
                "schema": "standard"
            },
            "cline": {
                "name": "Cline (VS Code)",
                "path": appdata / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json",
                "schema": "standard"
            },
            "zed": {
                "name": "Zed Editor",
                "path": home / ".config" / "zed" / "settings.json",
                "schema": "zed"
            }
        }

    elif sys_name == "Darwin":  # macOS
        app_support = home / "Library" / "Application Support"
        return {
            "claude": {
                "name": "Claude Desktop",
                "path": app_support / "Claude" / "claude_desktop_config.json",
                "schema": "standard"
            },
            "cursor": {
                "name": "Cursor",
                "path": app_support / "Cursor" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json",
                "schema": "standard"
            },
            "antigravity": {
                "name": "Google Antigravity",
                "path": home / ".gemini" / "config" / "mcp_config.json",
                "schema": "standard"
            },
            "windsurf": {
                "name": "Windsurf (Codeium)",
                "path": home / ".codeium" / "windsurf" / "mcp_config.json",
                "schema": "standard"
            },
            "roo": {
                "name": "Roo Code (VS Code)",
                "path": app_support / "Code" / "User" / "globalStorage" / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json",
                "schema": "standard"
            },
            "cline": {
                "name": "Cline (VS Code)",
                "path": app_support / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json",
                "schema": "standard"
            },
            "zed": {
                "name": "Zed Editor",
                "path": home / ".config" / "zed" / "settings.json",
                "schema": "zed"
            }
        }

    else:  # Linux / default
        config_dir = home / ".config"
        return {
            "claude": {
                "name": "Claude Desktop",
                "path": config_dir / "Claude" / "claude_desktop_config.json",
                "schema": "standard"
            },
            "cursor": {
                "name": "Cursor",
                "path": config_dir / "Cursor" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json",
                "schema": "standard"
            },
            "antigravity": {
                "name": "Google Antigravity",
                "path": home / ".gemini" / "config" / "mcp_config.json",
                "schema": "standard"
            },
            "windsurf": {
                "name": "Windsurf (Codeium)",
                "path": home / ".codeium" / "windsurf" / "mcp_config.json",
                "schema": "standard"
            },
            "roo": {
                "name": "Roo Code (VS Code)",
                "path": config_dir / "Code" / "User" / "globalStorage" / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json",
                "schema": "standard"
            },
            "cline": {
                "name": "Cline (VS Code)",
                "path": config_dir / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json",
                "schema": "standard"
            },
            "zed": {
                "name": "Zed Editor",
                "path": config_dir / "zed" / "settings.json",
                "schema": "zed"
            }
        }


def inspect_targets(system: Optional[str] = None, base_dir: Optional[Path] = None) -> List[TargetInfo]:
    """Inspects all supported targets on the host and checks their configuration state."""
    specs = get_system_paths(system, base_dir)
    results = []

    for target_id, info in specs.items():
        p = info["path"]
        detected = p.exists() or p.parent.exists()
        configured = False

        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if info["schema"] == "zed":
                    configured = "calyx" in data.get("context_servers", {})
                else:
                    configured = "calyx" in data.get("mcpServers", {})
            except Exception:
                configured = False

        results.append(TargetInfo(
            id=target_id,
            name=info["name"],
            config_path=p,
            detected=detected,
            configured=configured,
            schema_type=info["schema"]
        ))

    return results


def build_calyx_entry(mode: str = "python", schema_type: str = "standard") -> Dict[str, Any]:
    """Builds standard or Zed JSON payload for Calyx server entry."""
    if mode == "uvx":
        if schema_type == "zed":
            return {"command": "uvx", "args": ["calyx-mcp"]}
        return {"command": "uvx", "args": ["calyx-mcp"]}
    else:
        if schema_type == "zed":
            return {"command": "calyx-mcp", "args": []}
        return {"command": "calyx-mcp"}


def install_to_target(target_id: str, mode: str = "python", system: Optional[str] = None,
                      base_dir: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Safely adds Calyx MCP configuration into the target IDE's JSON file.
    Preserves all existing configured servers and creates a .bak backup.
    """
    specs = get_system_paths(system, base_dir)
    if target_id not in specs:
        return False, f"Unknown target: {target_id}. Supported: {', '.join(specs.keys())}"

    info = specs[target_id]
    path: Path = info["path"]
    schema: str = info["schema"]

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data: Dict[str, Any] = {}

        if path.exists():
            # Create safety backup
            bak_path = path.with_suffix(path.suffix + ".bak")
            shutil.copy2(path, bak_path)

            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                return False, f"Existing config at {path} is invalid JSON: {e}"

        entry = build_calyx_entry(mode=mode, schema_type=schema)

        if schema == "zed":
            if "context_servers" not in data or not isinstance(data["context_servers"], dict):
                data["context_servers"] = {}
            data["context_servers"]["calyx"] = entry
        else:
            if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
                data["mcpServers"] = {}
            data["mcpServers"]["calyx"] = entry

        # Atomic write
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp_path.replace(path)

        return True, f"Configured {info['name']} ({path})"

    except Exception as e:
        return False, f"Failed to configure {info['name']}: {e}"


def install_all_detected(mode: str = "python", system: Optional[str] = None,
                         base_dir: Optional[Path] = None) -> List[Tuple[str, bool, str]]:
    """Configures all detected IDEs on the host."""
    targets = inspect_targets(system, base_dir)
    results = []

    for t in targets:
        if t.detected or t.config_path.exists():
            success, msg = install_to_target(t.id, mode=mode, system=system, base_dir=base_dir)
            results.append((t.name, success, msg))

    # If no specific target folder was detected, configure Antigravity and Claude as defaults
    if not results:
        for default_id in ["antigravity", "claude"]:
            success, msg = install_to_target(default_id, mode=mode, system=system, base_dir=base_dir)
            specs = get_system_paths(system, base_dir)
            results.append((specs[default_id]["name"], success, msg))

    return results


def init_agents_md(target_dir: Optional[Path] = None, overwrite: bool = False) -> Tuple[bool, Path]:
    """
    Creates an AGENTS.md file with the Calyx reflex loop in the specified directory.
    """
    root = target_dir or Path.cwd()
    dest = root / "AGENTS.md"

    if dest.exists() and not overwrite:
        return False, dest

    dest.write_text(DEFAULT_AGENTS_MD, encoding="utf-8")
    return True, dest
