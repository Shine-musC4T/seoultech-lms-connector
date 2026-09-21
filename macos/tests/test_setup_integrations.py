import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "setup_integrations.py"
SPEC = importlib.util.spec_from_file_location("setup_integrations", SCRIPT_PATH)
assert SPEC and SPEC.loader
setup_integrations = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup_integrations)


class SetupIntegrationsTests(unittest.TestCase):
    def test_install_and_uninstall_preserve_unrelated_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plugin_source = root / "distribution" / "plugin" / "seoultech-c4t"
            manifest_path = plugin_source / ".codex-plugin" / "plugin.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps({"name": "seoultech-c4t", "version": "0.3.2"}),
                encoding="utf-8",
            )
            (plugin_source / ".mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "seoultech_c4t": {
                                "command": "python",
                                "args": ["-m", "seoultech_lms.mcp_server"],
                                "enabled": True,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            user_profile = root / "user"
            marketplace_path = user_profile / ".agents" / "plugins" / "marketplace.json"
            marketplace_path.parent.mkdir(parents=True)
            marketplace_path.write_text(
                json.dumps(
                    {
                        "name": "personal",
                        "interface": {"displayName": "My Plugins"},
                        "plugins": [{"name": "keep-me"}],
                    }
                ),
                encoding="utf-8",
            )
            claude_path = root / "appdata" / "Claude" / "claude_desktop_config.json"
            claude_path.parent.mkdir(parents=True)
            claude_path.write_text(
                json.dumps({"mcpServers": {"keep-me": {"command": "example"}}}),
                encoding="utf-8",
            )

            python_executable = "/Users/test/Library/Application Support/seoultech-lms-connector/venv/bin/python3"
            result = setup_integrations.install_codex(
                plugin_source, user_profile, python_executable
            )
            setup_integrations.install_claude_desktop(claude_path, python_executable)

            installed_plugin = Path(result["plugin_path"])
            installed_manifest = json.loads(
                (installed_plugin / ".codex-plugin" / "plugin.json").read_text(
                    encoding="utf-8"
                )
            )
            installed_mcp = json.loads(
                (installed_plugin / ".mcp.json").read_text(encoding="utf-8")
            )
            marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
            claude = json.loads(claude_path.read_text(encoding="utf-8"))

            self.assertEqual(installed_manifest["version"], "0.3.2")
            self.assertEqual(
                installed_mcp["mcpServers"]["seoultech_c4t"]["command"],
                python_executable,
            )
            self.assertTrue(installed_mcp["mcpServers"]["seoultech_c4t"]["enabled"])
            self.assertEqual(marketplace["interface"]["displayName"], "My Plugins")
            self.assertEqual(
                [item["name"] for item in marketplace["plugins"]],
                ["keep-me", "seoultech-c4t"],
            )
            self.assertEqual(
                marketplace["plugins"][1]["source"]["path"],
                "./.codex/plugins/seoultech-c4t",
            )
            self.assertIn("keep-me", claude["mcpServers"])
            self.assertEqual(
                claude["mcpServers"]["seoultech_c4t"]["command"],
                python_executable,
            )

            setup_integrations.uninstall_integrations(user_profile, claude_path)
            marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
            claude = json.loads(claude_path.read_text(encoding="utf-8"))
            self.assertFalse(installed_plugin.exists())
            self.assertEqual(
                [item["name"] for item in marketplace["plugins"]], ["keep-me"]
            )
            self.assertEqual(list(claude["mcpServers"]), ["keep-me"])

    def test_claude_install_keeps_existing_servers_and_restores_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "claude_desktop_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "keep-me": {"command": "example"},
                            "seoultech_c4t": {"command": "python"},
                        }
                    }
                ),
                encoding="utf-8",
            )
            setup_integrations.install_claude_desktop(
                config_path,
                "/Users/test/Library/Application Support/seoultech-lms-connector/venv/bin/python3",
            )
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(list(config["mcpServers"]), ["keep-me", "seoultech_c4t"])
            self.assertEqual(
                config["mcpServers"]["seoultech_c4t"]["args"],
                ["-m", "seoultech_lms.mcp_server"],
            )


if __name__ == "__main__":
    unittest.main()
