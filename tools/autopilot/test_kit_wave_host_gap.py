"""KW-FIX-46 11-12 (COORD 09:3x): a missing-input FLOW failure on a host the last src probe listed as SRC-INCOMPLETE for the
die (or item) is INFRA (host copy gap); anywhere else it stays FLOW"""
import unittest
import kit_wave as K

ST = {"src_incomplete_last": {"dies": {"intel1": {"hbm": "/s/tools/die_plan/bind.py missing"}},
                              "items": {"epyc2": {"hbm": {"q_b013": "/p/plan.json missing"}}}}}


class HostGap(unittest.TestCase):
    def test_die_gap_on_that_host(self):
        self.assertIn("bind.py", K.host_input_gap(ST, {"die": "hbm", "item": "PHY_NE"}, "intel1"))

    def test_item_gap_on_that_host_only(self):
        self.assertTrue(K.host_input_gap(ST, {"die": "hbm", "item": "q_b013"}, "epyc2"))
        self.assertEqual(K.host_input_gap(ST, {"die": "hbm", "item": "q_other"}, "epyc2"), "")

    def test_other_host_die_or_no_probe_is_no_gap(self):
        self.assertEqual(K.host_input_gap(ST, {"die": "hbm", "item": "PHY_NE"}, "epyc9"), "")
        self.assertEqual(K.host_input_gap(ST, {"die": "s81", "item": "t1"}, "intel1"), "")
        self.assertEqual(K.host_input_gap({}, {"die": "hbm", "item": "PHY_NE"}, "intel1"), "")
        self.assertEqual(K.host_input_gap(ST, {"die": "hbm", "item": "PHY_NE"}, None), "")

    def test_reasons_covered(self):
        cls, why = K.classify("kit_rtl", "bash: line 1: cd: /srv/x/src: No such file or directory")
        self.assertEqual(cls, "FLOW")
        self.assertTrue(why.startswith(K.HOST_GAP_WHY))


if __name__ == "__main__":
    unittest.main()
