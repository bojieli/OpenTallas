import unittest
import kit_wave as KW


class HeldStop(unittest.TestCase):
    """KW-FIX-46 11-12: a held row whose unit was stopped from outside is a deliberate stop, not a FAIL"""
    cfg = {"dies": {"qc": {"hold_items": {"sle_hc*": "WAIT-FORM (DIE-QC-100): HF-1c changes these"}}}}

    def test_held_unit_stop(self):
        r = KW.held_stop_reason(self.cfg, {"die": "qc", "item": "sle_hc0__x"}, {"stage": "unit"})
        self.assertIn("WAIT-FORM", r)

    def test_unheld_or_real_stage_stays_fail(self):
        self.assertEqual(KW.held_stop_reason(self.cfg, {"die": "qc", "item": "slw_fe"}, {"stage": "unit"}), "")
        self.assertEqual(KW.held_stop_reason(self.cfg, {"die": "qc", "item": "sle_hc0"}, {"stage": "place"}), "")


if __name__ == "__main__":
    unittest.main()
