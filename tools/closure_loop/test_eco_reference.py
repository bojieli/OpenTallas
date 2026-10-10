"""ECO REFERENCE (drive-0849 2026-10-09): every ECO launcher times with the verdict's post-SDC set (incl. a spec post-SDC
baked into the route's in-run w18_extra.sdc); combo installs add the LVT libraries to the routed re-STA; a combo result
that misses hold by < 5 ps gets one stacked hold pass; the hold-stall guard tries the combo ECO first."""
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import closure_loop as cl

M = dict(ss_ps=-11.35, ff_ps=4.0, drc=0, post_sdc=[cl.IOREF_SDC], sdc_name="6_final.sdc", orfs_dir="/R/routes/L/work/orfs")


def job(**kw):
    j = dict(name="j", host="h", run="/R", attempt=1, events=[],
             spec=dict(block="b", hold_eco={}, verdict=dict(post_sdc=["physical/x/signoff.sdc"], macros=[])))
    j.update(kw)
    return j


class PostSdc(unittest.TestCase):
    def test_baked_first_ioref_last(self):
        with patch.object(cl, "baked_post_sdcs", return_value=["physical/x/signoff.sdc"]), patch.object(cl, "event"):
            self.assertEqual(cl.eco_post_sdcs(job(), M), ["physical/x/signoff.sdc", cl.IOREF_SDC])

    def test_vtswap_uses_it(self):
        fleet = MagicMock(); fleet.fits.return_value = (True, "ok")
        j = job()
        with patch.object(cl, "eco_paths", return_value=("/rb", "/ob")), patch.object(cl, "ship_helpers"), \
                patch.object(cl, "launch_stage") as ls, patch.object(cl, "event"), patch.object(cl, "ledger"), \
                patch.object(cl, "experiment"), patch.object(cl, "baked_post_sdcs", return_value=["physical/x/signoff.sdc"]):
            cl.start_vtswap_eco(j, fleet, M)
        self.assertIn("physical/x/signoff.sdc physical/common_flow/io_ref_routed.sdc", ls.call_args[0][2])

    def test_combo_uses_it(self):
        fleet = MagicMock(); fleet.fits.return_value = (True, "ok")
        j = job()
        with patch.object(cl, "eco_paths", return_value=("/rb", "/ob")), patch.object(cl, "ship_helpers"), \
                patch.object(cl, "launch_stage") as ls, patch.object(cl, "event"), patch.object(cl, "ledger"), \
                patch.object(cl, "experiment"), patch.object(cl, "baked_post_sdcs", return_value=["physical/x/signoff.sdc"]):
            cl.start_combo_eco(j, fleet, dict(M, ff_ps=-7.0))
        self.assertEqual(ls.call_args[0][2].count("physical/x/signoff.sdc"), 2)   # VT-swap and hold stages
        self.assertEqual(j["eco"]["post_sdc"], ["physical/x/signoff.sdc", cl.IOREF_SDC])


class ComboHoldRetry(unittest.TestCase):
    def test_eligible(self):
        self.assertTrue(cl.combo_hold_retry_eligible(dict(ss_ps=4.89, ff_ps=-0.13, drc=0)))
        self.assertFalse(cl.combo_hold_retry_eligible(dict(ss_ps=-1.0, ff_ps=-0.13, drc=0)))
        self.assertFalse(cl.combo_hold_retry_eligible(dict(ss_ps=4.89, ff_ps=-6.0, drc=0)))

    def test_launch_once(self):
        fleet = MagicMock(); fleet.fits.return_value = (True, "ok")
        prev = dict(kind="combo", rb="/rb", ob="/ob", out="/R/cl/eco-combo1", post_sdc=["p.sdc"], sdc_name="6_final.sdc",
                    result=dict(ss_ps=4.89, ff_ps=-0.13))
        j = job(eco=prev)
        with patch.object(cl, "ship_helpers"), patch.object(cl, "launch_stage") as ls, patch.object(cl, "event"):
            self.assertTrue(cl.start_combo_hold_retry(j, fleet, M, prev))
            cmd = ls.call_args[0][2]
            self.assertIn("/R/cl/eco-combo1/orfs/results/asap7/*/base", cmd)
            self.assertIn("hold_eco.sh $VB $VB /R/cl/eco-combo1-h b p.sdc", cmd)
            self.assertEqual(j["eco"]["kind"], "combo_hold")
            self.assertFalse(cl.start_combo_hold_retry(j, fleet, M, prev))     # once


class InstallLvt(unittest.TestCase):
    def test_lvt_lines(self):
        with tempfile.TemporaryDirectory() as d:
            orfs = os.path.join(d, "R/routes/L/work/orfs"); os.makedirs(orfs)
            rb = os.path.join(orfs, "results/asap7/dd/base")
            P = "/OpenROAD-flow-scripts/flow/platforms/asap7"
            t = os.path.join(orfs, "w18_sta_ss.tcl")
            open(t, "w").write(f"read_lef {P}/lef/asap7sc7p5t_28_R_1x_220121a.lef\n"
                               f"read_liberty {P}/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz\n")
            j = job(eco=dict(kind="combo", rb=rb, ob=rb, out="/x")); j["spec"]["verdict"]["corner_sta"] = "/x/cs.json"
            with patch.object(cl, "subst", side_effect=lambda s, j: s):
                cmd = cl.eco_install_cmd(j)
            line = [l for l in cmd.split("\n") if "w18_sta_ss.tcl" in l][0]
            subprocess.run(["bash", "-c", line], check=True)
            txt = open(t).read()
            self.assertIn("asap7sc7p5t_AO_LVT_TT_nldm_211120.lib.gz", txt)
            self.assertIn("asap7sc7p5t_28_L_1x_220121a.lef", txt)
            subprocess.run(["bash", "-c", line], check=True)                   # idempotent
            self.assertEqual(open(t).read().count("_LVT_"), 1)


if __name__ == "__main__":
    unittest.main()
