from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


PLUGIN_NAME = "seoultech-c4t"
SERVER_NAME = "seoultech_c4t"


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path}")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _mcp_server(python_executable: str) -> dict[str, Any]:
    return {
        "command": python_executable,
        "args": ["-m", "seoultech_lms.mcp_server"],
        "env": {},
    }


def install_codex(
    plugin_source: Path,
    user_profile: Path,
    python_executable: str,
) -> dict[str, str]:
    if not (plugin_source / ".codex-plugin" / "plugin.json").is_file():
        raise FileNotFoundError(f"Codex plugin manifest not found: {plugin_source}")

    plugin_destination = user_profile / ".codex" / "plugins" / PLUGIN_NAME
    plugin_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(plugin_source, plugin_destination, dirs_exist_ok=True)

    manifest_path = plugin_destination / ".codex-plugin" / "plugin.json"
    manifest = _read_json(manifest_path, {})

    mcp_path = plugin_destination / ".mcp.json"
    mcp_config = _read_json(mcp_path, {"mcpServers": {}})
    servers = mcp_config.setdefault("mcpServers", {})
    server = servers.setdefault(SERVER_NAME, {})
    server["command"] = python_executable
    server["args"] = ["-m", "seoultech_lms.mcp_server"]
    _write_json(mcp_path, mcp_config)

    marketplace_path = user_profile / ".agents" / "plugins" / "marketplace.json"
    marketplace = _read_json(
        marketplace_path,
        {
            "name": "personal",
            "interface": {"displayName": "Personal"},
            "plugins": [],
        },
    )
    marketplace_name = str(marketplace.get("name", "personal"))
    plugins = marketplace.setdefault("plugins", [])
    if not isinstance(plugins, list):
        raise ValueError(f"plugins must be an array: {marketplace_path}")

    entry = {
        "name": PLUGIN_NAME,
        "source": {
            "source": "local",
            "path": f"./.codex/plugins/{PLUGIN_NAME}",
        },
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Productivity",
    }
    replaced = False
    for index, current in enumerate(plugins):
        if isinstance(current, dict) and current.get("name") == PLUGIN_NAME:
            plugins[index] = entry
            replaced = True
            break
    if not replaced:
        plugins.append(entry)
    _write_json(marketplace_path, marketplace)

    return {
        "marketplace_name": marketplace_name,
        "marketplace_path": str(marketplace_path),
        "plugin_path": str(plugin_destination),
        "plugin_version": str(manifest["version"]),
    }


def install_claude_desktop(config_path: Path, python_executable: str) -> dict[str, str]:
    config = _read_json(config_path, {})
    servers = config.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError(f"mcpServers must be an object: {config_path}")
    servers[SERVER_NAME] = _mcp_server(python_executable)
    _write_json(config_path, config)
    return {"claude_desktop_config": str(config_path)}


def uninstall_integrations(user_profile: Path, claude_config_path: Path) -> dict[str, str]:
    marketplace_path = user_profile / ".agents" / "plugins" / "marketplace.json"
    marketplace_name = "personal"
    if marketplace_path.exists():
        marketplace = _read_json(marketplace_path, {})
        marketplace_name = str(marketplace.get("name", "personal"))
        plugins = marketplace.get("plugins", [])
        if isinstance(plugins, list):
            marketplace["plugins"] = [
                item
                for item in plugins
                if not (isinstance(item, dict) and item.get("name") == PLUGIN_NAME)
            ]
            _write_json(marketplace_path, marketplace)

    plugin_destination = user_profile / ".codex" / "plugins" / PLUGIN_NAME
    expected_parent = (user_profile / ".codex" / "plugins").resolve()
    if plugin_destination.resolve().parent != expected_parent:
        raise ValueError(f"Refusing to remove unexpected path: {plugin_destination}")
    if plugin_destination.exists():
        shutil.rmtree(plugin_destination)

    if claude_config_path.exists():
        config = _read_json(claude_config_path, {})
        servers = config.get("mcpServers")
        if isinstance(servers, dict):
            servers.pop(SERVER_NAME, None)
            _write_json(claude_config_path, config)

    return {
        "marketplace_name": marketplace_name,
        "marketplace_path": str(marketplace_path),
        "plugin_path": str(plugin_destination),
        "claude_desktop_config": str(claude_config_path),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Configure SeoulTech LMS MCP integrations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser("install")
    install.add_argument("--plugin-source", type=Path, required=True)
    install.add_argument("--user-profile", type=Path, required=True)
    install.add_argument("--python-executable", required=True)
    install.add_argument("--claude-config", type=Path, required=True)
    install.add_argument("--skip-codex", action="store_true")
    install.add_argument("--skip-claude-desktop", action="store_true")

    uninstall = subparsers.add_parser("uninstall")
    uninstall.add_argument("--user-profile", type=Path, required=True)
    uninstall.add_argument("--claude-config", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "install":
        result = {"marketplace_name": "personal"}
        if not args.skip_codex:
            result.update(
                install_codex(
                    args.plugin_source.resolve(),
                    args.user_profile.resolve(),
                    args.python_executable,
                )
            )
        if not args.skip_claude_desktop:
            # Keep the regular MCP entry as the dependable fallback until the
            # user has explicitly installed the optional branded MCPB bundle.
            # Removing it pre-emptively makes the connector disappear from
            # Claude when the extension install has not been approved yet.
            result.update(
                install_claude_desktop(args.claude_config, args.python_executable)
            )
    else:
        result = uninstall_integrations(
            args.user_profile.resolve(),
            args.claude_config,
        )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
