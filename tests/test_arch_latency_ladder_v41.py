"""The V4.1 push-the-rate ladder (tools/arch_latency_ladder_v41.py): every adopted rung obeys the user's rules
(no batch-1 slowdown at 1M or 200K, with or without MTP; inside the compute envelope), the rung-0 point
reproduces the utilisation study's design point, and the HBM comparator is given its own best tensor group."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

LX = pytest.importorskip("arch_latency_ladder_v41")
REC = ROOT / "results/arch/v41_latency_ladder.json"


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


def test_adopted_rungs_never_slow_batch1(rec):
    for r in rec["ladder"][1:]:
        if r["adopted"]:
            assert r["fits_envelope_m2"]
            for ctx in ("1048576", "200000"):
                assert r[ctx]["gain_ar"] >= -1e-4 and r[ctx]["gain_mtp"] >= -1e-4, (r["key"], ctx)


def test_ladder_is_monotone_over_adopted_rungs(rec):
    adopted = [r for r in rec["ladder"] if r["adopted"]]
    for a, b in zip(adopted, adopted[1:]):
        assert b["1048576"]["rom"]["ar"] >= a["1048576"]["rom"]["ar"] - 1e-6


def test_rung0_reproduces_the_design_point(rec):
    u = json.loads((ROOT / "results/arch/v41_utilization.json").read_text())
    dp = u["design_point"]["rows"]["1048576"]["b1"]["tokens_s_per_user"]
    assert rec["ladder"][0]["1048576"]["rom"]["ar"] == pytest.approx(dp, rel=0.01)


def test_hbm_comparator_uses_its_best_group(rec):
    grid = rec["ladder"][0]["hbm_grid_1M"]
    best = max(g["ar"] for g in grid)
    assert rec["ladder"][0]["1048576"]["hbm"]["ar"] == pytest.approx(best)
    g4 = next(g["ar"] for g in grid if g["G"] == 4 and g["m"] == 2)
    assert best > 1.5 * g4                 # a wider tensor group is the HBM machine's own best lever


def test_rom_still_beats_best_hbm(rec):
    for r in rec["ladder"]:
        for ctx in ("1048576", "200000"):
            assert r[ctx]["rom_over_hbm_ar"] > 1.5 and r[ctx]["rom_over_hbm_mtp"] > 1.5
