"""The best HBM comparator, fully derived at its own tensor group (tools/arch_hbm_best_v41.py): at G = 4 it agrees
with the budget model's comparator, a wide group is its best choice, and the ROM array still leads on rate and on
energy with static power at every operating point."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

H = pytest.importorskip("arch_hbm_best_v41")
REC = ROOT / "results/arch/v41_hbm_best.json"


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


def test_g4_matches_the_budget_models_comparator(rec):
    """The re-derived G = 4 comparator reproduces the budget model's own (surgery-free) HBM pricing within 1%."""
    lad = json.loads((ROOT / "results/arch/v41_latency_ladder.json").read_text())
    g4_budget = next(g["ar"] for g in lad["ladder"][0]["hbm_grid_1M"] if g["G"] == 4)
    g4 = next(g["ar"] for g in rec["rungs"]["start"]["grid"]["1048576"] if g["G"] == 4)
    assert g4 == pytest.approx(g4_budget, rel=0.01)


def test_wide_group_is_the_comparators_best(rec):
    for tag in ("start", "top"):
        for ctx in ("1048576", "200000"):
            h = rec["rungs"][tag]["hbm"][ctx]
            assert h["ar_G"] >= 16 and h["mtp_G"] >= 16
            grid = rec["rungs"][tag]["grid"][ctx]
            assert h["ar"] == pytest.approx(max(g["ar"] for g in grid))


def test_rom_leads_the_best_comparator_everywhere(rec):
    for tag in ("start", "top"):
        for ctx in ("1048576", "200000"):
            for pt, v in rec["rungs"][tag]["energy"][ctx].items():
                assert v["ratio_rate_per_user"] > 1.5, (tag, ctx, pt)
                assert v["ratio_energy_with_static"] > 1.5, (tag, ctx, pt)
