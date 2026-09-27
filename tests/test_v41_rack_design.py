"""Physical feasibility gates for the proposed V4.1 rack layout."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v41_rack_design", ROOT / "tools/v41_rack_design.py")
rack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rack)


def test_rack_layout_respects_package_and_rack_limits():
    record = rack.build()
    counts = record["logical"]["counts"]
    assert counts["total"] == 188
    assert counts["packages"] == 94
    assert counts["hbm_stacks"] == sum(d["hbm_stacks"] for d in record["logical"]["dies"])
    assert counts["hbm_stacks"] in (448, 464)  # 464 once the head dies carry 4 stacks (spec C10 ruling)
    assert record["lanes"]["fits"]
    assert record["lanes"]["total"] == record["lanes"]["available"]
    assert record["elevation"]["fits"]
    assert record["power"]["shelves"]["fits"]
    assert all(link["within_reach"] for link in record["links"]["stage_links"])
    assert all(tier["within_reach"] for tier in record["links"]["tiers"])
    placement = record["logical"]
    assert placement["embedding_dies"] == [112, 113, 114, 115]
    assert sum(d.get("embedding_bytes", 0) for d in placement["dies"]) == placement["bytes"]["embed"]
    assert all(d["weight_bytes"] + d.get("engram_spill_bytes", 0) <= placement["per_die_capacity_bytes"] + 1
               for d in placement["dies"])
    table_bytes = sum(sum(piece["bytes"] for piece in d.get("engram", [])) for d in placement["dies"])
    assert abs(table_bytes + placement["engram_spill"]["total"]
               - placement["bytes"]["engram_table_L1"] - placement["bytes"]["engram_table_L14"]) < 2


def test_claimed_stage_hop_stays_inside_modelled_latency_band():
    record = rack.build()
    lo, hi = rack.PHYS["cable_hop_s"]["band"]      # the ring cables run full KP4 (validated 209 ns, 160-300)
    worst = max(link["latency_s"] for link in record["links"]["stage_links"])
    assert lo <= worst <= hi
    assert record["elevation"]["ring_max_tray_span"] <= 1


def test_repricing_does_not_double_count_the_embedding_return():
    record = rack.build()
    s = record["reprice_sensitivity"]
    assert s["embedding_return"]["previous_switched_s"] > s["embedding_return"]["adopted_ring_s"]
    assert s["geometry"]["rate_tokens_s"] <= s["baseline"]["rate_tokens_s"]
    assert s["no_collective_overlap_stress"]["rate_tokens_s"] < s["geometry"]["rate_tokens_s"]
    assert s["serdes_static"]["geometry_j_per_token"] > s["baseline"]["dynamic_j_per_token"]


def test_unresolved_physical_conflicts_remain_explicit():
    record = rack.build()
    sev = {entry["id"]: entry["severity"] for entry in record["conflicts"]}
    # C4 (SerDes static) and C8 (two-die link lanes) close once the R-L9 lane record prices them
    if rack.LANES_R_L9:
        assert sev["C4"] == "resolved-in-model" and sev["C8"] == "resolved-in-model"
    else:
        assert sev["C4"] == "conflict" and sev["C8"] == "conflict"
    # overlap + whole-system clock, and the head-die draft SRAM floorplan, stay open gates
    assert sev["C7"] == "gate" and sev["C10"] in ("gate", "conflict")
    assert sev["C3"] != "conflict" and sev["C6"] != "conflict"


def test_lanes_follow_r_l9_and_cables_are_shipping_dacs():
    record = rack.build()
    lb = record["lanes"]
    assert lb["total"] <= 90
    if rack.LANES_R_L9:
        assert lb["per_package"]["tp"] == 52 and lb["per_package"]["stage_out"] == 14
        assert lb["tp_lanes_per_die_pair"] == 13 and lb["two_step_allreduce"]
    assert lb["cables_per_package_per_hop"] * 8 >= lb["per_package"]["stage_out"]
    assert lb["ring_cables"] == 29 * 2 * lb["cables_per_package_per_hop"]


def test_kv_replicate_on_write_matches_the_spec_capacity():
    kv = rack.build()["kv_replication"]
    assert set(kv["owners"]) == {2, 8, 14, 20}
    assert all(o["owner_stage"] in o["reader_stages"] for o in kv["owners"].values())
    # the spec's 1M capacity (arch_budget_v41 capacity: 962 users at 4 stacks) within 1%
    assert abs(kv["users_at_1m_by_capacity"] - 962) <= 10
    assert kv["ingest"]["seconds_per_user_worst_stage_port"] < kv["ingest"]["seconds_per_user_nic"]


def test_head_draft_sram_is_allocated_and_fits_spare_rom():
    a = rack.build()["head_draft_sram_allocation"]
    assert a["fits"] and a["allocated_mm2"] >= a["min_mm2"]


def test_demonstration_plan_names_clock_and_overlap_gates():
    plan = rack.build()["demonstration_plan"]
    assert {s["id"] for s in plan["clock"]["steps"]} >= {"K1", "K2", "K3", "K4"}
    assert {s["id"] for s in plan["overlap"]["steps"]} >= {"O1", "O2", "O3"}


def test_report_contains_generated_rack_figures_and_caveat():
    report = (ROOT / "docs/ARCHITECTURE_ATLAS.html").read_text()
    assert report.count("<!-- V41_RACK_FIGURES_BEGIN -->") == 1
    assert report.count("<!-- V41_RACK_FIGURES_END -->") == 1
    assert "before the headline rates can use this layout" in report
    assert "No collective overlap (stress case)" in report
    assert "(C7)" in report and "(C10)" in report and "demonstration_plan" in report
    assert "no corrected ROM:HBM energy ratio" in report
    for name in ("logical", "elevation", "links", "compare"):
        figure = (ROOT / f"results/arch/figures/v41_rack_{name}.html").read_text()
        assert report.count(figure) == 1
