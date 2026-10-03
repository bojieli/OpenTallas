#!/usr/bin/env python3
"""DeepSeek-V4.1 ROM: does a near-HBM index scan and/or near-HBM attention help?  MODEL ONLY.

    python3 tools/dsrom_nearhbm.py            # rewrites results/uarch/dsrom_nearhbm_20261003/model.json
    python3 tools/dsrom_nearhbm.py --check    # recompute and refuse if the committed record differs

Basis: the unified model's S58 product (tools/uarch_model.py cons_v41_rom with the S58 selection's settings, as in
results/uarch/dsrom_stage_balance_20261003/options.py), read-only.  Every variant is graph surgery applied before
uarch_model._cons_adjust re-times the AR graph (P = 1) and the DSpark MTP verify graph (P = 6); uarch_model.py and every
pinned record stay byte-identical.  Per-die figures are per logical die of the TP-4 group (4 HBM3E stacks), as in
the model; the PAR2/TP-8 physical split is the parallelism study's (claude/dsrom-parallelism-20261003) business.

What is priced
  Q1  per token, per die, bytes from HBM for (a) the index scan, (b) the selected + window KV rows, (c) KV writes,
      and their time at the HBM aggregate against each on-die delivery path the records carry.
  Q2  (i) near-HBM index scan returning per-stack top-512 candidates, (ii) near-HBM attention in its exact form,
      (iii) both; each also composed with the CP-8 index scan of C5hc.  AR and MTP at 1M and 200K, area, tracks,
      shoreline power density against the IEEE EPS HIR 2.0 W/mm2 nominal limit.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

OUT = ROOT / "results/uarch/dsrom_nearhbm_20261003/model.json"
S = 58
CTXS = (1048576, 200000)
SRC = dict(
    uarch_model="tools/uarch_model.py",
    decode_critical_path="tools/decode_critical_path.py",
    arch_budget_v41="tools/arch_budget_v41.py",
    golden="tools/hdc_golden_v41.py",
    capacity="results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json",
    die_route="results/physical_abi3/asap7/chip/v41_w18/route/die_route_k32_ph5.json",
    die_assembly="results/physical_abi3/asap7/chip/v41_w18/die_assembly.json",
    connectivity="results/contracts/v41_floorplan_connectivity.json",
    reader="results/rtl/hdc_v41x_idx_four_stack_verilator_collector_pipeline.json",
    stack_major="results/rtl/v41_idx_stack_major_ingest.json",
    s58_corridor="results/uarch/dsrom_main_S58_corridor_correction_20261002/correction.json",
    s58_outline="results/uarch/dsrom_main_S58_corridor_correction_20261002/inputs/reservation_outline.json",
)
# IEEE EPS Heterogeneous Integration Roadmap, Thermal chapter v0.9, s2 and Table 4 (as sourced in
# claude/qwen-rom-floorplan-nearhbm-20261003 results/uarch/qwen_rom_floorplan_nearhbm_20261003/REPLAY.md:178)
HIR_LIMIT_W_MM2 = dict(nominal=2.0, conservative=1.0, aggressive=4.0)
CP8_MERGE_NS = 200.0          # the stage-balance study's CP-8 crossing charge (+200 ns on the merge)
NS_PER_DIE = 4                # HBM stacks per logical die (arch_budget_v41.ROM_DIE_HBM_STACKS)
# crossings of the 669 mm2 shrunk die at 504 um/stage (uarch_model.py:3380-3382, "not separately priced in the graph")
SHRUNK = dict(hbm_window=25, idx_keys=39, idx_topk=38, selected_kv=24)


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def J(rel):
    return json.loads((ROOT / rel).read_text())


# --------------------------------------------------------------------------------------------------------------
# Variant surgery on the priced graph (before _cons_adjust re-times it)
# --------------------------------------------------------------------------------------------------------------
SCAN_LAYERS = (2, 8, 14, 20)


def surgery(g, P, v, cyc, D, A, u):
    """v: dict(bus_Bpc=None|float, chase=bool, nh_scan=bool, nh_attn=bool, cp=4|8).  P: positions of the pass."""
    W = v.get("cp", 4)
    for n, nd in g.nodes.items():
        L = nd.get("layer")
        scan_node = n.endswith((".idx.score", ".idx.topk_local", ".cand.topk_local"))
        # CP-W over the uncapped scans (stage-balance options.py, verbatim rule): keys per die x 4/W
        if W != 4 and L in SCAN_LAYERS:
            k = 4 / W
            if scan_node:
                nd["issue"] *= k
            elif n.endswith(".idx.topk_final"):
                nd["depth"] = (math.ceil(W * 512 / 64) + D.tselect_latency(W * 512)) * cyc
            elif n.endswith(".cand.final"):
                nd["depth"] = (math.ceil(W * 2048 / 64) + D.tselect_latency(W * 2048)) * cyc
            elif n.endswith((".idx.topk_merge", ".cand.merge")):
                nd["depth"] += CP8_MERGE_NS * 1e-9
        # an on-die key path narrower than the HBM aggregate: the scan reads at min(HBM, path)
        if v.get("bus_Bpc") and n.endswith(".idx.score"):
            keys = int(nd["desc"].split()[2]) * (4 / W if L in SCAN_LAYERS else 1)
            macs = P * keys * 32 * 128
            nd["issue"] = max(keys * A.IDX_KEY_B / v["bus_Bpc"], macs / u.PRESETS["proposal"]["idx_macs"]) * cyc
        if v.get("chase") or v.get("nh_scan"):
            if n.endswith((".idx.topk_local", ".cand.topk_local")):
                nd["stream"] = True
        if v.get("nh_scan") or v.get("central4"):
            # four stack-local selectors (stack-major ingest, results/rtl/v41_idx_stack_major_ingest.json) each take
            # a quarter of the die's keys, then one exact top-k of the <= 4 k survivors (position order, lower index on
            # ties): issue / 4, depth + the per-die merge level
            if n.endswith(".idx.topk_local"):
                nd["issue"] /= NS_PER_DIE
                nd["depth"] += (math.ceil(NS_PER_DIE * 512 / 64) + D.tselect_latency(NS_PER_DIE * 512)) * cyc
            elif n.endswith(".cand.topk_local"):
                nd["issue"] /= NS_PER_DIE
                nd["depth"] += (math.ceil(NS_PER_DIE * 2048 / 64) + D.tselect_latency(NS_PER_DIE * 2048)) * cyc
        if v.get("nh_attn") and n.endswith(".attn.scores") and nd["issue"] > 0:
            # exact near-HBM attention: q.k is row-local (sequential over head_dim, golden dots), so scores may be
            # formed at the stack; P x V is ONE sequential sum over the 640 rows (golden attend/dots) and the softmax
            # denominator is the P = 8 interleaved reduce_rows, so P x V and den stay where every row arrives in
            # order.  The rows (keys = values) still cross to the hub; the q fan-out to the stacks and the score
            # return are two added crossings on the scores' path.
            nd["wire_in"] = nd.get("wire_in", 0.0) + SHRUNK["selected_kv"] * cyc
            nd["wire_out"] = nd.get("wire_out", 0.0) + SHRUNK["selected_kv"] * cyc


def _run(args):
    ctx, name, v = args
    import uarch_model as u
    import decode_critical_path as D
    import arch_budget_v41 as A
    cap = J(SRC["capacity"])
    b = {r["stages"]: r for r in cap["all_stage_capacity_rows"]}[S]["BF16_pairs_per_die"]
    u.PRESETS["proposal"]["bf16_stripe_macros"] = 2 * b
    clk = u.PRODUCT_CLOCK_HZ
    cyc = 1.0 / clk
    orig = u._cons_adjust
    GS = []

    def adj(g, P, *a, **kw):
        surgery(g, P, v, cyc, D, A, u)
        t = orig(g, P, *a, **kw)
        GS.append((P, g))
        return t
    u._cons_adjust = adj
    try:
        with u._cons_ctx(ctx):
            p = u.cons_v41_rom(S, 8, 36, bf16="columns", clock_hz=clk, field_concurrency=u.FIELD_CONCURRENCY,
                               added_latency=dict(u.SOFTPLUS_FIX, **u.W11_STREAM_SS, **u.PLUS_LAT),
                               dyn_scale=u.PRODUCT_DYN_SCALE, slow_domain=(.9e9, "w18"), elem_stages=8, ss_wire=True,
                               serial=u.PRODUCT_SERIAL, die=u.DIE_SHRUNK_INTERIM, vmh=u.VMC_FUSED,
                               hub_block=u.PRODUCT_HUB)
    finally:
        u._cons_adjust = orig
    fam = {}
    for P, g in GS:
        sink = [n for n in g.nodes if n.endswith("token.return")][0]
        acc = {}
        for n in g.path(sink):
            tail = n.split(".", 1)[1] if n.startswith(("L", "E")) and "." in n else n
            if tail.startswith("attn.") and any(t in tail for t in ("idx", "cand", "gather", "rows_allgather",
                                                                     "scores", ".pv", ".max", ".exp", ".den", ".sink",
                                                                     "normalize")):
                acc[tail] = acc.get(tail, 0.0) + sum(g.contrib[n].values()) * 1e6
        fam["ar" if P == 1 else "mtp_verify"] = {k: round(x, 4) for k, x in sorted(acc.items(), key=lambda kv: -kv[1])}
    return dict(ctx=ctx, variant=name, spec=v, ar_us=round(1e6 / p["ar_tokens_s_b1"], 4),
                ar_tok_s=p["ar_tokens_s_b1"], mtp_tok_s=p["mtp_tokens_s_b1"], ar_sat_tok_s=p["ar_saturated_tokens_s"],
                busiest_stage_us=p["busiest_stage_us"], critical_path_attention_us=fam)


# routed W18 key bus: 4 bands x 4,096 bits (die_route.py idx_bits = ceil(60.04 / 4) x 256), i.e. 2,048 B/cycle
VARIANTS = {
    "base": dict(),
    "base_routed_bus": dict(bus_Bpc=2048.0),
    "chase": dict(chase=True),
    "central4_chase": dict(chase=True, central4=True),
    "nh_scan": dict(nh_scan=True),
    "nh_attn_exact": dict(nh_attn=True),
    "nh_both": dict(nh_scan=True, nh_attn=True),
    "cp8": dict(cp=8),
    "cp8_routed_bus": dict(cp=8, bus_Bpc=2048.0),
    "cp8_chase": dict(cp=8, chase=True),
    "cp8_nh_scan": dict(cp=8, nh_scan=True),
    "cp8_nh_both": dict(cp=8, nh_scan=True, nh_attn=True),
}


# --------------------------------------------------------------------------------------------------------------
# Q1: the byte ledger and the delivery paths
# --------------------------------------------------------------------------------------------------------------
def ledger():
    import arch_budget_v41 as A
    import uarch_model as u
    c = A._env()["c"]
    clk = u.PRODUCT_CLOCK_HZ
    hbm_Bpc = A.ROM_DIE_HBM_BPS / clk                         # 3,000 B/cycle at 1.2 GHz
    route = J(SRC["die_route"])
    rd = J(SRC["reader"])
    meas = next(x for x in rd["cases"] if x["keys"] == 262144)
    nets = {n["id"]: n for n in route["nets"]}
    bands = ("s0", "s1", "n0", "n1")
    key_bits = sum(nets[f"idx_keys.hbm_service_{b}"]["bits"] for b in bands)
    win_bits = sum(nets[f"hbm_window.hbm_service_{b}"]["bits"] for b in bands)
    sel_bits = sum(nets[f"selected_kv.hbm_service_{b}"]["bits"] for b in bands)
    key_um = [nets[f"idx_keys.hbm_service_{b}"]["routed_um"] for b in bands]
    paths = dict(
        hbm_aggregate=dict(Bpc=hbm_Bpc, src="arch_budget_v41.ROM_DIE_HBM_BPS = 4 x 1.0 TB/s x 0.90"),
        scorer_ingest=dict(Bpc=u.PRESETS["proposal"]["idx_macs"] / (32 * 128) * A.IDX_KEY_B,
                           src="proposal idx_macs 262,144 = 64 keys/cycle x 68 B (uarch_model PRESETS)"),
        routed_idx_keys_bus=dict(Bpc=key_bits / 8, bits=key_bits, routed_um=key_um,
                                 cycles=[nets[f"idx_keys.hbm_service_{b}"]["cycles"] for b in bands],
                                 src=SRC["die_route"] + " idx_keys (sized 'at the measured reader rate')"),
        measured_reader=dict(Bpc=meas["sector_per_cycle"] * 32, src=SRC["reader"] + " (behavioural HBM; "
                             "'no physical or model throughput claim')"),
        routed_hbm_window_bus=dict(Bpc=win_bits / 8, bits=win_bits, src=SRC["die_route"] + " hbm_window"),
        routed_selected_kv_request=dict(bits=sel_bits, src=SRC["die_route"] + " selected_kv (32-bit IDs, request "
                                        "direction); the selected-row RETURN path is not a routed bus"),
    )
    rows = {}
    for ctx in CTXS:
        per = {}
        for L in range(40):
            ops, meta = A.ops_of_layer(c, L, ctx)
            by = {}
            for o in ops:
                for k, x in (o.get("bytes") or {}).items():
                    by[k] = by.get(k, 0) + x
            ratio = c["compress_ratios"][L]
            src = L in c["kv_source_layer_ids"]
            # writes per token per group: window row (every layer); at a source layer one compressed row (owner,
            # 9 sectors) + one index key per `ratio` tokens, the key written to all 4 stacks of each die
            # (deployed writer w_stack_mask = 4'b1111, docs/V41_HBM_REGION_PREFLIGHT.md)
            w_group = A.WIN_ROW_B + ((A.CKV_ROW_B + A.IDX_KEY_B * NS_PER_DIE) / ratio if src else 0)
            per[L] = dict(kind=meta["kind"], idx_B_die=by.get("idx", 0) / 4, rows_B_die=by.get("kv_sram", 0) / 4,
                          sel_rows_B_die=by.get("kv_hbm", 0) / 4, write_B_group=w_group)
        scan = {L: x["idx_B_die"] for L, x in per.items() if x["idx_B_die"]}
        t = lambda B, Bpc: B / Bpc / clk * 1e6  # noqa: E731
        rows[str(ctx)] = dict(
            per_layer_die=per,
            index_scan=dict(
                L20_die_MB=scan[20] / 1e6, L2_8_14_die_MB=scan[2] / 1e6, reindex_die_MB=scan.get(24, 0) / 1e6,
                path_sum_MB=sum(scan.values()) / 1e6,
                L20_us={k: round(t(scan[20], p["Bpc"]), 3) for k, p in paths.items() if "Bpc" in p},
                path_sum_us={k: round(t(sum(scan.values()), p["Bpc"]), 3) for k, p in paths.items() if "Bpc" in p}),
            kv_rows=dict(
                per_layer_die_B=per[20]["rows_B_die"], selected_per_layer_die_B=per[20]["sel_rows_B_die"],
                window_per_layer_die_B=per[20]["rows_B_die"] - per[20]["sel_rows_B_die"],
                fresh_selection_layers=[L for L in range(40) if per[L]["idx_B_die"]],
                at_hbm_us_per_layer=round(t(per[20]["rows_B_die"], hbm_Bpc), 4),
                at_hbm_window_bus_us_per_layer=round(t(per[20]["rows_B_die"], win_bits / 8), 4),
                selected_at_hbm_window_bus_us_per_layer=round(t(per[20]["sel_rows_B_die"], win_bits / 8), 4),
                mtp_positions=u.V41_POSITIONS, mtp_rows_B_die_per_layer=per[20]["rows_B_die"] * u.V41_POSITIONS),
            kv_writes=dict(per_token_group_B=sum(x["write_B_group"] for x in per.values()),
                           at_hbm_us=round(t(sum(x["write_B_group"] for x in per.values()) / 4, hbm_Bpc), 5)))
    # wire energy of the key stream on the routed bus (unpriced in the model: power_ledger charges HBM IF + stack only)
    mean_um = sum(key_um) / len(key_um)
    e_key = rows["1048576"]["index_scan"]["L20_die_MB"] * 1e6 * 8 * mean_um / 1000 * u.WIRE_J_PER_BIT_MM
    return dict(paths=paths, by_ctx=rows,
                key_wire_energy=dict(mean_routed_um=round(mean_um, 1), L20_die_mJ_per_token_1m=round(e_key * 1e3, 4),
                                     basis="17.8 MB x 8 b x mean routed idx_keys length x WIRE_J_PER_BIT_MM "
                                           "(0.1 pJ/b/mm, ASSUMED in uarch_model)"))


# --------------------------------------------------------------------------------------------------------------
# Area, tracks, shoreline power density
# --------------------------------------------------------------------------------------------------------------
def physical():
    import uarch_model as u
    import arch_budget_v41 as A
    clk = u.PRODUCT_CLOCK_HZ
    U = u.UNIT
    d = u.PRESETS["proposal"]
    el = u.DEDICATED["indexer"]
    slices = d["idx_macs"] // el["macs_per_element"]                        # 16 NK = 4 score slices
    a_slice = el["area_est_um2"] / 1e6                                       # ESTIMATE (no hardened slice)
    a_scorer = slices * a_slice
    tsel64 = 4 * U["tselect16_um2"] / 1e6                                     # one 64-lane tselect (4 x w16)
    outline = J(SRC["s58_outline"])
    corr = J(SRC["s58_corridor"])
    bands = {b["name"]: b["gross_mm2"] for b in outline["clear_route_bands"]}
    comps = {c_["name"]: c_["gross_mm2"] for c_ in outline["components"]}
    raw_key_bands = (bands["index_HBM_all128responses_CLEAR_ROUTE_BAND"] + corr["new_corridor_debit_mm2"]
                     + bands["index_quarter_join_to_batch_CLEAR_ROUTE_BAND"])
    collector = comps["BANKED_COLLECTOR_MACROS_AND_CLEAR20909TRACK_BAND"]
    pooled = comps["ACTUAL_POOLED_INDEXER_AND4RING_READERS"]
    route = J(SRC["die_route"])
    key_wires = route["classes"]["idx_keys"]["wires"]
    # near-HBM scan: the score slices sit beside each stack's service strip; the stack's own local top-512 selector
    # (already in the stack-major plan) moves with them; each key is owned by one die; the hub keeps the per-die 4 x 512 merge and q staging
    per_stack = dict(scorer_mm2=a_scorer / NS_PER_DIE, tselect_mm2=tsel64,
                     q_and_cand_regs_mm2=(el["query_bits"] * (slices // NS_PER_DIE) + 512 * 46) * u.DFF_UM2 / 1e6)
    per_stack["total_mm2"] = sum(per_stack.values())
    phy_edge_um = 12000.0       # PHY 12.0 x 0.8335 mm per stack (results/physical_abi3/asap7/chip/dies/v41_rom_*)
    strip_um = 8500.0           # W18 HBM_SERVICE strip 8,500 x 216 um (die_floorplan_ch8.64.json)
    # power at the shoreline: scorer dynamic (FP4 block-dot MACs at E_MAC fp4 x PRODUCT_DYN_SCALE) + logic leakage +
    # ungated clock per mm2 (technology constants); AR scans at the HBM rate (0.9 TB/s per stack, 13.2 G keys/s),
    # MTP verify is MAC-bound (64 keys/cycle per die = 16 per stack, 6 positions at m = 1 time-multiplexed)
    keys_ar = 0.9e12 / A.IDX_KEY_B
    keys_mtp = d["idx_macs"] / (32 * 128) / NS_PER_DIE * clk
    e_mac = u.E_MAC["fp4"] * u.PRODUCT_DYN_SCALE
    static_w_mm2 = u.LEAK["logic"] + u.CLOCK_J_MM2 * clk
    a = per_stack["total_mm2"]
    dyn_ar = keys_ar * 32 * 128 * e_mac
    dyn_mtp = keys_mtp * 32 * 128 * e_mac
    phy_w = 0.9e12 * u.E_HBM_IF_B                      # on-die PHY/controller share of an HBM byte, per stack
    phy_mm2 = 12.0 * 0.8335
    dens = dict(
        scorer_band_ar_w_mm2=round((dyn_ar + static_w_mm2 * a) / a, 3),
        scorer_band_mtp_w_mm2=round((dyn_mtp + static_w_mm2 * a) / a, 3),
        phy_band_w_mm2=round(phy_w / phy_mm2, 3),
        phy_plus_scorer_mtp_w_mm2=round((phy_w + dyn_mtp + static_w_mm2 * a) / (phy_mm2 + a), 3),
        limit=HIR_LIMIT_W_MM2,
        basis="dynamic at E_MAC fp4 %.3g J x %.2f; static LEAK logic %.2f W/mm2 + CLOCK_J_MM2 x 1.2 GHz %.3f W/mm2 "
              "(ungated: an upper bound); PHY at E_HBM_IF_B %.3g J/B over 12.0 x 0.8335 mm"
              % (u.E_MAC["fp4"], u.PRODUCT_DYN_SCALE, u.LEAK["logic"], u.CLOCK_J_MM2 * clk, u.E_HBM_IF_B))
    dens["verdict_nominal"] = "PASS" if max(v for k, v in dens.items() if k.endswith("w_mm2")) <= 2.0 else "FAIL"
    return dict(
        scorer=dict(slices=slices, slice_mm2_est=round(a_slice, 4), die_mm2_est=round(a_scorer, 3),
                    basis=el["area_basis"]),
        nh_scan_per_stack=({k: round(x, 4) for k, x in per_stack.items()}),
        nh_scan_strip_depth_um=dict(on_12mm_phy_edge=round(per_stack["total_mm2"] * 1e6 / phy_edge_um, 1),
                                    on_8p5mm_w18_strip=round(per_stack["total_mm2"] * 1e6 / strip_um, 1)),
        die_area_delta_mm2=dict(
            moved_hub_to_shoreline=round(a_scorer + NS_PER_DIE * tsel64, 3),
            added=round(NS_PER_DIE * per_stack["q_and_cand_regs_mm2"], 4),
            s58_raw_key_route_bands_removed=round(raw_key_bands, 3),
            s58_collector_band_removed=round(collector, 3),
            s58_corrected_margin_mm2=round(corr["corrected_margin_mm2"], 3),
            s58_pooled_indexer_mm2=round(pooled, 3),
            # central at the model's full scorer width: the 262,144-MAC scorer replaces the 7.48 mm2 pooled indexer
            s58_margin_central_full_scorer_mm2=round(corr["corrected_margin_mm2"] - (a_scorer - pooled), 3),
            # near-HBM: the raw-key bands, the collector band and the pooled indexer leave the hub; the full scorer,
            # its four local selectors and the q / candidate registers land at the shoreline (charged to the same
            # budget, since they displace field next to the PHYs)
            s58_margin_nh_scan_mm2=round(corr["corrected_margin_mm2"] + raw_key_bands + collector + pooled
                                         - NS_PER_DIE * per_stack["total_mm2"], 3),
            note="S58 hub outline (L20 reticle) prices the pooled indexer at 7.48 mm2 with index_MACs_per_cycle 1,024 "
                 "(as-built), not the model's 262,144-MAC proposal (21.7 mm2 est); both margins below charge the full "
                 "scorer, the near-HBM one at the shoreline"),
        tracks=dict(
            s58_native_all128_response_tracks=corr["native_response_tracks"],
            s58_native_request_tracks=corr["native_request_tracks"],
            w18_routed_idx_keys_wires=key_wires,
            nh_scan_candidate_wires_per_stack=route["classes"]["idx_topk"]["wires"] // 4,
            nh_scan_q_fanout_bits_per_stack=el["query_bits"],
            note="near-HBM scan carries q out (17,920 b per slice copy, loaded once per scan) and 512 x (BF16 score + "
                 "30-bit index) candidates back per stack; the raw 128-PC response fan-in to the hub disappears"),
        shoreline_power_density=dens,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--jobs", type=int, default=12)
    args = ap.parse_args()
    jobs = [(ctx, k, v) for ctx in CTXS for k, v in VARIANTS.items()]
    with mp.get_context("fork").Pool(min(args.jobs, len(jobs))) as pool:
        res = pool.map(_run, jobs)
    runs = {f"{r['variant']}@{r['ctx']}": r for r in res}
    base = {ctx: runs[f"base@{ctx}"] for ctx in CTXS}
    for ctx, want in ((1048576, (390.06, 3809.4)), (200000, (373.05, 4176.7))):
        assert abs(base[ctx]["ar_us"] - want[0]) < 0.02 and abs(base[ctx]["mtp_tok_s"] - want[1]) < 0.2, base[ctx]
    table = []
    for k in VARIANTS:
        row = dict(variant=k, spec=VARIANTS[k])
        for ctx in CTXS:
            r, b = runs[f"{k}@{ctx}"], base[ctx]
            tag = "1m" if ctx == 1048576 else "200k"
            row[f"ar_us_{tag}"] = r["ar_us"]
            row[f"ar_tok_s_{tag}"] = r["ar_tok_s"]
            row[f"mtp_tok_s_{tag}"] = r["mtp_tok_s"]
            row[f"d_ar_pct_{tag}"] = round(100 * (r["ar_tok_s"] / b["ar_tok_s"] - 1), 3)
            row[f"d_mtp_pct_{tag}"] = round(100 * (r["mtp_tok_s"] / b["mtp_tok_s"] - 1), 3)
        table.append(row)
    ref = lambda a, b_, tag: dict(  # noqa: E731
        ar_pct=round(100 * (runs[f"{a}@{tag}"]["ar_tok_s"] / runs[f"{b_}@{tag}"]["ar_tok_s"] - 1), 3),
        mtp_pct=round(100 * (runs[f"{a}@{tag}"]["mtp_tok_s"] / runs[f"{b_}@{tag}"]["mtp_tok_s"] - 1), 3))
    increments = {f"{a}_vs_{b_}@{ctx}": ref(a, b_, ctx) for ctx in CTXS for a, b_ in (
        ("nh_scan", "chase"), ("nh_scan", "central4_chase"), ("nh_scan", "base_routed_bus"),
        ("nh_attn_exact", "base"), ("nh_both", "nh_scan"), ("cp8_nh_scan", "cp8_chase"),
        ("cp8_nh_scan", "cp8_routed_bus"), ("cp8_nh_both", "cp8_nh_scan"), ("base", "base_routed_bus"))}
    exposure = {}
    for ctx in CTXS:
        e = {}
        for mode in ("ar", "mtp_verify"):
            cp = base[ctx]["critical_path_attention_us"][mode]
            g = lambda *ks: round(sum(cp.get(k, 0.0) for k in ks), 3)  # noqa: E731
            e[mode] = dict(index_scan_read_us=g("attn.idx.score"), index_topk_local_us=g("attn.idx.topk_local"),
                           index_merge_final_us=g("attn.idx.topk_merge", "attn.idx.topk_final"),
                           selected_kv_gather_latency_us=g("attn.gather"),
                           selected_kv_cross_die_allgather_us=g("attn.rows_allgather"),
                           attention_compute_us=g("attn.scores", "attn.max", "attn.exp", "attn.den", "attn.sink",
                                                  "attn.normalize"))
        e["ar_token_us"] = base[ctx]["ar_us"]
        e["ar_index_scan_pct_of_token"] = round(100 * (e["ar"]["index_scan_read_us"] + e["ar"]["index_topk_local_us"])
                                                / base[ctx]["ar_us"], 2)
        e["ar_routed_bus_exposure_us"] = round(runs[f"base_routed_bus@{ctx}"]["ar_us"] - base[ctx]["ar_us"], 3)
        exposure[str(ctx)] = e
    l20_sat = {ctx: base[ctx]["ar_sat_tok_s"] for ctx in CTXS}
    out = dict(
        schema="opentallas.dsrom.nearhbm.v1",
        q1_exposure=exposure,
        key_wire_power_l20_die_saturated_w_1m=None,
        scope="MODEL ONLY: no RTL, no P&R.  S58 product basis of tools/uarch_model.py, per logical die (TP-4, 4 stacks).",
        source_sha256={k: sha(p) for k, p in SRC.items()} | {"tool": sha("tools/dsrom_nearhbm.py")},
        q1_ledger=ledger(), variants=table, increments=increments, physical=physical(),
        runs={k: dict(v, spec=v["spec"]) for k, v in sorted(runs.items())},
        exactness=dict(
            nh_scan="class A: a key's score (dots_q4 blocks + csum, ReLU x w, reduce_rows over 32 heads) is key-local; "
                    "topk_lowest_index over the union of per-stack top-512 lists concatenated in position order keeps "
                    "the golden's tie order (stack-major proof, results/rtl/v41_idx_stack_major_ingest.json); the "
                    "candidate-block max needs 8-position blocks inside one stack (16-key round-robin groups satisfy it)",
            nh_attn="only q.k is row-local.  The golden forms P x V as one sequential sum over the 640 rows from +0 "
                    "(attend -> dots) and den with reduce_rows' 8-way interleave, after a single max over all rows: "
                    "per-stack partials with an (m, l, acc) merge are NOT bit-exact (class C), and the parallelism "
                    "study already rejected context-parallel attention for the same reason.  The exact form moves "
                    "only the scores, so the rows (K = V) still cross the die."),
    )
    out["key_wire_power_l20_die_saturated_w_1m"] = round(
        out["q1_ledger"]["key_wire_energy"]["L20_die_mJ_per_token_1m"] * 1e-3 * l20_sat[1048576], 2)
    raw = (json.dumps(out, indent=1, sort_keys=True) + "\n").encode()
    if args.check:
        assert OUT.read_bytes() == raw, "record differs"
        print("check: identical")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(raw)
    for r in table:
        print(f"{r['variant']:18s} 1M AR {r['ar_us_1m']:8.2f} us {r['d_ar_pct_1m']:+7.3f}% MTP {r['d_mtp_pct_1m']:+7.3f}%"
              f" | 200K AR {r['d_ar_pct_200k']:+7.3f}% MTP {r['d_mtp_pct_200k']:+7.3f}%")
    print(json.dumps(increments, indent=0))


if __name__ == "__main__":
    main()
