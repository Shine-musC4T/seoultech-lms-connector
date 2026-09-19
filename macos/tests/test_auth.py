import os
import unittest
from pathlib import Path
from unittest.mock import patch

from seoultech_lms.auth import user_data_dir


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


if __name__ == "__main__":
    unittest.main()
