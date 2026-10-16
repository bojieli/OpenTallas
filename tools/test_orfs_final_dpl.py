"""Guard the canonical final legalization patch; actual NK/NL replay is separate."""
import tempfile
import unittest
from pathlib import Path
from orfs_hold_mm import patch_final_dpl, FINAL_DPL_ANCHOR, FINAL_DPL_BLOCK

class FinalDplPatchTest(unittest.TestCase):
    def fixture(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name)
        (path / "detail_place.tcl").write_text(text)
        return path

    def test_preserves_check_and_is_idempotent(self):
        original = "proc do_dpl {} {\n" + FINAL_DPL_ANCHOR + "\n}\n"
        path = self.fixture(original)
        self.assertEqual(patch_final_dpl(path), "patched")
        patched = (path / "detail_place.tcl").read_text()
        self.assertEqual(patched.count("check_placement -verbose"), 1)
        self.assertLess(patched.index("optimize_mirroring"), patched.index("OT_FINAL_DPL"))
        self.assertLess(patched.index("OT_FINAL_DPL"), patched.index("check_placement"))
        self.assertEqual(patch_final_dpl(path), "already patched")
        self.assertEqual(patched, (path / "detail_place.tcl").read_text())

    def test_unknown_or_duplicate_sequence_refused_without_write(self):
        for text in ["unknown flow\n", FINAL_DPL_ANCHOR + "\n" + FINAL_DPL_ANCHOR,
                     FINAL_DPL_ANCHOR.replace("-verbose", ""), "# OT_FINAL_DPL\n" + FINAL_DPL_ANCHOR]:
            with self.subTest(text=text):
                path = self.fixture(text)
                with self.assertRaises(SystemExit):
                    patch_final_dpl(path)
                self.assertEqual((path / "detail_place.tcl").read_text(), text)

    def test_missing_stage_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                patch_final_dpl(Path(tmp))

if __name__ == "__main__":
    unittest.main()
