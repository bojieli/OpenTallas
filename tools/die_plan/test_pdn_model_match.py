#!/usr/bin/env python3
"""PDN-ONE 10-26 (COORD RULING HBM-PG ASK, one PDN rule): the plan's PG rows are the single source of the real PDN
scripts and of the die_infra PG model, and the model reproduces pdngen.

testdata/pdn_synth_pdngen.txt is the real M8/M9 dump (dbu) of OpenROAD 26Q3-1510-g6cb3f2b704 (openroad/orfs:asap7lock)
pdngen on pg_regions.pdn_tcl of SYNTH below (pdn.tcl sha256 SYNTH_TCL_SHA); re-record it with pdn_model_match.py when
the script text changes on purpose.

  python3 -m pytest tools/die_plan/test_pdn_model_match.py"""
import copy
import hashlib
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_infra as DI  # noqa: E402
import die_trial  # noqa: E402
import pdn_model_match as M  # noqa: E402
import pg_regions as G  # noqa: E402

CORE = [dict(layer="M8", width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=["VDD", "VSS"]),
        dict(layer="M9", width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=["VDD", "VSS"])]
PHY = [dict(g, width_um=1.92, nets=["VDDPHY", "VSS"]) for g in CORE]
SYNTH = {"outline_um": [300.0, 200.0],
         "pg": {"grid": CORE, "domains": [
             dict(name="phy_w", nets=["VDDPHY", "VSS"], rect_um=[0.0, 100.3, 70.1, 200.0], grid=PHY),
             dict(name="phy_c", nets=["VDDPHY", "VSS"], rect_um=[150.37, 40.11, 201.5, 90.2], grid=PHY)]}}
SYNTH_TCL_SHA = "a71fa13c005603e8792b6c5bd776fa4c628f1ba45967c6db295b6300cdcff093"
LAYERS = {"M8": {"dir": "H", "pitch_um": 0.08}, "M9": {"dir": "V", "pitch_um": 0.08}}


def plan(die):
    die = copy.deepcopy(die)
    return SimpleNamespace(W=die["outline_um"][0], H=die["outline_um"][1], name="t", layers=LAYERS, die=die)


class T(unittest.TestCase):
    def test_script_is_the_recorded_one(self):
        self.assertEqual(hashlib.sha256(G.pdn_tcl(copy.deepcopy(SYNTH)).encode()).hexdigest(), SYNTH_TCL_SHA)

    def test_model_matches_real_pdngen(self):
        real = M.load_dump(HERE / "testdata" / "pdn_synth_pdngen.txt")
        # pdngen-exact cases inside: VSS M9 dropped within its halo of the next region, a thin core band whose
        # single-crossing VSS pieces are removed, inner ends trimmed to the last via, die-edge ends kept
        c = M.compare(real, M.model_dbu(plan(SYNTH)))
        self.assertEqual(c["verdict"], "MATCH", c)
        self.assertEqual(c["real_rects"], 330)

    def test_exact_coordinates_and_parity(self):
        die = copy.deepcopy(SYNTH)
        die["outline_um"] = [28399.68, 17141.76]
        die["pg"]["domains"][1]["rect_um"] = [13328.36, 0.0, 14055.688, 1113.64]
        t = G.pdn_tcl(die)
        self.assertIn("round(13328.36*$dbu)", t)                 # %g printed 13328.4 (phase drift 0.04 um)
        self.assertIn("round(28399.68*$dbu)", t)                 # and 28399.7: region beyond the core
        self.assertNotIn("-voltage_domains {ot_pg_0} -starts_with", t)   # no hard-coded grid parity
        for line in t.splitlines():
            if line.startswith("add_pdn_stripe"):
                self.assertRegex(line, r"-starts_with (POWER|GROUND)$")
        # core region at the die origin: VDD (nets[0]) on offset 4.32 = POWER first, as die.pg.grid says
        self.assertIn("add_pdn_stripe -grid ot_pg_0 -layer M8 -width 0.48 -pitch 8.64 -offset 4.32 -spacing 3.84 "
                      "-starts_with POWER", t)

    def test_every_stripe_on_die_lattice(self):
        for n, L, x0, y0, x1, y1 in G.model_rects(copy.deepcopy(SYNTH)):
            c2 = (x0 + x1) if L == "M9" else (y0 + y1)           # 2 x centre, dbu
            k, r = divmod(c2 - 2 * 4320, 8640)
            self.assertEqual(r, 0)
            self.assertEqual(n == "VSS", k % 2 == 1)

    def test_trial_kit_builds_vddphy(self):
        P = plan(SYNTH)
        t = die_trial.psm_pdn_tcl(P)
        self.assertIn("-power VDDPHY", t)
        self.assertIn("-pin_pattern {^VDDPHY$}", t)
        self.assertIn(G.pdn_tcl(dict(P.die, outline_um=[P.W, P.H])).rstrip("\n"), t)
        Q = plan(dict(SYNTH, pg=dict(grid=CORE)))
        t = die_trial.psm_pdn_tcl(Q)
        self.assertNotIn("VDDPHY", t)
        self.assertIn("-offset 4.32 -spacing 3.84 -starts_with POWER", t)

    def test_pg_grid_is_the_model(self):
        P = plan(SYNTH)
        R = DI.pg_rects(P, DI.pg_grid(P))
        self.assertEqual(sorted((n, L) + tuple(int(round(v)) for v in r) for n, L, *r in G.model_rects(P.die)),
                         sorted((n, L) + tuple(int(round(v * 1000)) for v in r) for n, L, *r in R))
        c = DI.pg_conflicts(R)
        self.assertEqual((c["shorts"], c["spacing"]), (0, 0), c["examples"])


if __name__ == "__main__":
    unittest.main()
