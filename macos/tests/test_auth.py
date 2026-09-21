import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from seoultech_lms.auth import ensure_private_directory, user_data_dir, write_auth_state_secure


class AuthPathTests(unittest.TestCase):
    def test_macos_uses_application_support(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("seoultech_lms.auth.sys.platform", "darwin"),
            patch("seoultech_lms.auth.Path.home", return_value=Path("/Users/test")),
        ):
            self.assertEqual(
                user_data_dir(),
                Path("/Users/test/Library/Application Support/seoultech-lms-connector"),
            )

    def test_auth_state_is_written_atomically_as_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "private" / "auth_state.json"
            state = {"cookies": [{"name": "session", "value": "secret"}]}
            write_auth_state_secure(path, state)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), state)
            self.assertEqual(list(path.parent.glob(".auth_state.json.*.tmp")), [])

    @patch("seoultech_lms.auth.Path.chmod")
    def test_private_directory_uses_owner_only_mode_on_posix(self, chmod):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "private"
            with patch("seoultech_lms.auth.os.name", "posix"):
                ensure_private_directory(path)
            chmod.assert_called_once_with(0o700)


if __name__ == "__main__":
    unittest.main()
