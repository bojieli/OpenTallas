"""WAVE-OPS-1 11-10 (COORD URGENT): (a) WAVE-SRC-DRIFT FLAGS line (advisory) from srccheck/<die>.json; (b) core_kit
item_args / args are probed inputs (svgr_top --clock-regions on epyc4)."""
import json, os, tempfile, unittest
import kit_wave as KW


class SrcCheck(unittest.TestCase):
    def cfg(self, t):
        return {"wave_src_check_dir": t, "dies": {"hbm": {"src": "/srv/s/claude/kw43/src_h", "gen_host": "a",
                "gen_hosts": ["a", "b"],
                "core_kit": {"args": ["--slew-margin", "35", "--fp", "/srv/s/claude/l/fp/x.json"],
                             "item_args": {"ot_svgr_top": ["--clock-regions", "/srv/s/claude/p/p6_relay/ccr.json"],
                                           "gone": None}}}}}

    def test_flag_line(self):
        with tempfile.TemporaryDirectory() as t:
            c = self.cfg(t)
            self.assertEqual(KW.wave_src_flag(c, "hbm"), "")                     # no check yet
            json.dump({"src": "/srv/s/claude/kw43/src_h", "host": "epyc4", "declared": "4393753cf0b4aaaa",
                       "mismatch": 71, "stale": 60, "undeclared": 11, "at": "2026-11-10 21:00 PST"},
                      open(os.path.join(t, "hbm.json"), "w"))
            fl = KW.wave_src_flag(c, "hbm")
            self.assertTrue(fl.startswith("FLAGS WAVE-SRC-DRIFT hbm: src /srv/s/claude/kw43/src_h on epyc4"), fl)
            self.assertIn("4393753cf0b4 + approved overlays in 71 file(s)", fl)
            self.assertIn("ADVISORY", fl)
            c["dies"]["hbm"]["src"] = "/srv/s/claude/wave-src/x/hbm"                # switched: old check is moot
            self.assertEqual(KW.wave_src_flag(c, "hbm"), "")

    def test_clean_is_silent(self):
        with tempfile.TemporaryDirectory() as t:
            json.dump({"src": "/srv/s/claude/kw43/src_h", "mismatch": 0}, open(os.path.join(t, "hbm.json"), "w"))
            self.assertEqual(KW.wave_src_flag(self.cfg(t), "hbm"), "")

    def test_core_item_args_are_inputs(self):
        ins = KW.item_inputs(self.cfg("/x"), "hbm")
        self.assertEqual(ins["ot_svgr_top"], ["/srv/s/claude/p/p6_relay/ccr.json"])
        self.assertNotIn("gone", ins)
        self.assertIn("/srv/s/claude/l/fp/x.json", KW.deep_inputs(self.cfg("/x"), "hbm"))

    def test_core_view_item_skips_host_missing_its_args(self):
        c = self.cfg("/x")
        c["_item_incomplete"] = {"a": {"hbm": {"ot_svgr_top": "ccr.json missing"}}}
        self.assertEqual(KW.gen_hosts(c, "hbm", "ot_svgr_top__v0123456789ab"), ["b"])
        self.assertEqual(KW.gen_hosts(c, "hbm", "ot_svgr_top"), ["b"])
        self.assertEqual(KW.gen_hosts(c, "hbm", "other"), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
