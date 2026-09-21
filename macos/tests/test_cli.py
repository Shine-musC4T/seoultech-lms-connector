import unittest

from seoultech_lms.cli import _build_parser


class CliTests(unittest.TestCase):
    def test_deadlines_command_accepts_horizon(self):
        args = _build_parser().parse_args(["deadlines", "--days", "14", "--json"])
        self.assertEqual(args.command, "deadlines")
        self.assertEqual(args.days, 14)
        self.assertTrue(args.json)

    def test_deadlines_default_horizon_is_seven_days(self):
        args = _build_parser().parse_args(["deadlines"])
        self.assertEqual(args.days, 7)


if __name__ == "__main__":
    unittest.main()
