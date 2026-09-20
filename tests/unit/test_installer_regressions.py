"""Installer regressions: preserve string values and target native Cursor."""
import json
from pathlib import Path
import tempfile
import unittest

from calyx_mcp.installer import get_system_paths, inspect_targets, install_to_target


class InstallerRegressionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_jsonc_preserves_strings_and_existing_servers(self):
        values = [
            "a/*keep*/b", "https://example.com/api", "literal ,] and ,}",
            'escaped "quote" // still a string', "trailing backslash \\",
        ]
        for index, value in enumerate(values):
            with self.subTest(value=value):
                root = self.root / str(index)
                path = get_system_paths("Linux", root)["zed"]["path"]
                path.parent.mkdir(parents=True)
                original = '{ // comment\n"theme":' + json.dumps(value) + ',\n' + (
                    '"context_servers":{"existing":{"command":"keep"},},\n'
                    '"items":[1, /* between items */ 2,],\n}'
                )
                path.write_text(original, encoding="utf-8")
                ok, message = install_to_target("zed", system="Linux", base_dir=root)
                self.assertTrue(ok, message)
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(data["theme"], value)
                self.assertEqual(data["items"], [1, 2])
                self.assertEqual(data["context_servers"]["existing"], {"command": "keep"})
                self.assertIn("calyx", data["context_servers"])
                self.assertEqual(path.with_suffix(".json.orig.bak").read_text(encoding="utf-8"), original)

    def test_invalid_jsonc_does_not_overwrite_config(self):
        invalid = ['{"theme":1/* unterminated}', '{"theme":1/* gap */2}', '{"theme":"unterminated}']
        for index, original in enumerate(invalid):
            with self.subTest(original=original):
                root = self.root / str(index)
                path = get_system_paths("Linux", root)["zed"]["path"]
                path.parent.mkdir(parents=True)
                path.write_text(original, encoding="utf-8")
                ok, _ = install_to_target("zed", system="Linux", base_dir=root)
                self.assertFalse(ok)
                self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_status_understands_existing_jsonc(self):
        path = get_system_paths("Linux", self.root)["zed"]["path"]
        path.parent.mkdir(parents=True)
        path.write_text('{ // installed\n"context_servers":{"calyx":{"command":"python"},},}', encoding="utf-8")
        target = next(t for t in inspect_targets("Linux", self.root) if t.id == "zed")
        self.assertTrue(target.configured)

    def test_cursor_uses_native_user_config_on_every_platform(self):
        for platform in ["Windows", "Darwin", "Linux"]:
            with self.subTest(platform=platform):
                root = self.root / platform
                paths = get_system_paths(platform, root)
                self.assertEqual(paths["cursor"]["path"], root / ".cursor" / "mcp.json")
                self.assertNotEqual(paths["cursor"]["path"], paths["cline"]["path"])
                ok, message = install_to_target("cursor", system=platform, base_dir=root)
                self.assertTrue(ok, message)
                self.assertIn("calyx", json.loads(paths["cursor"]["path"].read_text())["mcpServers"])
                self.assertFalse(paths["cline"]["path"].exists())
