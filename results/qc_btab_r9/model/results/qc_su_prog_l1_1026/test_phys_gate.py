#!/usr/bin/env python3
"""QC-SU-PROG-L1 tests: uf_phys gating predictor wrapper (guard band, provenance, sensitivity) + per-branch sizer.
Library-dependent tests need OT_INVBUF_LIBDIR (invbuf_tt.lib / invbuf_ff.lib; fleet default below) and skip otherwise.
run: python3 -m pytest -q results/qc_su_prog_l1_1026/test_phys_gate.py"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import phys_gate as PG  # noqa: E402
import su_branch_size as SB  # noqa: E402

LIBDIR = os.environ.get("OT_INVBUF_LIBDIR", "/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor")
HAVE_LIB = (Path(LIBDIR) / "invbuf_tt.lib").exists()
K = HERE.parent / "qc_su_kits"
BTAB = (str(K / "r4/btab_m0_r4/btab_ls_k6_L3.gate.asbuilt.tcl"), str(K / "r4/btab_m0_r4/btab_ls_k6_L3.gate.asbuilt.json"),
        str(K / "r2/btab_m0.geo"))
PROG3 = (str(K / "r3/out/prog_m0_r3.gate.asbuilt.tcl"), str(K / "r3/out/prog_m0_r3.gate.asbuilt.json"), str(K / "r2/prog_m0.geo"))


def P(tt, wtt, ff, wff):
    return dict(TT_rise=dict(mean=tt, window=wtt), FF_early=dict(mean=ff, window=wff))


class GuardBand(unittest.TestCase):
    def test_band_edges(self):
        self.assertEqual(PG.verdict(P(250, 15, 202.5, 15))["verdict"], "PASS")
        self.assertEqual(PG.verdict(P(238.0, 15, 202.5, 15))["verdict"], "PASS")
        self.assertEqual(PG.verdict(P(262.0, 15, 202.5, 15))["verdict"], "PASS")
        self.assertEqual(PG.verdict(P(237.9, 15, 202.5, 15))["verdict"], "FAIL")    # inside 12.3 +-20, outside guard
        self.assertEqual(PG.verdict(P(262.1, 15, 202.5, 15))["verdict"], "FAIL")
        self.assertEqual(PG.verdict(P(250, 15, 187.5, 15))["verdict"], "PASS")
        self.assertEqual(PG.verdict(P(250, 15, 187.4, 15))["verdict"], "FAIL")
        self.assertEqual(PG.verdict(P(250, 15, 217.6, 15))["verdict"], "FAIL")

    def test_windows(self):
        self.assertEqual(PG.verdict(P(250, 20.0, 202.5, 20.0))["verdict"], "PASS")
        self.assertEqual(PG.verdict(P(250, 20.01, 202.5, 10))["verdict"], "FAIL")
        self.assertEqual(PG.verdict(P(250, 10, 202.5, 20.01))["verdict"], "FAIL")

    def test_band_values(self):
        b = PG.verdict(P(250, 1, 202.5, 1))["band"]
        self.assertEqual(b["TT_rise_mean"], [238.0, 262.0])
        self.assertEqual(b["FF_early_mean"], [187.5, 217.5])

    def test_sizer_list_calibrated_only(self):
        self.assertEqual(PG.SIZES_SIZER, ["BUFx8_ASAP7_75t_R", "BUFx10_ASAP7_75t_R", "BUFx12f_ASAP7_75t_R",
                                          "BUFx16f_ASAP7_75t_R", "BUFx24_ASAP7_75t_R"])

    def test_frozen_params(self):
        self.assertEqual(PG.PMAX, dict(alpha=0.2, beta=0.5, gslew=5.0, kleaf=1.2955))
        self.assertEqual(PG.PMIN, dict(alpha=0.2, beta=0.4, gslew=4.0, kleaf=1.2955))


@unittest.skipUnless(HAVE_LIB, "invbuf libs not present (set OT_INVBUF_LIBDIR)")
class Predict(unittest.TestCase):
    def test_reproduces_model_refit2_evalgate(self):
        # evalgate.txt (3d6754e1f4): btab_r4 pred TT rise 248.92 w22.03, FF early 188.91 w18.27; prog_r3 241.62 w25.87 / 182.30 w20.88
        o = PG.predict_file(*BTAB, LIBDIR)
        self.assertAlmostEqual(o["TT_rise"]["mean"], 248.92, places=2)
        self.assertAlmostEqual(o["TT_rise"]["window"], 22.03, places=2)
        self.assertAlmostEqual(o["FF_early"]["mean"], 188.91, places=2)
        self.assertAlmostEqual(o["FF_early"]["window"], 18.27, places=2)
        self.assertEqual(o["gate"]["verdict"], "FAIL")       # predicted TT window 22.03 > 20 (measured 17.27)
        o = PG.predict_file(*PROG3, LIBDIR)
        self.assertAlmostEqual(o["TT_rise"]["mean"], 241.62, places=2)
        self.assertAlmostEqual(o["FF_early"]["window"], 20.88, places=2)

    def test_provenance_and_sensitivity(self):
        o = PG.predict_file(*BTAB, LIBDIR)
        pv = o["provenance"]
        self.assertIn("argv", pv)
        self.assertEqual(pv["predictor_call"][1:4], list(BTAB))
        for p in list(BTAB) + [PG.U.__file__, PG.__file__]:
            self.assertIn(p, pv["sha256"])
            self.assertEqual(len(pv["sha256"][p]), 64)
        for nm in ("textbook", "ln2_fit"):
            s = o["sensitivity"][nm]
            self.assertIn(s["gate_under_these_params"], ("PASS", "FAIL"))
            self.assertIn("TT_rise_mean", s["delta_vs_gate"])
        self.assertAlmostEqual(o["sensitivity"]["textbook"]["params"]["max"]["beta"], 0.6931, places=3)

    def test_sizer_cells_only(self):
        r = SB.size(*BTAB, LIBDIR, passes=1, sizes=["BUFx8_ASAP7_75t_R", "BUFx16f_ASAP7_75t_R", "BUFx24_ASAP7_75t_R"])
        import uf_phys as U
        plan = U.Plan(BTAB[0], BTAB[2], json.load(open(BTAB[1]))["seg_um"])
        nodes = {n for n, v in plan.nodes.items() if v["kind"] == "node"}
        self.assertTrue(set(r["cells"]) == nodes)                        # only tree nodes, never root/leaf/macro
        self.assertLessEqual(r["after"]["J"], r["before"]["J"])
        self.assertLessEqual(r["after"]["max_slew"], r["slew_limit"] + 1e-6)
        with tempfile.TemporaryDirectory() as d:
            out = str(Path(d) / "s.tcl")
            SB.write_spec(BTAB[0], r["cells"], out, "test")
            import common
            a, b = common.parse_spec(BTAB[0]), common.parse_spec(out)
            self.assertEqual(set(a["tree"]), set(b["tree"]))
            for n in a["tree"]:                                           # sites + parents unchanged
                self.assertEqual((a["tree"][n]["par"], a["tree"][n]["xy"]), (b["tree"][n]["par"], b["tree"][n]["xy"]))
                self.assertEqual(b["tree"][n]["cell"], r["cells"][n])
            self.assertEqual(a["leaves"], b["leaves"])
            self.assertEqual(a["macros"], b["macros"])
            o = PG.predict_file(out, BTAB[1], BTAB[2], LIBDIR)              # sized spec re-predicts to the sizer's value
            self.assertAlmostEqual(o["TT_rise"]["window"], r["after"]["TT_rise"]["window"], places=2)
            self.assertAlmostEqual(o["FF_early"]["mean"], r["after"]["FF_early"]["mean"], places=2)


if __name__ == "__main__":
    unittest.main()
