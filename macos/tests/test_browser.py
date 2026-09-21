import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from seoultech_lms.browser import (
    _is_authenticated_lms_url,
    _persist_authenticated_state,
    start_login_browser,
)


class BrowserLoginTests(unittest.TestCase):
    def test_only_lms_main_page_counts_as_authenticated(self):
        self.assertTrue(
            _is_authenticated_lms_url(
                "https://eclass.seoultech.ac.kr/ilos/main/main_form.acl"
            )
        )
        self.assertFalse(
            _is_authenticated_lms_url(
                "https://eclass.seoultech.ac.kr/ilos/member/login_form.acl"
            )
        )
        self.assertFalse(_is_authenticated_lms_url("https://example.com/ilos/main/main_form.acl"))
        self.assertFalse(
            _is_authenticated_lms_url(
                "http://eclass.seoultech.ac.kr/ilos/main/main_form.acl"
            )
        )

    def test_invalid_login_page_is_not_saved(self):
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "auth_state.json"
            with self.assertRaises(RuntimeError):
                _persist_authenticated_state(
                    state_path,
                    "https://eclass.seoultech.ac.kr/ilos/member/login_form.acl",
                    {"cookies": [{"name": "session", "value": "secret"}]},
                )
            self.assertFalse(state_path.exists())

    def test_authenticated_main_page_is_saved(self):
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "auth_state.json"
            _persist_authenticated_state(
                state_path,
                "https://eclass.seoultech.ac.kr/ilos/main/main_form.acl",
                {"cookies": []},
            )
            self.assertTrue(state_path.is_file())

    @patch("seoultech_lms.browser._process_is_running", return_value=False)
    @patch("seoultech_lms.browser.subprocess.Popen")
    def test_start_login_browser_uses_detached_helper(self, popen: Mock, _running: Mock):
        popen.return_value.pid = 4321
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "auth_state.json"
            result = start_login_browser(state_path)
            self.assertEqual(result["status"], "started")
            self.assertEqual(
                state_path.with_name("login_process.pid").read_text(encoding="utf-8"),
                "4321",
            )
            command = popen.call_args.args[0]
            self.assertEqual(command[1:], ["-m", "seoultech_lms.login_window"])


if __name__ == "__main__":
    unittest.main()
