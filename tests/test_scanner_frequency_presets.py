# SPDX-License-Identifier: GPL-3.0-or-later
"""Receive-only frequency selection regression tests (no SDR hardware needed)."""

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from droneid_hackrf_scanner import build_parser, select_frequencies  # noqa: E402


class ScannerFrequencyPresetTests(unittest.TestCase):
    def parse_frequencies(self, *options):
        args = build_parser().parse_args(list(options))
        return select_frequencies(args)

    def test_default_2g_scan_order_is_unchanged(self):
        self.assertEqual(
            self.parse_frequencies(),
            [2444500000, 2429500000, 2414500000, 2459500000, 2399500000],
        )

    def test_baseline_5g_includes_reported_5816_5(self):
        self.assertEqual(
            self.parse_frequencies("--band", "5g"),
            [5756500000, 5776500000, 5796500000, 5816500000],
        )

    def test_issue2_preset_selects_the_published_four_plus_four(self):
        self.assertEqual(
            self.parse_frequencies("--preset", "issue2", "--band", "both"),
            [
                2414500000, 2429500000, 2444500000, 2459500000,
                5756500000, 5776500000, 5796500000, 5816500000,
            ],
        )

    def test_paper2022_frequencies_follow_unambiguous_table_rows(self):
        self.assertEqual(
            self.parse_frequencies("--preset", "paper2022", "--band", "both"),
            [
                2399500000, 2414500000, 2429500000, 2444500000,
                2459500000, 5741500000, 5756500000, 5771500000,
                5786500000, 5801500000, 5816500000, 5831500000,
            ],
        )
        # Prose says 2474.5 MHz, but Table II repeats 2459.5 MHz.
        self.assertNotIn(
            2474500000,
            self.parse_frequencies("--preset", "paper2022", "--band", "2g"),
        )

    def test_explicit_frequency_override_ignores_band_and_preset(self):
        self.assertEqual(
            self.parse_frequencies(
                "--band", "5g", "--preset", "issue2",
                "--freqs", "2474.5,5816.5",
            ),
            [2474500000, 5816500000],
        )


if __name__ == "__main__":
    unittest.main()
