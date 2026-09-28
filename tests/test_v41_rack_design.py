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
    # the bytes-only serialisation starts from the conditional (overlapped) point and lies below it; the measured
    # C7 exposure (the baseline) is worse still, so the bytes-only row is not a bound
    assert s["no_collective_overlap_stress"]["rate_tokens_s"] < s["baseline"]["conditional_rate_tokens_s"]
    assert s["baseline"]["rate_tokens_s"] < s["no_collective_overlap_stress"]["rate_tokens_s"]
    assert s["serdes_static"]["geometry_j_per_token"] > s["baseline"]["dynamic_j_per_token"]


def test_unresolved_physical_conflicts_remain_explicit():
    record = rack.build()
    sev = {entry["id"]: entry["severity"] for entry in record["conflicts"]}
    # C4 (SerDes static) and C8 (two-die link lanes) close once the R-L9 lane record prices them
    if rack.LANES_R_L9:
        assert sev["C4"] == "resolved-in-model" and sev["C8"] == "resolved-in-model"
    else:
        assert sev["C4"] == "conflict" and sev["C8"] == "conflict"
    # overlap + whole-system clock stay an open gate; C10 closes analytically once the draft-KV gate passes
    assert sev["C7"] == "gate"
    assert sev["C10"] == ("resolved-in-model" if record["gates"]["C10"]["verdict"] == "PASS" else "gate")
    c7 = next(e for e in record["conflicts"] if e["id"] == "C7")
    assert c7["status"] == "NOT MET (measured)"              # the RTL stage bench measured the overlap (O2)
    o2 = next(s for s in record["demonstration_plan"]["overlap"]["steps"] if s["id"] == "O2")
    assert o2["status"] == "NOT MET (measured)"
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
    rec = rack.build()
    a, fp = rec["head_draft_sram_allocation"], rec["head_draft_floorplan"]
    assert a["fits"] and a["allocated_mm2"] >= a["min_mm2"]
    # the head die's "spare" ROM is Engram spill: the SRAM goes in released engine area and displaces no ROM
    assert a["head_die_spare_rom_bytes"] < 1.0 and a["displaced_rom_bytes"] == 0.0
    assert fp["area"]["fits_released_area"] and fp["organisation"]["fits"]
    assert a["rom_alternative"]["fits"]            # the fallback re-spill would still fit the layer dies


def test_c10_draft_kv_gate_is_sized_from_the_released_model_and_meets_the_draft_timing():
    g = rack.build()["gates"]["C10"]
    assert g["verdict"] == "PASS"
    assert g["state"]["context_independent"]
    for ctx in ("1048576", "200000"):
        assert g["sizing"][ctx]["per_user_bytes"] == 3 * 128 * 528
    assert g["port"]["meets_model"] and g["port"]["sram_read_cycles"] <= g["port"]["model_sweep_cycles"]
    assert g["port"]["one_row_per_slot_cycles"] > g["port"]["model_sweep_cycles"]     # why the port was widened
    assert g["paging"]["hidden_under_draft"]
    r = g["rates"]["1048576"]
    fb = r["hbm_backed_unstaged"]
    assert fb["hbm_first_access_1us"]["mtp_tokens_s_per_user"] < fb["hbm_budgeted_250ns"]["mtp_tokens_s_per_user"] \
        < r["mtp_tokens_s_per_user"]


def test_c8_two_die_links_carry_the_fill_with_the_adopted_relay():
    rec = rack.build()
    g = rec["gates"]["C8"]
    # the analytic per-layer collectives reproduce the design-point DAG's per-position payload (less the argmax merge)
    lc = rack.layer_collectives()
    assert sum(c[3] for L in lc for c in lc[L]) == 10362400 - 32
    assert g["verdict"] == "PASS" and g["worst_gated_utilisation"] <= 1.0
    fm = g["points"]["fill28_mtp"]
    assert fm["adopted_levers"]["t1_utilisation"] < fm["no_levers"]["t1_utilisation"]
    assert fm["adopted_levers"]["ucie_utilisation"] > fm["no_levers"]["ucie_utilisation"]   # relay forwards on UCIe
    assert g["ucie_relay_burst"]["utilisation"] < 1.0
    # the traffic table now carries the KV-rows all-gathers and the design-point rates
    assert rec["traffic"]["collectives"]["rows_allgather_bytes"] > 0
    assert rec["traffic"]["rates"]["b1"] == rec["gates"]["C8"]["rates"]["b1"]


def test_c4_every_lane_is_charged():
    rec = rack.build()
    g = rec["gates"]["C4"]
    assert g["verdict"] == "PASS"
    assert abs(g["charged_w"] - rec["power"]["serdes"]["total_w"]) < 1.0
    assert g["active_lanes_per_layer_package"] + rack.LANES["spare"] == 90
    assert g["switch_side"]["within_tray"]


def test_demonstration_plan_names_clock_and_overlap_gates():
    plan = rack.build()["demonstration_plan"]
    assert {s["id"] for s in plan["clock"]["steps"]} >= {"K1", "K2", "K3", "K4"}
    assert {s["id"] for s in plan["overlap"]["steps"]} >= {"O1", "O2", "O3"}


def test_report_contains_generated_rack_figures_and_caveat():
    report = (ROOT / "docs/ARCHITECTURE_ATLAS.html").read_text()
    assert report.count("<!-- V41_RACK_FIGURES_BEGIN -->") == 1
    assert report.count("<!-- V41_RACK_FIGURES_END -->") == 1
    section = report[report.index("<!-- V41_RACK_FIGURES_BEGIN -->"):report.index("<!-- V41_RACK_FIGURES_END -->")]
    assert "Gate C7" in section and "NOT met" in section and "C10" in section and "demonstration plan" in section
    assert "not a bound" in section                     # the bytes-only row sits above the measured headline
    import re
    for name in ("logical", "elevation", "links", "compare"):
        # the atlas section is curated (captions, numbering); the figure bodies are the generated SVGs
        figure = (ROOT / f"results/arch/figures/v41_rack_{name}.html").read_text()
        svg = re.search(r"<svg.*?</svg>", figure, re.S).group(0)
        assert section.count(svg) == 1, name


def test_layer_collectives_match_the_design_point_dag():
    """The rack's per-layer collective payloads are the ones the design-point DAG issues (layer by layer)."""
    import re
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import arch_lanes_v41 as L
    sp, muts, hz = L._ladder_top()
    with L.LX.clock(hz[0]), L.U.params(**hz[1]):
        g = L.U.solve(sp, 1048576, levers=L.U.CHAIN_L3, muts=list(muts))["_built"].g
    dag = {}
    for n, nd in g.nodes.items():
        m = re.match(r"^L(\d+)\.(.*)$", n)
        if nd["kind"] == "collective" and m:
            dag.setdefault(int(m.group(1)), {})[m.group(2)] = nd["payload"]
    lc = rack.layer_collectives()
    for layer, rows in lc.items():
        assert {name: by for name, _, _, by in rows} == dag[layer], layer
