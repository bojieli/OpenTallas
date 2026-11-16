import unittest
import ruling_holds as R

LINES = [
    "- 2026-11-15 10:00 PST RULING [COORD -> X] r122 MHOLD s81 ot_s81sl_leaf__t14,slice_station__t2* until claude/genbug-fix-1115 : GEN_LINT defparam LOCAL",
    "plain text, no clause",
    "MHOLD nodie foo until abc123",
]


class RulingHolds(unittest.TestCase):
    def cfg(self):
        return {"dies": {"s81": {"hold_items": {"manual": "by hand"}}, "qwen_compute": {}}}

    def test_parse(self):
        c = R.parse_lines(LINES)
        self.assertEqual(c[0][:4], (1, "s81", ["ot_s81sl_leaf__t14", "slice_station__t2*"], "claude/genbug-fix-1115"))
        self.assertEqual(c[0][4], "GEN_LINT defparam LOCAL")
        self.assertEqual(len(c), 2)

    def test_add_then_release_on_merge(self):
        cfg = self.cfg(); c = R.parse_lines(LINES)
        added, rel = R.apply(cfg, c, lambda ref: False)
        self.assertEqual(added, [("s81", "ot_s81sl_leaf__t14"), ("s81", "slice_station__t2*")])   # unknown die skipped
        self.assertTrue(cfg["dies"]["s81"]["hold_items"]["ot_s81sl_leaf__t14"].startswith("MHOLD claude/genbug-fix-1115 "))
        self.assertEqual(R.apply(cfg, c, lambda ref: False), ([], []))                              # idempotent
        added, rel = R.apply(cfg, c, lambda ref: ref == "claude/genbug-fix-1115")
        self.assertEqual(added, []); self.assertEqual(len(rel), 2)
        self.assertEqual(cfg["dies"]["s81"]["hold_items"], {"manual": "by hand"})                   # hand holds untouched

    def test_merged_ref_adds_nothing(self):
        cfg = self.cfg()
        self.assertEqual(R.apply(cfg, R.parse_lines(LINES), lambda ref: True), ([], []))


if __name__ == "__main__":
    unittest.main()
