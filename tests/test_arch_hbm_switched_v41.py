"""The best HBM comparator on a switched NVLink domain (tools/arch_hbm_switched_v41.py)."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/arch/v41_hbm_switched.json"


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


def test_best_group_is_the_grid_maximum(rec):
    for cfg in rec["configs"].values():
        for ctx, r in cfg.items():
            assert r["best_ar"]["rate"] == pytest.approx(max(g["ar"] for g in r["grid"]))


def test_switched_domain_beats_the_board_mesh_for_hbm(rec):
    for ctx, was in rec["board_mesh_was"].items():
        now = rec["configs"][rec["headline_config"]][ctx]
        assert now["best_ar"]["rate"] >= was["ar"] and now["best_mtp"]["rate"] >= was["mtp"]


def test_rom_still_leads(rec):
    for ctx, rows in rec["energy"].items():
        for k, v in rows.items():
            assert v["ratio_rate_per_user"] > 1.5 and v["ratio_energy_with_static"] > 1.5, (ctx, k)


def test_same_wall_chain_and_switches_on_both_machines(rec):
    sw = rec["switches_and_wall"]
    assert sw["hbm_switch_w"] > 0 and sw["rom_switch_w"] > 0 and sw["wall_factor"] > 1.2
    assert rec["alpha_s"] == pytest.approx(2 * 209e-9 + 250e-9)


def test_rom_worst_die_under_the_cooling_limit(rec):
    w = rec["rom_worst_die_w"]
    assert w["total_w"] < min(w["cooling_limit_w"].values())      # air and liquid classes (power_scenarios)


def test_kv_replicate_on_write_fits_the_stage_lanes(rec):
    kv = rec["kv_replicate_on_write"]
    assert kv["link_load_fraction"] < 0.5
