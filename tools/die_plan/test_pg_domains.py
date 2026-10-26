#!/usr/bin/env python3
"""HBM-PG 10-26: the die PG model (die_infra.pg_grid + pg_rects) with die.pg.domains (OWNER decision 7 PHY supply)
must never put same-layer stripes of different nets (VDD / VDDPHY / VSS) on top of, or within the ASAP7 LEF spacing
of, each other.  Runs on every die's committed plan (QC, KV, S81, S81 head, HBM) and on a synthetic PHY window.

  python3 -m pytest tools/die_plan/test_pg_domains.py"""
import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import die_infra as DI  # noqa: E402
import die_clock_128 as C128  # noqa: E402
import schema as S  # noqa: E402

DIES = {"QC": "physical/die_plan/qwen_compute/die_plan.json",
        "KV": "physical/die_plan/qwen_kvsys/die_plan.json",
        "S81": "physical/die_plan/s81/die_plan.json",
        "S81_HEAD": "physical/die_plan/s81_head/die_plan.json",
        "HBM": "physical/die_plan/hbm_arch/B2n/die_plan.json"}
LAYERS = {"M8": {"dir": "H", "pitch_um": 0.08}, "M9": {"dir": "V", "pitch_um": 0.08}}
CORE = [dict(layer="M8", width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=["VDD", "VSS"]),
        dict(layer="M9", width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=["VDD", "VSS"])]
PHY = [dict(g, width_um=1.92, nets=["VDDPHY", "VSS"]) for g in CORE]


def synth(rect=(0.0, 100.3, 70.1, 200.0)):
    """a 300 x 200 um die with one PHY window on its W edge, the HBM r8 form (same pitch/offset, 1.92-um stripes,
    rect edges off the 4.32-um phase)."""
    die = {"outline_um": [300.0, 200.0],
           "pg": {"grid": copy.deepcopy(CORE),
                  "domains": [dict(name="phy_w", nets=["VDDPHY", "VSS"], rect_um=list(rect), grid=copy.deepcopy(PHY))]}}
    return SimpleNamespace(W=300.0, H=200.0, name="t", layers=LAYERS, die=die)


def old_overlay(P):
    """the pre-fix model (die_clock_128.pg_grid on main fec963a5e): full-die core rows + domain rows on a
    region-local phase."""
    pg = P.die["pg"]
    rows = [dict(g) for g in pg["grid"]]
    for d in pg["domains"]:
        rows += [dict(g, rect_um=list(d["rect_um"])) for g in d["grid"]]
    return rows


class T(unittest.TestCase):
    def test_lef_spacing_table(self):
        self.assertEqual(DI.pg_spacing(0.48), 0.04)
        self.assertEqual(DI.pg_spacing(0.6), 0.5)
        self.assertEqual(DI.pg_spacing(1.92), 1.0)
        self.assertEqual(DI.pg_spacing(1.92, 1.0), 0.04)     # short parallel run
        self.assertEqual(DI.pg_spacing(1.92, 0.0), 0.04)     # end to end

    def test_checker_catches_the_r8_defect(self):
        # the 10-26 HBM r8 defect class: VDDPHY / VSS PHY stripes overlaid on the full-length core grid
        P = synth()
        c = DI.pg_conflicts(DI.pg_rects(P, old_overlay(P)))
        self.assertGreater(c["shorts"], 0)
        # VDD vs VDDPHY is a different-net short too (the clock-128 ODB check skipped VDD* pairs)
        r = [("VDD", "M8", 0, 10, 50, 10.48), ("VDDPHY", "M8", 40, 10.2, 60, 12.12)]
        self.assertEqual(DI.pg_conflicts(r)["shorts"], 1)
        # wide-metal spacing: 1.92 beside 0.48 over a long run needs 1.0 um, 0.5 um gap fails
        r = [("VSS", "M8", 0, 10, 50, 10.48), ("VDDPHY", "M8", 0, 10.98, 50, 12.9)]
        self.assertEqual(DI.pg_conflicts(r)["spacing"], 1)
        r = [("VSS", "M8", 0, 10, 50, 10.48), ("VDDPHY", "M8", 0, 11.48, 50, 13.4)]
        self.assertEqual(DI.pg_conflicts(r)["spacing"], 0)

    def test_synthetic_window_clean_and_die_phase(self):
        P = synth()
        R = DI.pg_rects(P, DI.pg_grid(P))
        c = DI.pg_conflicts(R)
        self.assertEqual((c["shorts"], c["spacing"]), (0, 0), c["examples"])
        x0, y0, x1, y1 = P.die["pg"]["domains"][0]["rect_um"]
        phy = [r for r in R if r[0] == "VDDPHY"]
        self.assertTrue(phy)
        for n, L, a, b, cc, d in R:
            centre = (b + d) / 2 if L == "M8" else (a + cc) / 2
            k = round((centre - 4.32) / 4.32)
            self.assertAlmostEqual(centre, 4.32 + 4.32 * k, places=6)          # die phase, every region
            self.assertEqual(n == "VSS", k % 2 == 1)                         # net parity: power even, VSS odd
            inside = a >= x0 - 1e-9 and cc <= x1 + 1e-9 and b >= y0 - 1e-9 and d <= y1 + 1e-9
            if n == "VDDPHY":
                self.assertTrue(inside)
            if n == "VDD":                                                   # core VDD never enters the window
                self.assertFalse(a < x1 and x0 < cc and b < y1 and y0 < d)
        # the stripe extents themselves are pdngen's (region cut + halo + trim): test_pdn_model_match.py

    def test_plan_without_domains_unchanged(self):
        P = S.Plan(S.load(ROOT / DIES["QC"]))
        self.assertFalse(P.die.get("pg", {}).get("domains"))
        self.assertEqual(DI.pg_grid(P), P.die["pg"]["grid"])
        self.assertEqual(C128.pg_grid(P), P.die["pg"]["grid"])

    def test_four_die_plans_no_pg_overlap(self):
        for die, rel in DIES.items():
            with self.subTest(die=die):
                P = S.Plan(S.load(ROOT / rel))
                R = DI.pg_rects(P, C128.pg_grid(P))
                c = DI.pg_conflicts(R)
                self.assertEqual((c["shorts"], c["spacing"]), (0, 0), f"{die}: {c['examples'][:2]}")
                doms = P.die.get("pg", {}).get("domains") or []
                for n in {n for d in doms for n in d["nets"]}:
                    self.assertTrue(any(r[0] == n for r in R), f"{die}: no {n} stripe")


if __name__ == "__main__":
    unittest.main()
