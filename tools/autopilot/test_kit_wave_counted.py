"""KW-RELAUNCH-1 11-05: counted_items turns an old wave FAIL row into SIGNED / COUNTED in kit_wave_stages.tsv"""
import tempfile
import unittest
from pathlib import Path

import kit_wave as KW


class CountedItems(unittest.TestCase):
    def rows(self, counted):
        cfg = {"dies": {"d": {"event": "e", "counted_items": counted}}}
        st = {"items": {"k1": dict(die="d", item="t1", event="e", status="FAIL", stage="route", reason="TT -3"),
                        "k2": dict(die="d", item="t2", event="e", status="FAIL", stage="route", reason="TT -4")}}
        with tempfile.TemporaryDirectory() as td:
            KW.write_stages(st, td, cfg)
            lines = (Path(td) / KW.STAGES_FILE).read_text().splitlines()
        hdr = lines[0].split("\t")
        return {r["item"]: r for r in (dict(zip(hdr, ln.split("\t"))) for ln in lines[1:])}

    def test_counted_row_reads_signed(self):
        r = self.rows(["t1"])
        self.assertEqual((r["t1"]["status"], r["t1"]["class"]), ("SIGNED", "COUNTED"))
        self.assertIn("counted elsewhere", r["t1"]["reason"])
        self.assertEqual(r["t2"]["status"], "FAIL")

    def test_no_option_unchanged(self):
        self.assertEqual(self.rows([])["t1"]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
