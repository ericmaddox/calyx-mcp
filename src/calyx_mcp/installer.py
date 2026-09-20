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
                "path": home / ".cursor" / "mcp.json",
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
                "path": home / ".cursor" / "mcp.json",
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
                "path": home / ".cursor" / "mcp.json",
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


def _parse_config(text: str) -> Dict[str, Any]:
    """Decode JSONC without treating quoted comment/comma markers as syntax."""
    decoder = json.JSONDecoder()
    tokens = []
    index = 0
    while index < len(text):
        if text[index] == '"':
            # Let the JSON decoder handle escaped quotes, backslashes and Unicode.
            _, end = decoder.raw_decode(text, index)
            tokens.append(text[index:end])
            index = end
        elif text.startswith("//", index):
            end = index + 2
            while end < len(text) and text[end] not in "\r\n":
                end += 1
            tokens.append(" ")
            index = end
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end == -1:
                raise ValueError("Unterminated block comment")
            # Whitespace prevents adjacent numbers/keywords from being joined.
            tokens.append(" ")
            index = end + 2
        else:
            tokens.append(text[index])
            index += 1

    significant = [i for i, token in enumerate(tokens) if token not in " \t\r\n"]
    for position, index in enumerate(significant):
        if tokens[index] != "," or position == 0 or position + 1 == len(significant):
            continue
        previous = tokens[significant[position - 1]]
        following = tokens[significant[position + 1]]
        if following in ("}", "]") and previous not in ("{", "[", ",", ":"):
            tokens[index] = " "
    data = json.loads("".join(tokens))
    if not isinstance(data, dict):
        raise ValueError("IDE configuration must be a JSON object")
    return data


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
                data = _parse_config(p.read_text(encoding="utf-8"))
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


def resolve_python_interpreter(python_path: Optional[str] = None) -> str:
    """
    Resolves the canonical Python interpreter path.
    Prioritizes explicit python_path, then sys.executable (filtering test runners),
    and falls back to python3 (POSIX) or python (Windows).
    """
    if python_path:
        return str(Path(python_path))
    
    exe = sys.executable
    if exe:
        name = Path(exe).name.lower()
        if not name.startswith("pytest") and not name.startswith("trial"):
            return str(Path(exe))
            
    return "python3" if os.name != "nt" else "python"


def build_calyx_entry(mode: str = "python", schema_type: str = "standard",
                      python_path: Optional[str] = None) -> Dict[str, Any]:
    """Builds standard or Zed JSON payload for Calyx server entry."""
    if mode == "uvx":
        if schema_type == "zed":
            return {"command": "uvx", "args": ["calyx-mcp"]}
        return {"command": "uvx", "args": ["calyx-mcp"]}
    else:
        interpreter = resolve_python_interpreter(python_path)
        return {"command": interpreter, "args": ["-m", "calyx_mcp.server"]}


def install_to_target(target_id: str, mode: str = "python", system: Optional[str] = None,
                      base_dir: Optional[Path] = None, python_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Safely adds Calyx MCP configuration into the target IDE's JSON file.
    Preserves all existing configured servers and creates a .bak backup.
    """
    specs = get_system_paths(system, base_dir)
    target_norm = target_id.lower().strip()

    # Target Aliases
    aliases = {
        "gemini": "antigravity",
        "agy": "antigravity",
        "antigravity_ide": "antigravity",
        "codeium": "windsurf",
        "vscode": "roo",
        "vs_code": "roo",
    }
    target_norm = aliases.get(target_norm, target_norm)

    if target_norm not in specs:
        return False, f"Unknown target: {target_id}. Supported: {', '.join(specs.keys())} (or 'gemini', 'vscode', 'codeium')"

    info = specs[target_norm]
    path: Path = info["path"]
    schema: str = info["schema"]

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data: Dict[str, Any] = {}

        if path.exists():
            # 1. Preserve pristine original backup if not already present
            orig_bak = path.with_suffix(path.suffix + ".orig.bak")
            if not orig_bak.exists():
                shutil.copy2(path, orig_bak)

            # 2. Maintain standard .bak of previous state
            bak_path = path.with_suffix(path.suffix + ".bak")
            shutil.copy2(path, bak_path)

            raw_text = path.read_text(encoding="utf-8")
            try:
                data = _parse_config(raw_text)
            except ValueError as e:
                return False, f"Existing config at {path} is invalid JSON: {e}"

        entry = build_calyx_entry(mode=mode, schema_type=schema, python_path=python_path)

        if schema == "zed":
            if "context_servers" not in data or not isinstance(data["context_servers"], dict):
                data["context_servers"] = {}
            data["context_servers"]["calyx"] = entry
        else:
            if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
                data["mcpServers"] = {}
            data["mcpServers"]["calyx"] = entry

        # Atomic write
        tmp_path = path.with_suffix(path.suffix + f".tmp_{os.getpid()}")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp_path.replace(path)

        return True, f"Configured {info['name']} ({path})"

    except Exception as e:
        return False, f"Failed to configure {info['name']}: {e}"


def install_all_detected(mode: str = "python", system: Optional[str] = None,
                         base_dir: Optional[Path] = None, python_path: Optional[str] = None) -> List[Tuple[str, bool, str]]:
    """Configures all detected IDEs on the host."""
    targets = inspect_targets(system, base_dir)
    results = []

    for t in targets:
        if t.detected or t.config_path.exists():
            success, msg = install_to_target(t.id, mode=mode, system=system, base_dir=base_dir, python_path=python_path)
            results.append((t.name, success, msg))

    # If no specific target folder was detected, configure Antigravity and Claude as defaults
    if not results:
        for default_id in ["antigravity", "claude"]:
            success, msg = install_to_target(default_id, mode=mode, system=system, base_dir=base_dir, python_path=python_path)
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
