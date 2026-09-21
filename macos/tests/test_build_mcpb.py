import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "build_mcpb.py"
SPEC = importlib.util.spec_from_file_location("build_mcpb", SCRIPT_PATH)
assert SPEC and SPEC.loader
build_mcpb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_mcpb)


class BuildMcpbTests(unittest.TestCase):
    def test_bundle_contains_manifest_icon_and_entry_point(self):
        project_root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "seoultech-c4t.mcpb"
            python_executable = "/Users/test/Library/Application Support/seoultech-lms-connector/venv/bin/python3"
            build_mcpb.build_mcpb(
                project_root,
                output,
                python_executable,
                "0.3.2",
            )
            with zipfile.ZipFile(output) as bundle:
                self.assertEqual(
                    set(bundle.namelist()),
                    {"manifest.json", "icon.png", "server/main.py"},
                )
                manifest = json.loads(bundle.read("manifest.json"))
                self.assertEqual(manifest["manifest_version"], "0.3")
                self.assertEqual(manifest["version"], "0.3.2")
                self.assertEqual(manifest["icon"], "icon.png")
                self.assertEqual(manifest["icons"][0]["size"], "512x512")
                self.assertEqual(
                    manifest["server"]["mcp_config"]["command"],
                    python_executable,
                )
                self.assertEqual(
                    manifest["compatibility"]["platforms"], ["darwin"]
                )
                self.assertNotIn("runtimes", manifest["compatibility"])
                self.assertEqual(len(manifest["tools"]), 7)


if __name__ == "__main__":
    unittest.main()
