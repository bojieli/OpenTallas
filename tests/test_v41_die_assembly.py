"""The V4.1 ROM array's analytical whole-die assembly (tools/v41_die_assembly.py)."""

import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v41_die_assembly", ROOT / "tools/v41_die_assembly.py")
DA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DA)

EVIDENCE = ("routed-closed", "routed-not-closed", "synthesis-only", "estimate", "analytical-macro", "derived",
            "assumed", "published")


@pytest.fixture(scope="module")
def rec():
    return DA.build()


def test_ledger_sums_and_tags_every_block(rec):
    for kind in ("layer", "head"):
        L = rec["ledger"][kind]
        assert L["die_mm2"] == 815.0
        assert math.isclose(L["placed_total_mm2"], sum(r["placed_mm2"] for r in L["rows"]))
        assert math.isclose(L["whitespace_mm2"], L["die_mm2"] - L["placed_total_mm2"])
        assert L["fits"] == (L["whitespace_mm2"] >= 0)
        for r in L["rows"]:
            assert r["evidence"].split(" ")[0] in EVIDENCE, r
            assert r["placed_mm2"] >= r["cell_area_mm2"] - 1e-9 or r["group"] == "sram"
            assert r["basis"]
    # the head die is the layer die plus the draft-window SRAM (rack C10)
    extra = rec["ledger"]["head"]["placed_total_mm2"] - rec["ledger"]["layer"]["placed_total_mm2"]
    assert math.isclose(extra, json.loads((ROOT / "results/arch/v41_rack.json").read_text())
                        ["head_draft_floorplan"]["area"]["block_mm2"], rel_tol=1e-9)


def test_engines_are_the_design_point_at_m2(rec):
    L = rec["ledger"]["layer"]
    u = L["placement_utilisation"]
    eng = {r["block"]: r["cell_area_mm2"] for r in L["rows"]}
    dp = rec["design_point"]
    pooled = sum(eng[k] for k in ("block-dot pool (FP8/FP4 weights + FP4 indexer)", "BF16 pool (BF16 weights, wo_a, "
                                  "attention)", "pool operand muxes", "HC projection (FP32 lanes)",
                                  "vector unit, light lanes", "vector unit, SFU lanes", "streaming select (4 x 16 tselect)"))
    assert math.isclose(pooled, dp["engine_cell_area_mm2_m2"], rel_tol=1e-9)
    # the ladder's top rung records the same m = 2 area
    top = json.loads((ROOT / "results/arch/v41_latency_ladder.json").read_text())["ladder"][-1]
    assert math.isclose(dp["engine_cell_area_mm2_m2"], top["area_mm2_m2"], rel_tol=1e-6)
    assert u == DA.CONST["placement_utilisation"]["value"]


def test_rom_is_capacity_times_ecc_over_the_model_density(rec):
    L = rec["ledger"]["layer"]
    cap = json.loads((ROOT / "results/arch/v41_die_placement.json").read_text())["rom_bytes_per_die"]
    dens, _ = DA.rom_density(json.loads((ROOT / "configs/hardware/technology.json").read_text()))
    assert math.isclose(L["rom_mm2"], cap * 8 * 266 / 256 / dens)
    # without the ECC word it is the analytical design's own ROM split
    if rec["analytical_split"]:
        assert math.isclose(L["rom_mm2"] * 256 / 266, rec["analytical_split"]["rom_mm2"], rel_tol=1e-6)
    rows = [r for r in L["rows"] if r["group"] == "rom"]
    assert rows[0]["held_bytes"] <= cap + 1


def test_break_even_utilisation_is_where_the_die_fills(rec):
    s = rec["ledger"]["sensitivities"]
    u = s["break_even_utilisation"]
    L = DA.ledger("layer", *DA.design_point(), util=u)
    assert abs(L["whitespace_mm2"]) < 1e-6
    assert s["n5_logic_credit"]["whitespace_mm2"] > rec["ledger"]["layer"]["whitespace_mm2"]
    assert s["m1_core"]["whitespace_mm2"] > rec["ledger"]["layer"]["whitespace_mm2"]


def test_floorplan_is_inside_the_die_with_phys_on_their_edges(rec):
    F = rec["floorplan"]["layer"]
    W, H = F["die_w_mm"], F["die_h_mm"]
    assert math.isclose(W * H, 815.0)
    for r in F["rects"]:
        assert -1e-6 <= r["x"] and r["x"] + r["w"] <= W + 1e-6, r
        assert -1e-6 <= r["y"] and r["y"] + r["h"] <= H + 1e-6, r
    hbm = [r for r in F["rects"] if r["cls"] == "phy_hbm"]
    assert len(hbm) == 4 and all(abs(r["y"]) < 1e-3 or abs(r["y"] + r["h"] - H) < 1e-3 for r in hbm)
    assert [r for r in F["rects"] if r["cls"] == "phy_ucie"][0]["x"] + [r for r in F["rects"] if r["cls"] ==
                                                                          "phy_ucie"][0]["w"] == pytest.approx(W)
    assert [r for r in F["rects"] if r["cls"] == "phy_serdes"][0]["x"] == 0
    assert F["edges"]["hbm_edge_fraction"] <= F["edges"]["hbm_max_beachfront_utilisation"]
    assert F["overfill_mm2"] == 0.0
    assert F["tiles"]["n"] == len(F["tile_centres"])


def test_long_wire_cycles_follow_the_reach(rec):
    W_ = rec["long_wires"]
    for key, m in W_["by_model"].items():
        wm = W_["wire_models"][key]
        assert math.isclose(wm["reach_mm_per_cycle"], (wm["period_ps"] - wm["flop_overhead_ps"]) / wm["ps_per_mm"])
        for name, p in m["paths"].items():
            assert p["cycles"] == math.ceil(p["mm"] / wm["reach_mm_per_cycle"])
        assert m["rate"] < m["rate_pre_wire"] and m["rate_mtp"] < m["rate_mtp_pre_wire"]
    # the routed-wire model is the slower one, so it exposes more; the headline carries it
    a, t = W_["by_model"]["asap7_routed_fit"], W_["by_model"]["tech_global_wire"]
    assert a["exposed_us_per_token"] > t["exposed_us_per_token"] > 0 and a["rate"] < t["rate"]
    assert W_["headline_model"] == "asap7_routed_fit"
    assert W_["budget_charges_on_die_wire_us"] == a["exposed_us_per_token"] > 0
    assert a["exposed_us_per_token"] <= a["charged_in_full_us"] + 1e-9
    assert not a["paths"]["rom_to_lane_in_tile"]["charged"] and not a["paths"]["kv_static_rows"]["charged"]
    assert W_["on_path_kinds"]["matvec"] > 0 and W_["on_path_kinds"]["collective"] > 0


def test_power_map_reprices_the_scenarios(rec):
    PM = rec["power"]
    add = PM["static_constants"]["always_on"]
    for sc, pts in PM["points"].items():
        for pt, v in pts.items():
            assert math.isclose(v["die_w"], sum(r["w"] for r in v["regions"].values()))
            # the dynamic part is exactly power_scenarios' dynamic part
            dyn = sum(r["dynamic_w"] for r in v["regions"].values())
            assert math.isclose(dyn + 0, v["die_w"] - sum(r["static_w"] for r in v["regions"].values()))
            # both the map and power_scenarios' die figure now charge the always-on SerDes and UCIe idle
            # (power_scenarios v41_links_static), so they differ only by the map's static re-pricing
            assert abs(v["die_w"] - v["scenario_hottest_die_w"]) < 10
            assert add["serdes_w"] + add["ucie_idle_w"] > 10
    # the map is the HOTTEST die of each point (at 1M, with the adopted stage rebalancing: the stage holding layer 14's
    # scan, S14 with MTP, a head die at batch 1 with MTP): scenario B fits the LIQUID limit (the V4.1 baseline cooling,
    # user decision 2026-09-28) at every point and the air limit at none; scenario A fails everywhere
    B = PM["points"]["B_proposed_production"]
    assert B["mtp_batch1"]["hottest_die"] == "head" and B["ar_batch1"]["hottest_die"] == "9"
    assert all(v["within_liquid_die_limit"] and not v["within_air_die_limit"] for v in B.values())
    assert all(not v["within_air_die_limit"] for v in PM["points"]["A_measured_implementation"].values())
    v = rec["verdict"]["criteria"]["power"]["cooling_by_point"]
    assert set(v) == set(B) and set(v.values()) <= {"air", "liquid", "neither"}


def test_ir_closed_form_matches_a_numeric_disk():
    """J R/2 (R^2 ln(R/a) - (R^2-a^2)/2): integrate dV = I(r) Rs / (2 pi r) dr with I(r) = J pi (R^2 - r^2)."""
    J, Rs, R, a = 2e-6, 10.0, 50.0, 10.0
    n = 200000
    h = (R - a) / n
    num = sum(J * math.pi * (R * R - (a + (i + 0.5) * h) ** 2) * Rs / (2 * math.pi * (a + (i + 0.5) * h)) * h
              for i in range(n))
    closed = J * Rs / 2 * (R * R * math.log(R / a) - (R * R - a * a) / 2)
    assert math.isclose(num, closed, rel_tol=1e-6)


def test_ir_and_clock_records(rec):
    IR = rec["ir_drop"]
    assert IR["grid_coverage_per_net"] == pytest.approx(1 / 40)
    for sc, pts in IR["points"].items():
        for pt, v in pts.items():
            assert v["within_budget"] == (v["drop_mv"] <= v["budget_mv"])
            assert math.isclose(v["m8m9_coverage_needed"], IR["grid_coverage_per_net"] * v["drop_mv"] / v["budget_mv"])
    CK = rec["clock"]
    assert CK["leaves"] <= 2 ** CK["levels"]
    for m in CK["by_wire_model"].values():
        assert m["skew_ps_if_one_tree"] == pytest.approx(m["global_insertion_ps"] * CK["measured_local"]["skew_over_insertion"])


def test_verdict_names_criteria_risks_and_missing_routes(rec):
    v = rec["verdict"]
    assert set(v["criteria"]) == {"area", "long_wire_timing", "power", "ir", "clock"}
    assert v["closes"] in ("conditionally", "not at every operating point", "no")
    assert len(v["top_risks"]) >= 5 and len(v["missing_routes"]) >= 8 and v["next_physical_steps"]
    assert rec["proposed_atlas_additions"]


def test_committed_record_and_figure_are_current(rec):
    committed = json.loads((ROOT / "results/arch/v41_die_assembly.json").read_text())
    assert committed["schema"] == DA.SCHEMA
    assert math.isclose(committed["ledger"]["layer"]["placed_total_mm2"], rec["ledger"]["layer"]["placed_total_mm2"])
    assert math.isclose(committed["long_wires"]["by_model"]["asap7_routed_fit"]["exposed_us_per_token"],
                        rec["long_wires"]["by_model"]["asap7_routed_fit"]["exposed_us_per_token"])
    assert committed["verdict"]["closes"] == rec["verdict"]["closes"]
    svg = (ROOT / "results/arch/figures/v41_die_floorplan.svg").read_text()
    assert svg.startswith("<svg") and "layer die floorplan" in svg
