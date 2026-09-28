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
    # the least favourable measured path without a last-level cache on it (MI250X GCD), not the A100's
    parts = cfg["memory"]["hbm_path_total"]["measured_parts"]
    assert h["total"] == pytest.approx(parts["mi250x_gcd"]) == pytest.approx(13.64)
    assert h["total"] == max(v for k, v in parts.items() if k != "mi300a")
    assert h["die"] == pytest.approx(10.19)
    assert cfg["memory"]["die_share"]["evidence_class"] != "assumed"
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


def test_v41_stack_count_matches_the_budget(cfg):
    import arch_budget_v41 as V
    assert cfg["design_points"]["v41"]["hbm_stacks_per_die"] == V.ROM_DIE_HBM_STACKS == 4
    assert V.ROM_DIE_HBM_BPS == pytest.approx(3.6e12)


def test_cooling_limits_come_from_shipping_packages_less_their_stacks(cfg):
    L = P.cooling_limits(cfg)
    hi = cfg["memory"]["stack_share"]["stack_high_pj_per_bit"]
    # air, one die + six stacks: H200 SXM 700 W less 4.8 TB/s x 3.92 pJ/b; the least favourable of H200 / H100
    assert L["air"]["1"]["reference"] == "h200_sxm"
    assert L["air"]["1"]["die_w"] == pytest.approx(700 - 4.8e12 * 8 * hi * 1e-12)
    assert L["air"]["1"]["die_w"] == min(c["die_w"] for c in L["air"]["1"]["candidates"])
    # two dies + eight stacks: B200 HGX (air, 1,000 W) and GB200 (liquid, 1,200 W), per die
    assert L["air"]["2"]["die_w"] == pytest.approx((1000 - 8e12 * 8 * hi * 1e-12) / 2)
    assert L["liquid"]["2"]["die_w"] == pytest.approx((1200 - 8e12 * 8 * hi * 1e-12) / 2)
    # no single-reticle liquid rating exists: liquid falls back to air, and is never below it
    assert L["liquid"]["1"]["die_w"] == L["air"]["1"]["die_w"]
    for n in ("1", "2"):
        assert L["liquid"][n]["die_w"] >= L["air"][n]["die_w"]
    # the withdrawn A100-derived 407.5 W is gone from the model
    assert "w_per_mm2" not in cfg["cooling"]
    for r in cfg["cooling"]["references"].values():
        assert r["evidence_class"] == "published-spec" and "http" in r["source"] and r["quote"]


def test_every_point_is_capped_per_class_and_liquid_never_caps_lower(rec):
    for s in P.SCENARIOS:
        body = rec["scenarios"][s]
        pts = list(body["qwen3_8b_rom_8k"].values()) + [p for c in body["deepseek_v41_rom_array"]["per_context"].values()
                                                        for p in c.values()]
        for p in pts:
            cc = p["cooling_classes"]
            assert set(cc) == set(P.COOLING_CLASSES)
            assert cc["liquid"]["capped_rate"] >= cc["air"]["capped_rate"]
            assert p["capped_rate"] == cc["air"]["capped_rate"]
            for c in cc.values():
                assert c["die_w_at_cap"] <= c["die_limit_w"] * (1 + 1e-6)
                assert c["package_w_at_cap"] <= c["package_limit_w"] * (1 + 1e-6)
    classes = {r["cooling"] for r in rec["summary"]}
    assert classes == set(P.COOLING_CLASSES)


def test_design_point_rows_price_the_measured_headline(rec):
    """The adopted V4.1 design point (results/arch/v41_lanes.json design_point, collective exposure measured) is
    priced in both scenarios beside the specification model, KV in HBM charged on every point."""
    ln = json.loads((ROOT / "results/arch/v41_lanes.json").read_text())
    for s in P.SCENARIOS:
        dp = rec["scenarios"][s]["deepseek_v41_design_point"]
        assert dp["mtp_tau"] == 5.0
        for c in ("1048576", "200000"):
            p = dp["per_context"][c]
            assert p["ar_batch1"]["design_rate_tokens_s"] == pytest.approx(ln["design_point"][c]["ar"], rel=1e-5)
            assert p["mtp_batch1"]["design_rate_tokens_s"] == pytest.approx(ln["design_point"][c]["mtp"], rel=1e-5)
            assert p["ar_batch1"]["die_components_j_per_token"]["hbm_controller_phy_io"] > 0
            assert p["ar_batch1"]["stack_j_per_token"] > 0


def test_hbm_comparator_is_the_best_switched_machine_on_the_same_power_model(rec):
    """The best switched HBM comparator (results/arch/v41_hbm_switched.json: 99 dies, 4 stacks each, the tensor group
    each operating point picks there) is priced by the same function and inputs as the design point: its rates
    are the switched record's, its weights are charged to HBM (die share + stack share), and static power covers
    all 99 dies with 4 stacks' idle each."""
    sw = json.loads((ROOT / "results/arch/v41_hbm_switched.json").read_text())
    for s in P.SCENARIOS:
        hb = rec["scenarios"][s]["deepseek_v41_hbm_comparator"]
        assert hb["dies"] == sw["dies"] == 99 and hb["stacks_per_die"] == 4 and hb["packages"] == 50
        assert hb["die_static_w"]["hbm_idle_w"] == pytest.approx(4 * 2.8)
        for c in ("1048576", "200000"):
            for key, sk in P.HBM_POINTS:
                p, h = hb["per_context"][c][key], sw["energy"][c][sk]["hbm"]
                assert p["design_rate_tokens_s"] == pytest.approx(h["aggregate_tokens_s"], rel=1e-5)
                assert p["tensor_group"] == h["G"]
                assert p["die_components_j_per_token"]["weight_hbm_controller_phy_io"] > 0
                assert p["stack_j_per_token"] > 0
                assert p["energy_per_token_j"] == pytest.approx(
                    p["array_dynamic_j_per_token"] + p["stack_j_per_token"] + p["array_static_j_per_token"], rel=1e-5)


def test_rom_weights_never_touch_hbm_in_the_rom_blocks(rec):
    for s in P.SCENARIOS:
        for blk in ("deepseek_v41_rom_array", "deepseek_v41_design_point"):
            for pts in rec["scenarios"][s][blk]["per_context"].values():
                for p in pts.values():
                    assert "weight_hbm_controller_phy_io" not in p["die_components_j_per_token"]


def test_rom_over_hbm_ratios_come_from_the_two_blocks(rec):
    """Every ROM / HBM energy ratio is the quotient of the two blocks' energies (one power model), and the ROM
    wins on energy at every operating point."""
    for s in P.SCENARIOS:
        body = rec["scenarios"][s]
        for c, pts in rec["rom_over_hbm"][s].items():
            assert set(pts) == {k for k, _ in P.HBM_POINTS}
            for k, r in pts.items():
                rom = body["deepseek_v41_design_point"]["per_context"][c][k]["energy_per_token_j"]
                hbm = body["deepseek_v41_hbm_comparator"]["per_context"][c][k]["energy_per_token_j"]
                assert r["energy_hbm_over_rom"] == pytest.approx(hbm / rom, rel=1e-4)
                assert r["energy_hbm_over_rom"] > 1
    b = rec["rom_over_hbm"]["B_proposed_production"]["1048576"]
    assert 3.0 < b["ar_batch1"]["energy_hbm_over_rom"] < 4.0
    assert b["fill28"]["energy_hbm_over_rom"] > b["ar_batch1"]["energy_hbm_over_rom"]


def test_leakage_is_one_value_across_the_models(cfg):
    tech = json.loads((ROOT / "configs/hardware/technology.json").read_text())
    assert tech["power"]["static_leakage_w_per_mm2"]["logic"]["value"] == P.val(cfg["die"]["leakage_w_per_mm2"]["logic"]) == 0.1


def test_both_v41_machines_charge_their_always_on_links(rec):
    """The ROM array's die-side 112G lanes (the rack's gate C4) and the comparator's own fabric lanes, plus UCIe
    idle on every die, are static power on both machines."""
    lanes = json.loads(P.V41_LANES.read_text())["static_w"]
    sw = json.loads(P.V41_SWITCHED.read_text())
    for s in P.SCENARIOS:
        rom = rec["scenarios"][s]["deepseek_v41_design_point"]
        hbm = rec["scenarios"][s]["deepseek_v41_hbm_comparator"]
        assert rom["links_always_on"]["serdes_w_array"] == pytest.approx(lanes["rom_serdes"], rel=1e-5)   # 6 s.f. record
        assert hbm["links_always_on"]["serdes_w_per_die"] == pytest.approx(sw["hbm_static_w_per_die"]["serdes"], rel=1e-5)
        assert hbm["links_always_on"]["dies"] == sw["dies"]
        assert rom["die_static_w"]["links_always_on_w"] > 0 and hbm["die_static_w"]["links_always_on_w"] > 0
        for body, links in ((rom, rom["links_always_on"]), (hbm, hbm["links_always_on"])):
            for ctx, pts in body["per_context"].items():
                for k, r in pts.items():
                    assert r["array_links_always_on_j_per_token"] == pytest.approx(
                        links["array_w"] / r["design_rate_tokens_s"], rel=1e-4)
