"""Batch-1 power levers of the Qwen3-8B ROM package (tools/qwen_power_levers.py): the evaluator reproduces the
O4 baseline (two reticles, tensor-parallel 2, 8-bit weights, 8 stacks), every lever input is tagged, the levers move
the energy the way their mechanism says, and the committed record reproduces from its inputs."""
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import power_scenarios as PS  # noqa: E402
import qwen_power_levers as QL  # noqa: E402

CLASSES = {"measured-ours", "published-measured", "published-spec", "assumed"}


@pytest.fixture(scope="module")
def cfgs():
    return QL.load()


@pytest.fixture(scope="module")
def rec():
    return json.loads(QL.OUT.read_text())


def _inputs(node, path=""):
    if isinstance(node, dict):
        if "evidence_class" in node:
            yield path, node
        for k, v in node.items():
            yield from _inputs(v, f"{path}.{k}")


def test_every_lever_input_carries_a_class_boundary_and_source(cfgs):
    _, L = cfgs
    found = list(_inputs(L))
    assert len(found) >= 8
    for path, node in found:
        assert node["evidence_class"] in CLASSES, path
        assert node.get("boundary"), path
        assert node.get("source"), path


@pytest.mark.parametrize("scenario", QL.SCENARIOS)
@pytest.mark.parametrize("key", QL.KEYS)
def test_no_lever_is_the_baseline(cfgs, scenario, key):
    cfg, _ = cfgs
    ref = PS.qwen_point(cfg, scenario, key)
    got = QL.evaluate(cfg, scenario, key)
    for f in ("energy_per_token_mj", "die_energy_per_token_mj", "die_dynamic_mj_per_token", "die_w_at_design_rate",
              "package_dies_w_at_design_rate", "capped_rate", "design_rate_tokens_s", "stack_energy_per_token_mj",
              "stacks_w_high"):
        assert got[f] == pytest.approx(ref[f], rel=1e-12), f
    assert set(got["die_components_mj_per_token"]) == set(ref["die_components_mj_per_token"])
    for c, v in ref["die_components_mj_per_token"].items():
        assert got["die_components_mj_per_token"][c] == pytest.approx(v, rel=1e-12), c
    for c, v in ref["die_static_w"].items():
        assert got["die_static_w"][c] == pytest.approx(v, rel=1e-12), c
    assert got["dies"] == ref["dies_per_package"] == 2
    for c in ("air", "liquid"):
        for f in ("capped_rate", "die_limit_w", "package_limit_w", "dies_per_package", "bound_by"):
            assert got["cooling_classes"][c][f] == pytest.approx(ref["cooling_classes"][c][f]), (c, f)


def test_baseline_charges_the_package(cfgs):
    cfg, _ = cfgs
    dp = cfg["design_points"]["qwen3"]
    r = QL.evaluate(cfg, "B_proposed_production", "ar_batch1")
    assert r["die_components_mj_per_token"]["ucie_exchange"] > 0
    assert r["die_w_at_design_rate"] == pytest.approx(r["package_dies_w_at_design_rate"] / dp["dies_per_package"])
    assert r["areas_package_mm2"]["total"] <= dp["dies_per_package"] * cfg["cooling"]["die_mm2"]


def test_baseline_energy_split_is_kv_dominated(rec):
    sp = rec["energy_split_batch1"]["B_proposed_production"]["ar_batch1"]
    assert sum(sp["fraction"].values()) == pytest.approx(1.0)
    assert max(sp["fraction"], key=sp["fraction"].get) == "kv_streaming"   # the HBM die share + ring
    assert sp["fraction"]["kv_streaming"] > 0.5
    assert sp["fraction"]["kv_streaming"] > 5 * sp["fraction"]["weights"]


def test_resident_kv_lowers_die_energy_and_keeps_the_rate(cfgs):
    cfg, L = cfgs
    rd = QL.val(L["sram"]["resident_read_j_per_byte"])
    b = QL.evaluate(cfg, "B_proposed_production", "ar_batch1")
    r = QL.evaluate(cfg, "B_proposed_production", "ar_batch1",
                    dict(resident_kv_bytes=100e6, resident_read_j_per_byte=rd, kv_sram_mm2=10.0))
    assert r["design_rate_tokens_s"] == pytest.approx(b["design_rate_tokens_s"])
    assert r["die_dynamic_mj_per_token"] < b["die_dynamic_mj_per_token"]
    # the saving is the HBM die share less the SRAM read (plus the new rows written), per resident byte
    per_byte = 8 * PS.hbm_split(cfg)["die"] * 1e-12 - rd
    saved = (b["die_dynamic_mj_per_token"] - r["die_dynamic_mj_per_token"]) * 1e-3
    new_rows = 2 * 36 * 8 * 128 * rd
    assert saved == pytest.approx(100e6 * per_byte - new_rows, rel=1e-9)


def test_kv_sram_levers_fit_the_package(rec, cfgs):
    cfg, _ = cfgs
    silicon = cfg["design_points"]["qwen3"]["dies_per_package"] * cfg["cooling"]["die_mm2"]
    for name, lv in rec["levers"].items():
        if name.startswith("kv_sram_"):
            a = lv["result"]["B_proposed_production"]["ar_batch1"]["areas_package_mm2"]
            assert a["total"] == pytest.approx(silicon, abs=0.01), name
            assert lv["silicon_mm2"] == silicon and lv["dies"] == 2


def test_dflash_at_design_m_recomputed_equals_the_record(cfgs):
    cfg, _ = cfgs
    dp = cfg["design_points"]["qwen3"]
    p = QL.dflash_point_m(dp, dp["area_mm2"]["lane_multiplier_m"])
    for k in ("block", "tokens_per_step", "step_cycles", "macs_per_step"):
        assert p[k] == dp["dflash"][k], k


def test_dflash_at_m1_recomputed_equals_the_record(cfgs):
    cfg, _ = cfgs
    dp = cfg["design_points"]["qwen3"]
    p = QL.dflash_point_m(dp, 1)
    b = json.loads(PS.DFLASH_REC.read_text())["rom"][f"{dp['context']}/fp8/m1"]["best"]
    for k in ("block", "tokens_per_step", "step_cycles"):
        assert p[k] == b[k], k


def test_dflash_is_not_priced_on_the_legacy_basis(rec):
    assert not hasattr(QL, "DFLASH_BASIS")
    assert "design_basis" in rec["timing_basis"]["source"]
    assert not any("dflash_timing_basis" in k for k in rec["inputs"])


def test_dflash_amortises_kv(rec):
    a = rec["dflash_kv_amortisation"]
    assert a["ratio_dflash_over_ar"] == pytest.approx((1 + 5 / 36) / a["tokens_per_step"])
    assert a["ratio_dflash_over_ar"] < 0.55


def test_levers_do_not_touch_the_baseline_record(rec):
    base = json.loads(PS.OUT.read_text())
    for s in QL.SCENARIOS:
        for k in QL.KEYS:
            assert rec["baseline"][s][k]["capped_rate"] == pytest.approx(
                base["scenarios"][s]["qwen3_8b_rom_8k"][k]["capped_rate"], rel=1e-5)


def test_record_reproduces(rec):
    assert json.loads(json.dumps(PS._round(QL.build()))) == rec


def test_two_die_levers_are_superseded_by_the_baseline(rec):
    assert not any(n.startswith("two_die") for n in rec["levers"])
    assert "3_two_die_package" in rec["superseded_levers"]


def test_lane_trades_keep_ar_and_cost_dflash(rec):
    for name, lv in rec["levers"].items():
        if name.startswith("kv_sram_for_"):
            for s in QL.SCENARIOS:
                assert lv["result"][s]["ar_batch1"]["per_user_rate_kept"]
                assert not lv["result"][s]["dflash"]["per_user_rate_kept"]     # the multiplier is the DFlash lever


def test_dvfs_trades_rate_for_cap_and_never_keeps_the_rate(rec):
    assert rec["dvfs_sweep"]["basis"]["highest_f_ratio_still_compute_bound"] >= 1.0
    for name, lv in rec["levers"].items():
        if name.startswith("dvfs_"):
            for s in QL.SCENARIOS:
                r = lv["result"][s]["ar_batch1"]
                assert not r["per_user_rate_kept"]
                assert r["capped_rate"] <= r["design_rate_tokens_s"] + 1e-6


def test_hbm_die_share_requirement_is_below_the_baseline_and_above_the_io_floor(rec):
    need = rec["hbm_die_share_needed_for_target"]["B_proposed_production/ar_batch1"]["pj_per_bit"]
    assert 0.8 < need < 10.19          # above the modelled I/O floor, below the charged MI250X-derived die share
    assert rec["levers"].get("fixed_function_streaming_controller") is None   # no measured part to build it from


def test_target_is_the_ar_design_rate(rec):
    assert rec["target_tokens_s"] == pytest.approx(
        rec["baseline"]["B_proposed_production"]["ar_batch1"]["design_rate_tokens_s"])
    assert math.isfinite(rec["package_slack_mm2"]) and rec["package_slack_mm2"] > 0
