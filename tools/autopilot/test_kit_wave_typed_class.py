import unittest
import kit_wave as K


class Typed(unittest.TestCase):
    def t(self, why, stage="gen", cls="INFRA"):
        return K.typed_class(cls, stage, why)

    def test_types(self):
        self.assertEqual(self.t("ot-run: interrupted (signal 15) on epyc7"), "stopped")
        self.assertEqual(self.t("infra @gen: sdc_lint.SdcLintError: type sl"), "sdc_lint")
        self.assertEqual(self.t("STALE-CORE-VIEW ot_s81_cfg7_seq_bfp"), "stale_view")
        self.assertEqual(self.t("bind: ERROR preferred HDL source missing: /x", "kit_rtl"), "missing_input")
        self.assertEqual(self.t("INFRA-VIEW-MISSING: the die-owner view is not on any host", "prov_views"), "missing_input")
        self.assertEqual(self.t("gen phys: ERROR plan invalid: unknown key 'phy_pg_floor_um'", "kit_rtl"), "tool_mix")
        self.assertEqual(self.t("NameError: name 'os' is not defined", "kit_rtl"), "tool_mix")
        self.assertEqual(self.t("global_place.tcl 5 unmapped flop", "place", "FLOW"), "design:place")
        self.assertEqual(self.t("x", "", "FLOW"), "design:unknown")

    def test_ssh_timeouts_and_earlyoom_are_infra(self):
        for why in ("ssh: connect to host epyc7 port 22: Connection timed out", "ssh transport drop before RAN on",
                    "host earlyoom SIGTERM victim, make Error 247", "ot-run: NOT RUN: no host qualifies", "rc 137"):
            self.assertEqual(self.t(why, "place", "FLOW"), "infra", why)
        self.assertEqual(self.t("global_place.tcl 5 unmapped flop", "place", "FLOW"), "design:place")

    def test_stopped_never_counts(self):
        self.assertIsNone(K.fail_signature("INFRA", "ot-run: interrupted (signal 15) on epyc7", "place"))
        self.assertIsNone(K.fail_signature("FLOW", "stopped by operator", "place"))
        self.assertIsNotNone(K.fail_signature("FLOW", "global_place.tcl 5 unmapped flop @place", "place"))


if __name__ == "__main__":
    unittest.main()
