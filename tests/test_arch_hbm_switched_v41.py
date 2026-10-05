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


def test_rom_worst_die_is_the_hottest_die(rec):
    """The worst die is the HOTTEST die (the busiest stage's share of the work over the layer-die mean), not the
    array average; since the uncapped index scan's stage carries several times the mean it exceeds the air class
    at 1M saturation (power_scenarios states the per-point verdict)."""
    w = rec["rom_worst_die_w"]
    for k, d in w["dynamic_w_by_point"].items():
        f = w["hottest_die_factor_by_point"][k]["factor"]
        assert f >= 1.0 and abs(d - w["average_die_dynamic_w_by_point"][k] * f) < 1e-6 * d
    assert w["total_w"] == pytest.approx(w["static_w"] + w["dynamic_w"])
    assert w["total_w"] > w["cooling_limit_w"]["air"]


def test_kv_replicate_on_write_fits_the_stage_lanes(rec):
    kv = rec["kv_replicate_on_write"]
    assert kv["link_load_fraction"] < 0.5


def test_comparator_pays_the_link_cap_and_drafter_rule(rec):
    """The costs the ROM design point pays, on the comparator's own fabric: every aggregate is capped at its busiest
    package link (the same rule as arch_lanes_v41.link_cap), and the drafter's inputs are priced where they would
    cross a link (co-located on the comparator's G graph: 0 s, the separate-drafter placement as a sensitivity)."""
    for ctx, rows in rec["energy"].items():
        for k, v in rows.items():
            lk = v["hbm_link_cap"]
            assert lk["utilisation"] <= 1.0 + 1e-9
            assert abs(v["hbm"]["aggregate_tokens_s"] - lk["aggregate_tokens_s_uncapped"] * lk["cap"]) < 1e-6 * \
                v["hbm"]["aggregate_tokens_s"]
            dc = v["hbm_draft_conditioning"]
            if k.endswith("_mtp"):
                assert dc["seconds"] == 0.0 and dc["separate_drafter_sensitivity_s"] > 0
            else:
                assert dc is None
        assert rows["sat1024_mtp"]["hbm_link_cap"]["binds"]
