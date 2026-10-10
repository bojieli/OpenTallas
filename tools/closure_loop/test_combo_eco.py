"""COMBO ECO (drive-0849 2026-10-09): a thin TT AND thin FF miss runs the VT-swap ECO then a hold ECO stacked on it."""
import unittest
from unittest.mock import patch, MagicMock

import closure_loop as cl


def job(**kw):
    j = dict(name="j", host="h", run="/r", attempt=1, spec=dict(block="b", hold_eco={}, verdict=dict(macros=["m1"])),
             events=[])
    j.update(kw)
    return j


M = dict(ss_ps=-13.9, ff_ps=-7.3, drc=0, post_sdc=["p.sdc"], sdc_name="6_final.sdc")


class Eligible(unittest.TestCase):
    def test_both_thin(self):
        self.assertTrue(cl.combo_eligible(job(), M))

    def test_bounds(self):
        self.assertFalse(cl.combo_eligible(job(), dict(M, ss_ps=-46)))          # TT too deep
        self.assertFalse(cl.combo_eligible(job(), dict(M, ff_ps=-31)))          # FF too deep
        self.assertFalse(cl.combo_eligible(job(), dict(M, ff_ps=0.5)))          # FF ok -> VT-swap's case
        self.assertFalse(cl.combo_eligible(job(), dict(M, ss_ps=1.0)))          # TT ok -> hold ECO's case
        self.assertFalse(cl.combo_eligible(job(), dict(M, drc=3)))

    def test_guards(self):
        self.assertFalse(cl.combo_eligible(job(), M, failed=["x"]))
        self.assertFalse(cl.combo_eligible(job(), M, benches_ok=False))
        self.assertFalse(cl.combo_eligible(job(eco=dict(installed="t")), M))
        self.assertFalse(cl.combo_eligible(job(eco=dict(kind="combo", tried=True)), M))       # once only
        self.assertFalse(cl.combo_eligible(job(eco_history=[dict(kind="combo")]), M))
        self.assertFalse(cl.combo_eligible(job(spec=dict(block="b", hold_eco=dict(combo=False))), M))
        self.assertTrue(cl.combo_eligible(job(eco=dict(kind="hold", tried=True)), M))         # an earlier ECO: still eligible


class Start(unittest.TestCase):
    def test_launch(self):
        j = job()
        fleet = MagicMock()
        fleet.fits.return_value = (True, "ok")
        with patch.object(cl, "eco_paths", return_value=("/rb", "/ob")), patch.object(cl, "ship_helpers"), \
                patch.object(cl, "launch_stage") as ls, patch.object(cl, "event"), patch.object(cl, "ledger"), \
                patch.object(cl, "experiment"):
            self.assertTrue(cl.start_combo_eco(j, fleet, M))
        cmd = ls.call_args[0][2]
        self.assertIn("vtswap_eco.sh /rb /ob /r/cl/eco-combo1-vt b", cmd)
        self.assertIn("hold_eco.sh $VB $VB /r/cl/eco-combo1 b", cmd)
        self.assertIn("ECO_RB_DB=6_final.odb", cmd)
        self.assertEqual(j["eco"]["kind"], "combo")
        self.assertEqual(j["eco"]["out"], "/r/cl/eco-combo1")
        self.assertEqual(j["status"], "ECO")

    def test_waits_for_capacity(self):
        j = job()
        fleet = MagicMock()
        fleet.fits.return_value = (False, "full")
        with patch.object(cl, "eco_paths", return_value=("/rb", "/ob")), patch.object(cl, "event") as ev:
            self.assertTrue(cl.start_combo_eco(j, fleet, M))
        self.assertNotIn("eco", j)
        self.assertIn("waiting", ev.call_args[0][1])


if __name__ == "__main__":
    unittest.main()
