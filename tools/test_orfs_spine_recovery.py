"""Only the spine's completed ordinary legalization clears a stale error count."""
import tempfile
import unittest
from pathlib import Path
from orfs_hold_mm import tolerate_flow_errors

ERROR = "[ERROR DPL-0033] detailed placement checks failed during check placement."
WARNING = "OT_SPINE WARNING: check_placement failed after spine insertion (DPL-0033); legalising movable cells around the spine"
CLEAN = "OT_SPINE legal: check_placement clean after detailed_placement"

class SpineRecovery(unittest.TestCase):
    def check(self, lines, expected, count=1, stage="cts"):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "4_1_cts.log" if stage == "cts" else "5_1_grt.log").write_text("\n".join(lines))
            key = stage + "__flow__errors__count"
            self.assertEqual(tolerate_flow_errors({key: count}, d)[key], expected)

    def test_completed_recovery(self):
        self.check([ERROR, WARNING, CLEAN], 0)

    def test_missing_or_reordered_recovery(self):
        for lines in ([ERROR, WARNING], [ERROR, CLEAN], [ERROR, CLEAN, WARNING], [CLEAN, ERROR, WARNING]):
            with self.subTest(lines=lines): self.check(lines, 1)

    def test_unrelated_and_repeated_errors(self):
        self.check([ERROR, WARNING, CLEAN, "[ERROR STA-0001] failure"], 2, 2)
        self.check([ERROR, WARNING, ERROR, CLEAN], 2, 2)
        self.check([ERROR, WARNING, CLEAN, ERROR, WARNING, CLEAN], 0, 2)
        self.check([ERROR, WARNING, CLEAN], 2, 2)

    def test_wrong_stage(self):
        self.check([ERROR, WARNING, CLEAN], 1, stage="globalroute")

    def test_existing_hold_cap(self):
        self.check(["[ERROR RSZ-0060] Max buffer count", "OT_HOLD_MM after repair"], 0)

if __name__ == "__main__": unittest.main()
