"""KW-FIX-4 11-03: AUTO-GEOM is advisory in the wave (OWNER targets-not-gates); sign-off is the only blocking gate."""
import unittest
import kit_wave as K

FAILL = ("AP_AUTO_GEOM AUTO-GEOM FAIL x KIT-WAVE d44o 3_place r2r=FAIL(912.0) pin_reg_max=FAIL(80.1) "
         "outline=ok(10x10) clock_reach=NA(0)")


class GeomAdvisory(unittest.TestCase):
    def test_fail_line_passes_cond_with_rules(self):
        v, failing, tag = K.geom_gate(FAILL)
        self.assertEqual(v, "PASS-COND")
        self.assertIn("r2r", tag)
        self.assertIn("GEOM-ADVISORY", tag)

    def test_hard_gate_opt_out(self):
        self.assertEqual(K.geom_gate(FAILL, advisory=False)[0], "FAIL")

    def test_missing_verdict_stays_fail(self):
        self.assertEqual(K.geom_gate("AP_AUTO_GEOM_ERROR boom")[0], "FAIL")
        self.assertEqual(K.geom_gate("")[0], "FAIL")

    def test_pass_unchanged(self):
        line = "AP_AUTO_GEOM AUTO-GEOM PASS x outline=ok(1x1)"
        self.assertEqual(K.geom_gate(line), K.geom_verdict(line))

    def test_grt_wall_default_and_override(self):
        # 11-04: S81 probes hit the old 2 h limit and gave grt NA; route GRT measures overflow anyway.
        self.assertEqual(K.opt({"dies": {"d": {}}}, "d", "geom_grt_wall_s"), 1800)
        self.assertEqual(K.opt({"dies": {"d": {"geom_grt_wall_s": 0}}}, "d", "geom_grt_wall_s"), 0)

    def test_spec_carries_option(self):
        cfg = {"dies": {"d": {"geom_advisory": False}}}
        self.assertFalse(K.opt(cfg, "d", "geom_advisory") is not False)
        self.assertTrue(K.opt({"dies": {"d": {}}}, "d", "geom_advisory") is not False)

    def test_rejudge_rows_release_advisory(self):
        st = {"items": {"k": {"die": "d", "item": "x", "attempt": 2, "status": "FAIL", "stage": "geom", "class": "PLAN",
                              "evidence": "h:/g/auto_geom.json", "kit": "h:/kit", "event": "e"}}}
        cfg = {"dies": {"d": {"event": "e"}}}
        rows = K.rejudge_rows(cfg, st, lambda h, items: {"k": {"line": FAILL, "kit_ok": True}})
        self.assertEqual(rows[0]["old"], "FAIL")
        self.assertEqual(rows[0]["new"], "PASS-COND")
        cfg["dies"]["d"]["geom_advisory"] = False
        rows = K.rejudge_rows(cfg, st, lambda h, items: {"k": {"line": FAILL, "kit_ok": True}})
        self.assertEqual(rows[0]["new"], "FAIL")


if __name__ == "__main__":
    unittest.main()
