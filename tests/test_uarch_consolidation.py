"""Consolidation section of the microarchitecture model (tools/uarch_model.py --consolidation): V4.1 ROM die count
from the placed field at each density basis, Engram table dies, right-sized HBM dies, the V4.1 HBM die-count sweep,
and the comparison rule."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/uarch/consolidation.json"
sys.path.insert(0, str(ROOT / "tools"))


def _rec():
    return json.loads(REC.read_text())


def test_record_is_source_pinned_and_states_the_refit_provenance():
    r = _rec()
    assert r["schema"] == "opentallas.uarch.consolidation.v1"
    for q in ("tools/uarch_model.py", "results/arch/v41_die_assembly.json", "results/arch/v41_die_placement.json",
              "results/floorplan/v41_die_macromap_expanded_woa.json", "tools/decode_critical_path.py"):
        assert len(r["source_sha256"][q]) == 64
    rf = r["v41_rom"]["refit"]
    assert rf["committed"] is False and rf["element_pair"]["closed"] is False
    assert len(rf["tool_sha256"]) == 64 and len(rf["element_pair"]["sha256"]) == 64


def test_refit_geometry_closes_the_die():
    import uarch_model as U
    rf = U.CONS_REFIT
    parts = U.CONS_FIELD_MM2 + rf["hub_mm2"] + rf["edge_io_mm2"] + rf["hbm_service_mm2"] + rf["channels_mm2"] \
        + U.CONS_SLIVER_MM2
    assert abs(parts - rf["die_mm2"]) < 0.05
    g = U.CONS_GEOM["w10_refit"]
    assert abs(g["ring_free_mm2"] + g["core_gap_mm2"] - U.CONS_SLIVER_MM2) < 0.1   # rounded measurements
    # the ASAP7 need at 28 stages reproduces the re-fit's busiest-die pair rows (less the Engram spill)
    b = rf["busiest_macros"]
    pairs = (b["expert"] + b["dense_qe"] + b["me"] + b["vm_constant"]) / 2
    assert abs(U.cons_field_need_mm2(28, "asap7") - pairs * rf["pair_footprint_mm2"]) < 0.5


def test_stage_plan_is_the_equal_byte_placement():
    import uarch_model as U
    P = json.loads((ROOT / "results/arch/v41_die_placement.json").read_text())
    p = U.cons_stage_plan(28)
    for st in P["stages"]:
        for l in st["layers"]:
            f = dict(p["frac"][l["layer"]])
            assert abs(f.get(st["stage"], 0.0) - l["fraction"]) < 2e-3, (st["stage"], l)
    assert abs(p["payload_per_die_B"] - P["die_table"][0]["weight_bytes"]) / p["payload_per_die_B"] < 1e-6


def test_product_basis_and_stage_table():
    r = _rec()
    v = r["v41_rom"]
    assert v["product"]["status"].startswith("188 dies: 37 TP-4 stages")      # BF16 columns (user decision)
    pb = v["product_basis"]
    assert pb["density"] == "analytical" and pb["overhead"] == 0.125 and pb["credit"] == "ring"
    cs = v["counts"]
    for bf in ("standard_pair", "columns"):
        for pitch in ("w10_budget", "w18_measured"):
            for o in (0.10, 0.125, 0.15):
                for cr in ("ring", "none"):
                    n = {c["density"]: c["stages"] for c in cs
                         if (c["bf16"], c["pitch"], c["overhead"], c["sliver_credit"]) == (bf, pitch, o, cr)}
                    assert n["asap7"] <= n["analytical"] <= n["roma"]
    # less credit, a wider pitch, or BF16 columns never need fewer stages
    idx = {(c["bf16"], c["pitch"], c["density"], c["overhead"], c["sliver_credit"]): c["stages"] for c in cs}
    for (bf, pitch, d, o, cr), n in idx.items():
        assert n <= idx[(bf, pitch, d, o, "none")]
        assert n <= idx[(bf, "w18_measured", d, o, cr)]
        if bf == "standard_pair":
            assert n <= idx[("columns", pitch, d, o, cr)]


def test_ss_rows_are_slower_than_tt():
    r = _rec()
    pts = r["v41_rom"]["points"]
    tt = next(p for p in pts if p["label"] == "BF16 lever: standard_pair")
    for p in pts:
        if p.get("role") == "ss":
            assert p["clock_hz"] <= r["v41_rom"]["ss"]["tt_clock_hz"] * 1.3
            if p["clock_hz"] < r["v41_rom"]["ss"]["tt_clock_hz"]:
                assert p["ar_tokens_s_b1"] < tt["ar_tokens_s_b1"]


def test_stage_rebuild_moves_only_hops():
    import uarch_model as U
    graphs = {}
    for S in (28, 24):
        with U._cons_stages(S) as units:
            import decode_critical_path as D
            assert D.packed_placement(units, 4)["layer_groups"] == S
            _, b = U.arch_graph(1048576)
            graphs[S] = b.g
    a, b = graphs[28], graphs[24]
    for n, nd in a.nodes.items():
        if nd["kind"] == "hop":
            continue
        assert abs(nd["issue"] - b.nodes[n]["issue"]) < 1e-15 and abs(nd["depth"] - b.nodes[n]["depth"]) < 1e-15, n
    assert U._ARCH_CACHE == {} or 1048576 in U._ARCH_CACHE


def test_188_point_reproduces_the_economics_single_user_rates():
    r = _rec()
    e = json.loads((ROOT / "results/uarch/economics.json").read_text())
    p0 = r["v41_rom"]["points"][0]
    assert p0["dies"] == 188 and p0["hbm_stacks"] == 464
    assert abs(p0["ar_tokens_s_b1"] - e["v41_rom"]["ar"]["tokens_s_b1"]) < 1.0
    assert abs(p0["mtp_tokens_s_b1"] - e["v41_rom"]["mtp_m1"]["tokens_s_b1"]) < 1.0
    assert p0["capacity_users_1m"] == e["v41_rom"]["capacity_users"]


def test_table_consolidation_leaves_the_token_path_unchanged():
    r = _rec()
    p0 = r["v41_rom"]["points"][0]
    for p in r["v41_rom"]["points"]:
        eg = p["engram"]
        assert eg["engram_l1_latency_us"] < eg["engram_l1_slack_us"]
        assert all(v < 0.5 for k, v in eg.items() if k.startswith("link_utilisation"))
        for L, s in p["engram_dag_slack"].items():
            assert not s["on_critical_path"] and s["slack_us"] > 0, (p["label"], L)
        if p["stages"] == 28 and p.get("bf16") == "columns" and p.get("clock_hz") == p0.get("clock_hz"):
            assert abs(p["ar_tokens_s_b1"] - p0["ar_tokens_s_b1"]) < 0.05


def test_hbm_chain_at_96_dies_is_the_w13_chain():
    import uarch_model as U
    for P in (1, 6):
        T, parts, _ = U.v41_hbm_chain(True, P)
        mine = U._hbm_chain_n(96, 32, P)
        assert all(abs(mine[k] - v) < 1e-9 for k, v in parts.items())


def test_right_sized_hbm_dies_hold_their_shoreline():
    r = _rec()
    rs = r["hbm"]["right_sized"]
    # at the 12 mm placeholder, six PHYs need a 38 mm edge: no reticle holds them (the H200 shoreline does)
    assert not rs["qwen_6_phy12mm"]["fits_reticle"]
    for k, d in rs.items():
        if "phy12mm" in k:
            continue
        assert d["fits_reticle"], k
        assert d["die_mm2"] < 815.0 and d["die_w_mm"] >= (d["stacks"] + 1) // 2 * 8.5
        assert d["demonstrated"] == (d["stacks"] <= 6)


def test_hbm_sweep_is_monotone_and_starts_at_capacity():
    r = _rec()
    for s in (4, 6):
        rows = [x for x in r["hbm"]["v41_sweep"] if x["stacks_per_die"] == s and x["replicas"] == 1]
        assert rows[0]["capacity_minimum"] and rows[0]["capacity_users_1m"] >= 1
        users = [x["capacity_users_1m"] for x in rows]
        assert users == sorted(users)
        ar = [x["ar"]["batch1"]["per_user_tokens_s"] for x in rows]
        assert all(b >= a * 0.97 for a, b in zip(ar, ar[1:]))


def test_die_cost_model():
    import uarch_model as U
    small, big = U.die_cost(300.0), U.die_cost(815.0)
    assert small["yield_"] > big["yield_"] and small["usd"] < big["usd"] * 300 / 815


def test_qwen_rom_product_is_option_c():
    r = _rec()
    q = r["qwen_rom"]
    assert q["product"] == "C" and q["product_row"]["G"] == 6144 and q["product_row"]["k"] == 4
    assert q["product_row"]["fits"] and q["options"]["g_search"]["chosen"] == 6144
    e = json.loads((ROOT / "results/uarch/economics.json").read_text())
    assert abs(e["qwen_rom"]["ar"]["tokens_s_b1"] - q["product_row"]["tokens_s_b1"]) < 0.5
    fit = q["options"]["fit_by_density"]
    assert fit["storage_n5"]["2"] > 560 if "2" in fit["storage_n5"] else fit["storage_n5"][2] > 560


def test_ss_curve_is_monotone_and_capped():
    r = _rec()
    cur = r["v41_rom"]["ss"]["curve"]
    dv = r["v41_rom"]["ss"]["depth_options"]
    for depth in dv:
        rows = [x for x in cur if x["depth"] == depth]
        assert rows and all(x["clock_ghz"] <= dv[depth]["ss_ghz"] + 1e-9 for x in rows)
        ar = [x["ar_tokens_s_b1"] for x in rows]
        assert all(b >= a - 0.5 for a, b in zip(ar, ar[1:])), depth


def test_adopted_product_row():
    r = _rec()
    pts = [p for p in r["v41_rom"]["points"] if p.get("role") == "product"]
    ad = next(p for p in pts if "ADOPTED" in p["label"])
    assert ad["clock_hz"] == 1.2e9 and ad["field_concurrency"] == 0.5 and ad["bf16"] == "columns"
    assert list(ad["slow_domain"]) == [0.9e9, "w18"] and ad["elem_stages"] == 7
    assert ad["added_latency"] == {"suffix:softplus_sqrt": -97}         # the v41x softplus (162, not 259)
    import uarch_model as U                                   # the product stage count is the fit's own answer
    assert ad["stages"] == U.cons_min_stages("analytical", 0.125, "ring", "w10_refit", "w10_q_1p2", "columns", "4096m8")
    assert ad["dies"] == 4 * ad["stages"] + 4 + 36             # head group on 8192m8 ping-pong (4 dies), 36 tables
    ref = ad["bf16_stage_reference"]
    assert ref["option_ii cap 3 (reference)"] < ref["option_iii BF16_PAIR (reference)"] <= ref["columns (product)"]
    ft = r["v41_rom"]["product"]["bf16_full_token"]
    assert all(ad["ar_tokens_s_b1"] >= v["ar"] for v in ft.values())       # the columns win per user
    ideal = next(p for p in pts if p["label"].endswith("ideal depths, no concurrency cap"))
    capped = next(p for p in pts if p["label"].endswith("(W18, adopted)"))
    assert capped["ar_tokens_s_b1"] < ideal["ar_tokens_s_b1"]          # the 50% cap costs time
    # per-pair ICG adopted: idle pairs pay leakage only; the ungated form (every idle pair clocked) is kept for the
    # waterfall and must be far above (the pre-fix 807 W came from charging it)
    c = ad["cooling"]
    assert c["layer_die_mean_w_saturated"] <= c["layer_die_busiest_w_saturated"] < c["limit_w_per_die"] and c["fits"]
    assert c["cooling_ungated"]["mean_w"] > 3 * c["layer_die_mean_w_saturated"]
    # the comparison rule's reference is the adopted row
    assert abs(r["comparison_rule"]["v41_targets"]["power"] - ad["energy"]["ar_sat"]["gated_system_w"]) < 1.0


def test_clock_cases_and_droop():
    r = _rec()
    cc = r["clock_domain_cases"]
    a8 = cc["a: all 1.2 GHz, chain adds 8 stages"]
    a9 = cc["a: all 1.2 GHz, chain adds 9 stages"]
    b9 = next(v for k, v in cc.items() if k.startswith("b: 1.2 GHz field (LAT 7) + 0.9"))
    assert a9["ar_tokens_s_b1"] <= a8["ar_tokens_s_b1"] < b9["ar_tokens_s_b1"]     # the measured add favours (b)
    for c in cc.values():
        d = c["droop"]
        assert d["1,024-cycle pre-ramp, no cap"]["pre_ramp_mJ_per_token"] > d["50% cap + 256-cycle pre-ramp"]["pre_ramp_mJ_per_token"]
    fs = next(p for p in r["v41_rom"]["points"] if "ADOPTED" in p["label"])["field_starts"]
    assert fs["mean_ramps_per_die"] <= fs["mean_starts_per_die"]


def test_karb_and_cdc_records():
    r = _rec()
    k = r["karb"]
    assert k["regions_tt"] == [13, 11, 9, 7, 7, 9, 11, 13] and max(k["regions_ss"]) == 15
    c = r["v41_rom"]["cdc"]
    assert c["fast_to_slow_slow_cycles"] == 4 and c["slow_to_fast_fast_cycles"] == 5
    assert c["vm_port_area_mm2"]["after"] > c["vm_port_area_mm2"]["before"]


def test_product_stage_owner_file():
    import uarch_model as U
    own = json.loads((ROOT / "results/arch/v41_stage_owner_product.json").read_text())
    r = _rec()
    ad = next(p for p in r["v41_rom"]["points"] if p.get("role") == "product" and "SS wire" in p["label"])
    assert own["schema"] == "opentallas.v41.stage_owner_preflight.v1" and own["stage_count"] == ad["stages"]
    assert own["layer_dies"] == ad["layer_dies"] and len(own["layer_owners"]) == 40
    assert own["min_per_die_headroom_after_rounding_and_engram_spill_bytes"] > 0
    stages = {o["dense_owner_stage"] for o in own["layer_owners"]}
    assert max(stages) <= own["stage_count"] - 1
    assert own["source_sha256"]["tools/uarch_model.py"] == __import__("hashlib").sha256(
        (ROOT / "tools/uarch_model.py").read_bytes()).hexdigest()
    assert U.cons_min_stages("analytical", 0.125, "ring", "w10_refit", "w10_q_1p2", "columns", "4096m8") == own["stage_count"]
