"""The two power scenarios (tools/power_scenarios.py): tagged inputs, the HBM die/stack split, the floating-point
lane derivation, and the committed record reproducing from its inputs."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import power_scenarios as P  # noqa: E402

CLASSES = {"measured-ours", "published-measured", "published-spec", "assumed"}


@pytest.fixture(scope="module")
def cfg():
    return P.load_cfg()


@pytest.fixture(scope="module")
def rec():
    return json.loads(P.OUT.read_text())


def _inputs(node, path=""):
    if isinstance(node, dict):
        if "evidence_class" in node:
            yield path, node
        for k, v in node.items():
            yield from _inputs(v, f"{path}.{k}")


def test_every_input_carries_a_class_and_a_boundary(cfg):
    found = list(_inputs(cfg))
    assert len(found) >= 25
    for path, node in found:
        assert node["evidence_class"] in CLASSES, path
        assert node.get("boundary"), path
        assert node.get("source"), path
    assert set(cfg["evidence_classes"]) == CLASSES


def test_hbm_split_counts_every_joule_once_and_charges_the_controller_to_the_die(cfg):
    h = P.hbm_split(cfg)
    assert h["die"] + h["stack"] == pytest.approx(h["total"])
    assert h["total"] == pytest.approx(13.11)
    # the stack keeps only in-DRAM energy (O'Connor: activation 1.21 + data movement 2.24)
    assert h["stack"] == pytest.approx(1.21 + 2.24)
    assert h["stack"] <= h["stack_high"] < 4.0
    # the withdrawn allocation put 12.31 pJ/bit in the stacks; the die now carries the controller, PHY and I/O
    assert h["die"] > 0.8 * 10


def test_keller_is_an_integer_lower_bound_not_the_lane(cfg):
    lb = cfg["mac_lane"]["bounds"]["integer_lower_bound"]
    assert "INTEGER" in lb["boundary"] and "24-bit partial sums" in lb["boundary"]
    for fmt, e in cfg["mac_lane"]["scenario_B"]["per_mac"].items():
        assert e["value"] > 10 * lb["value"], fmt
    tech = json.loads((ROOT / "configs/hardware/technology.json").read_text())
    fp4 = tech["energy"]["mac_energy_j_per_op"]["fp4"]
    assert "NOT a floating-point measurement" in fp4["boundary"]


def test_scenario_b_lane_carries_an_fp32_add_per_product(cfg):
    c = cfg["mac_lane"]["scenario_B"]["components"]
    add = c["fp32_add"]["value"]
    pm = cfg["mac_lane"]["scenario_B"]["per_mac"]
    assert pm["w4a8"]["value"] == pytest.approx(c["int8_mult"]["value"] + add)
    assert pm["bf16"]["value"] == pytest.approx(c["bf16_mult"]["value"] + add)
    assert pm["fp8"]["value"] == pytest.approx(c["bf16_mult"]["value"] + add)   # wider multiplier: upper bound
    assert pm["fp32"]["value"] == pytest.approx(c["fp32_mult"]["value"] + add)
    # and it is 5x the W4A8 input the Qwen production model charged per MAC
    assert pm["w4a8"]["value"] >= 5 * cfg["mac_lane"]["scenario_B"]["was"]["w4a8_pj_per_mac_in_qwen_production_model"]


def test_scenario_a_is_the_routed_lane(cfg):
    sig = json.loads((ROOT / "results/physical_abi3/asap7/signoff/energy_per_token.json").read_text())["architectures"]
    a = cfg["mac_lane"]["scenario_A"]
    assert a["qwen3"]["value"] == sig["qwen3_8b_rom_reticle"]["pj_per_mac"]["matrix_engine_logic_pj_per_mac"]
    assert a["v41"]["value"] == sig["deepseek_v41_rom_array_die"]["pj_per_mac"]["matrix_engine_logic_pj_per_mac"]
    for fmt in ("w4a8", "bf16"):
        assert P.mac_pj(cfg, "A_measured_implementation", "qwen3", fmt) == a["qwen3"]["value"]


def test_cap_arithmetic():
    c = P._cap(400.0, 100.0, 0.01, 50000.0)
    assert c["thermal_rate_limit"] == pytest.approx(30000.0)
    assert c["binds"] and c["capped_rate"] == pytest.approx(30000.0)
    assert not P._cap(400.0, 100.0, 0.01, 20000.0)["binds"]


def test_record_reproduces(rec):
    fresh = P._round(P.build())
    assert rec["inputs"] == fresh["inputs"], "power_scenarios.json is stale: rerun tools/power_scenarios.py"
    assert rec["summary"] == json.loads(json.dumps(fresh["summary"]))


def test_scenario_a_is_hotter_than_b_and_the_die_power_is_self_consistent(rec):
    A, B = (rec["scenarios"][s] for s in P.SCENARIOS)
    for k in ("ar_batch1", "dflash"):
        a, b = A["qwen3_8b_rom_8k"][k], B["qwen3_8b_rom_8k"][k]
        assert a["energy_per_token_mj"] > b["energy_per_token_mj"]
        assert a["capped_rate"] <= b["capped_rate"]
        static = sum(a["die_static_w"].values())
        assert a["die_w_at_design_rate"] == pytest.approx(static + a["die_dynamic_mj_per_token"] / 1e3 * a["design_rate_tokens_s"],
                                                          rel=1e-4)
    for ctx in ("1048576", "200000"):
        for k, a in A["deepseek_v41_rom_array"]["per_context"][ctx].items():
            b = B["deepseek_v41_rom_array"]["per_context"][ctx][k]
            assert a["hottest_die_w"] > b["hottest_die_w"]
            assert a["capped_rate"] <= b["capped_rate"] <= b["design_rate_tokens_s"]


def test_old_allocation_understates_die_power(rec):
    new = rec["scenarios"]["B_proposed_production"]["qwen3_8b_rom_8k"]["ar_batch1"]
    old = rec["sensitivities"]["B_old_hbm_allocation_die_0p8"]["qwen3_8b_rom_8k"]["ar_batch1"]
    assert old["energy_per_token_mj"] == pytest.approx(new["energy_per_token_mj"], rel=1e-6)   # same joules
    assert old["die_w_at_design_rate"] < new["die_w_at_design_rate"]                          # moved to the stacks
