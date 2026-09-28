"""Batch-1 power levers of the Qwen3-8B ROM reticle (tools/qwen_power_levers.py): the evaluator reproduces the
baseline, every lever input is tagged, the levers move the energy the way their mechanism says, and the committed
record reproduces from its inputs."""
import json
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
    for f in ("energy_per_token_mj", "die_energy_per_token_mj", "die_w_at_design_rate", "capped_rate",
              "design_rate_tokens_s", "stack_energy_per_token_mj"):
        assert got[f] == pytest.approx(ref[f], rel=1e-12), f
    for c in ("air", "liquid"):
        assert got["cooling_classes"][c]["capped_rate"] == pytest.approx(ref["cooling_classes"][c]["capped_rate"])


def test_baseline_energy_split_is_kv_dominated(rec):
    sp = rec["energy_split_batch1"]["B_proposed_production"]["ar_batch1"]
    assert sum(sp["fraction"].values()) == pytest.approx(1.0)
    assert sp["fraction"]["kv_streaming"] > 0.7            # the HBM die share + ring
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


def test_two_die_halves_the_layer_work_on_the_hottest_die(cfgs):
    cfg, L = cfgs
    spec = QL.levers(cfg, L)["two_die_striped_kv"]["lever"]
    b = QL.evaluate(cfg, "B_proposed_production", "ar_batch1")
    r = QL.evaluate(cfg, "B_proposed_production", "ar_batch1", spec)
    assert r["dies"] == 2
    assert 0.5 * b["die_dynamic_mj_per_token"] < r["hottest_die_dynamic_mj_per_token"] < b["die_dynamic_mj_per_token"]
    assert r["design_rate_tokens_s"] > 0.99 * b["design_rate_tokens_s"]
    assert r["cooling_classes"]["air"]["dies_per_package"] == 2


def test_dflash_at_m3_recomputed_equals_the_record(cfgs):
    cfg, _ = cfgs
    dp = cfg["design_points"]["qwen3"]
    p = QL.dflash_point_m(dp, 3)
    for k in ("block", "tokens_per_step", "step_cycles", "macs_per_step"):
        assert p[k] == dp["dflash"][k], k


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


def test_unstriped_two_die_loses_the_per_user_rate(rec):
    for s in QL.SCENARIOS:
        r = rec["levers"]["two_die_unstriped_kv"]["result"][s]["ar_batch1"]
        assert not r["per_user_rate_kept"] and r["design_rate_over_baseline"] < 0.55
        assert rec["levers"]["two_die_striped_kv"]["result"][s]["ar_batch1"]["per_user_rate_kept"]


def test_dvfs_trades_rate_for_cap_and_never_keeps_the_rate(rec):
    for name, lv in rec["levers"].items():
        if name.startswith("dvfs_"):
            for s in QL.SCENARIOS:
                r = lv["result"][s]["ar_batch1"]
                assert not r["per_user_rate_kept"]
                assert r["capped_rate"] <= r["design_rate_tokens_s"] + 1e-6


def test_hbm_die_share_requirement_is_below_every_measured_path(rec):
    need = rec["hbm_die_share_needed_for_target"]["B_proposed_production/ar_batch1"]["pj_per_bit"]
    assert 0.8 < need < 8.23          # below GH200's derived 8.23, above the modelled I/O floor
    assert rec["levers"].get("fixed_function_streaming_controller") is None   # no measured part to build it from
