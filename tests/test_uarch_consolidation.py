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
    assert v["product"]["status"].startswith("208 dies: 41 TP-4 stages")      # W10b tiles + the VM-H hub block
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
    assert ad["added_latency"] == {"suffix:softplus_sqrt": -97, "suffix:idx.topk_local": 8}   # v41x softplus; idx_tail 16
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
    # the comparison rule's reference is the final product row
    fin = next(p for p in r["v41_rom"]["points"] if p.get("product_final"))
    assert abs(r["comparison_rule"]["v41_targets"]["power"] - fin["energy"]["ar_sat"]["gated_system_w"]) < 1.0


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
    ad = next(p for p in r["v41_rom"]["points"] if p.get("product_final"))
    assert own["schema"] == "opentallas.v41.stage_owner_preflight.v1" and own["stage_count"] == ad["stages"]
    assert own["layer_dies"] == ad["layer_dies"] and len(own["layer_owners"]) == 40
    assert own["min_per_die_headroom_after_rounding_and_engram_spill_bytes"] > 0
    stages = {o["dense_owner_stage"] for o in own["layer_owners"]}
    assert max(stages) <= own["stage_count"] - 1
    assert own["source_sha256"]["tools/uarch_model.py"] == __import__("hashlib").sha256(
        (ROOT / "tools/uarch_model.py").read_bytes()).hexdigest()
    assert U.cons_min_stages("analytical", 0.125, "ring", U.PRODUCT_GEOM, U.PRODUCT_PITCH, "columns",
                             "4096m8") == own["stage_count"]


def test_followup_rows():
    r = _rec()
    ts = r["tau_sweep_1m"]
    assert ts["headline_tau"] == 3.78 and "lmsys.org" in ts["source"]
    rom = ts["rows"][0]
    assert rom["tau_2.91"] < rom["tau_3.78"] < rom["tau_5.24"]
    assert {x["design"][:10] for x in r["short_context_8k"]["rows"]} and r["short_context_8k"]["ctx"] == 8192
    q = r["qwen_context_sweep"]["rows"]
    rom = [x for x in q if x["design"].startswith("ROM option C (4 stacks")]
    assert [x["ctx"] for x in rom] == [8192, 32768, 131072, 200000]
    assert all(b["ar_tokens_s"] <= a["ar_tokens_s"] for a, b in zip(rom, rom[1:]))
    hx = r["qwen_helix_200k"]["rows"]
    assert hx[0]["extra_kv_dies"] == 0 and hx[-1]["ar_tokens_s"] > hx[0]["ar_tokens_s"]
    assert r["gpu_calibration"]["published"][0]["tok_s_user"] == 368.0


def test_w11_measured_serial_step():
    """Named step (W16b): W11's measured serial build at 1.111 ns SS (ddd2f725) replaces the 3-stage-add depths
    and the +1 LAT-4 multiply lower bound in the 0.9 GHz domain; it lengthens the chain, so AR and MTP drop,
    the stage plan and die count do not move, and the product row is the one the headline table reads."""
    import uarch_model as U
    m = U.W11_SERIAL_MEASURED
    assert (m["linear"], m["exp"], m["sigmoid"], m["silu"], m["rsqrt"], m["softplus"], m["gate"]) == (9, 22, 23, 23, 21, 54, 23)
    assert (m["reduce_tap"], m["reduce_per_level"], m["div"], m["light_lane_ss_mhz"]) == (9, 1, 0, 929.0)
    r = _rec()
    pts = {p["label"]: p for p in r["v41_rom"]["points"] if p.get("role") == "product"}
    old = next(p for k, p in pts.items() if k.endswith("W11 LAT-4 serial mul"))
    new = next(p for k, p in pts.items() if k.endswith(U.SERIAL_TAG))
    assert new["serial"] == "w11_measured" and old.get("serial") is None
    assert new["ar_tokens_s_b1"] < old["ar_tokens_s_b1"] and new["mtp_tokens_s_b1"] < old["mtp_tokens_s_b1"]
    assert (new["stages"], new["dies"]) == (old["stages"], old["dies"])
    fin = [p for p in pts.values() if p.get("product_final")]
    assert len(fin) == 1 and fin[0]["label"].endswith(U.PRODUCT_TAG)
    h = r["headline_table"]["v41"][0]
    assert abs(h["per_user_ar"] - fin[0]["ar_tokens_s_b1"]) < 0.5 and abs(h["per_user_mtp"] - fin[0]["mtp_tokens_s_b1"]) < 0.5


def test_w16b_pass2_steps():
    """Shrunk-die interim crossings shorten the path; the W11 streaming depths lengthen it; the tier-3 rows are W19's
    composed token; the Qwen RTL comparison and its calibrated row are recorded."""
    import uarch_model as U
    r = _rec()
    pts = {p["label"]: p for p in r["v41_rom"]["points"] if p.get("role") == "product"}
    ser = next(p for k, p in pts.items() if k.endswith(U.SERIAL_TAG))
    shr = next(p for k, p in pts.items() if k.endswith(U.SHRINK_TAG))
    stm = next(p for k, p in pts.items() if k.endswith(U.STREAM_TAG))
    assert shr["ar_tokens_s_b1"] >= ser["ar_tokens_s_b1"] and stm["ar_tokens_s_b1"] <= shr["ar_tokens_s_b1"]
    assert shr["die"]["expert_wire"] == 63 and shr["die"]["coll_stages"] == 45
    t3 = [x for x in r["headline_table"]["v41"] if x["tier"] == "3"]
    assert t3 and all(abs(x["per_user_ar"] - 1e6 / 431.55) < 0.1 for x in t3)
    q = r["qwen_l0_rtl_vs_model"]
    assert q["rtl"]["cycles"] == 4669 and q["rtl"]["me_extra"] == U.QWEN_W12_TP4_ME_EXTRA_SS   # the RTL ran without +54
    assert abs(q["ratio"] - 4669 / q["model_layer_cycles"]) < 1e-3
    qs = r["qwen_product_ss"]
    assert qs["kv_prep_cycles"] == 216
    assert (qs["rtl_attributed_as_built"]["tokens_s_b1"] < qs["rtl_attributed_body_only"]["tokens_s_b1"]
            < qs["tokens_s_b1"])
    assert U.QWEN_SS["me_lat_extra"] == U.QWEN_W12_TP4_ME_EXTRA_SS + 54                       # LAT-7 counted once


def test_die_shrink_ruling():
    """Root ruling 2026-09-30: shrink the layer die to the owner file's pairs + ~10%; W18b's interim die holds them."""
    import uarch_model as U
    own = json.loads((ROOT / "results/arch/v41_stage_owner_product.json").read_text())
    # the ruling sized the die at 37 stages (5,289 pairs); W10b's 39-stage re-fit needs fewer pairs a die, so the
    # interim die still holds the owner file's (re-sizing to the 39-stage owner file is W18b's, pending a root ruling)
    assert U.DIE_SHRINK["pairs_needed"] == 5289 >= max(own["pairs_per_die_by_stage"])
    ds = _rec()["v41_rom"]["die_shrink_sensitivity"]
    assert ds["role"] == "ruling" and ds["interim"]["pair_slots"] >= ds["pairs_needed"]


def test_w16b_followup_steps():
    """W11 VM-H slows the SU chain; W10b's wider tiles and the hub block re-fit the stages; the product's VM is
    C_rotate (root 2026-10-01) with measured VM-H kept as a reference row; the K arbiter row is MERGE2 + HEADREG
    (+2, not in the product); the Qwen rows are attributed (body and all-reduce separately)."""
    import uarch_model as U
    r = _rec()
    pts = {p["label"]: p for p in r["v41_rom"]["points"] if p.get("role") == "product"}
    stm = next(p for k, p in pts.items() if k.endswith(U.STREAM_TAG))
    vmh = next(p for k, p in pts.items() if k.endswith(U.VMH_TAG))
    ref = next(p for k, p in pts.items() if k.endswith(U.VMH_REF_TAG))
    fin = next(p for k, p in pts.items() if k.endswith(U.PRODUCT_TAG))
    assert vmh["vmh"] == U.VMH and stm.get("vmh") is None and ref["vmh"] == U.VMH and fin["vmh"] == U.VMC
    assert vmh["ar_tokens_s_b1"] < stm["ar_tokens_s_b1"] and vmh["stages"] == stm["stages"] == 37
    assert ref["stages"] == 41 and ref["hub_block"] == "H_rtl" and not ref["product_final"]
    assert fin["stages"] == U.cons_min_stages("analytical", 0.125, "ring", "w10_refit_crot", "w10b_q", "columns", "4096m8")
    assert fin["stages"] == 41 and fin["dies"] == 4 * 41 + fin["head_dies"] + 36 and fin["hub_block"] == "C_rotate"
    assert vmh["hub_block"] is None and ref["ar_tokens_s_b1"] < fin["ar_tokens_s_b1"]       # C_rotate beats VM-H
    hf = r["v41_rom"]["product"]["head_fit"]
    assert hf["stages_w10b_tiles_only"] == 39 < fin["stages"] and hf["stages_vmh_reference"] == ref["stages"]
    assert abs(U.VMC_BLOCK["field_loss_mm2"] - (38.601 - 14.249) * 1.05) < 1e-3
    assert hf["dies"] == fin["head_dies"] and hf["dies_at_w10_q"] == 4 and hf["margin_storage_only_w10_q"] > 0
    assert U.CONS_PITCH["w10b_q"]["q_um"] == (510.84, 126.9)
    assert U._cons_pair_mm2("w10b_q", True) == 1002.89 * 142.56 / 1e6
    assert any(c["id"] == "vm_per_op_latency" for c in r["model_caveats"])
    k = r["karb"]
    assert k["regions_w18b_merge2_headreg"] == [20, 16, 14, 10, 10, 14, 16, 20]
    assert k["rows"]["w18b_merge2_headreg_worst"]["tokens_s_delta_pct"] < k["rows"]["ss_0p75mm_worst"]["tokens_s_delta_pct"]
    a = r["qwen_l0_rtl_vs_model"]["attribution"]
    assert (a["body_cycles"], a["allreduce_cycles"]) == (2687, 991)
    assert abs(a["body_ratio"] - 2687 / a["model_body_cycles"]) < 1e-4
    qs = r["qwen_product_ss"]
    assert "rtl_calibrated" not in qs
    q = [x for x in r["headline_table"]["qwen"] if "RTL-attributed" in x["design"]]
    assert len(q) == 2


def test_vmh_hub_block_in_dedicated_row():
    """Root rulings 2026-10-01: W18b packs proposal_w11_p6, whose stream unit is the product's measured SU+VM block
    (C_rotate)."""
    import uarch_model as U
    rows = {r["design"]: r for r in json.loads((ROOT / "results/uarch/v41_dedicated_units.json").read_text())["rows"]}
    su = rows["proposal_w11_p6"]["units"]["stream_unit"]
    assert su["area_mm2"] == U.VMC_BLOCK["block_mm2"] == 38.601 and su["area_lanes_ledger_mm2"] == 14.249
    assert su["vmh_block"]["option"] == "C_rotate"
    assert rows["proposal"]["units"]["stream_unit"]["area_mm2"] == 14.249                 # the reference row unchanged
    own = json.loads((ROOT / "results/arch/v41_stage_owner_product.json").read_text())
    assert own["stage_count"] == 41 and own["min_per_die_headroom_after_rounding_and_engram_spill_bytes"] > 0


def test_vm_waterfall_record():
    """Root 2026-10-01: the committed waterfall from the pre-VM-H product to measured VM-H, and the levers."""
    import uarch_model as U
    w = json.loads((ROOT / "results/uarch/v41_vm_waterfall.json").read_text())
    r = _rec()
    pts = {p["label"]: p for p in r["v41_rom"]["points"] if p.get("role") == "product"}
    stm = next(p for k, p in pts.items() if k.endswith(U.STREAM_TAG))
    ref = next(p for k, p in pts.items() if k.endswith(U.VMH_REF_TAG))
    fin = next(p for k, p in pts.items() if p.get("product_final"))
    wf = w["waterfall"]
    assert abs(wf[0]["ar_tokens_s_b1"] - stm["ar_tokens_s_b1"]) < 0.5
    assert abs(wf[-1]["ar_tokens_s_b1"] - ref["ar_tokens_s_b1"]) < 0.5
    assert abs(sum(x["delta_ar"] for x in wf[1:]) - w["total_drop_ar"]) < 0.5
    big = min(wf[1:], key=lambda x: x["delta_ar"])
    assert "SU op network latency" in big["step"]                                  # the dominant term
    lv = {x["lever"]: x for x in w["levers"]}
    ca = next(x for k, x in lv.items() if k.startswith("(a) C_rotate"))
    assert abs(ca["ar_tokens_s_b1"] - fin["ar_tokens_s_b1"]) < 0.5 and ca["vs_vmh_reference_pct"] > 0
