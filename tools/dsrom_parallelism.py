#!/usr/bin/env python3
"""DeepSeek-V4.1 ROM array: parallelism mapping study (PP / TP / EP / CP and per-operator hybrids).

Model only: no RTL, no P&R, no pinned file modified.  Every candidate is priced with the unified model
(tools/uarch_model.py cons_v41_rom, the S58 selection's own settings from tools/dsrom_4096_partition_token_options.py)
through the opt-in extensions tools/uarch_model_parallelism.py (this study) and tools/uarch_model_par2_boundary.py
(the PAR2 boundary term, branch claude/dsrom-par2-boundary-20261003 aafbe3a75).
Writes results/uarch/dsrom_parallelism_20261003/model.json (refuses to overwrite with different bytes).
"""
import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import uarch_model as u  # noqa: E402
import uarch_model_par2_boundary as X  # noqa: E402
import uarch_model_parallelism as M  # noqa: E402

OUT = ROOT / "results/uarch/dsrom_parallelism_20261003"
CAP = ROOT / "results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json"
CTXS = (1048576, 200000)
S = 58
PINNED = {1048576: (2563.7, 3809.4), 200000: (2680.6, 4176.7)}          # S58, unified model, no PAR2 term
PAR2_PINNED = {1048576: (2347.4, 3539.3), 200000: (2445.0, 3854.2)}     # dsrom_par2_boundary_20261003 owner_fc4

# ---- physical facts carried from records (each cited) ---------------------------------------------------------------
DIE = dict(
    reticle_mm2=858.0,                     # 26 x 33 mm (dsrom_l20_reticle_prerequisite_20261002/model.json:145669)
    screen_par2_mm2=759.44,                # selected PAR2 die reservation screen (model-r4.json:129; review Part 1)
    screen_reframed_mm2=786.23,            # option (c): q/BF elements re-framed to <= 0.60 instance utilisation
    element_util_reframed=0.60,            # design target vs the 0.375 closed / 0.72 first-failure ceiling
    element_util_current_q=0.723,          # q pair frame 510.84 x 151.2 um (failing band 0.72-0.83)
    q_pair_mm2_reframed=0.093039,          # 521.64 x 178.47 um
    payload_B_per_die=10206100496 / 8 / 2,  # S58 TP-4 rank payload / 2 PAR2 dies (partition_token_options.json)
    pairs_per_die=2048,                    # NP2048
    cooling_limit_w=474.56,                # liquid, two-die package (uarch_model COOLING_LIMIT_W)
)
FC4 = "fc4"


def _kmax_fn(bins):
    return lambda P: M.kmax(6 if P == 1 else u.A.distinct_experts(P, 384, 6), bins)


def _dispatch_fn(P_payload_B=5440):
    """EP with x only on the hub die: x (5,120 FP8 codes + 160 UE8M0 scales + ids/weights) one way over the board."""
    def f(P):
        clk = u.PRODUCT_CLOCK_HZ
        return M.board_one_way_s(clk) + P_payload_B * P / M.fabric(8, FC4).link_bw
    return f


ATT_HEAD_NODES = (".attn.q_rope", ".attn.scores", ".attn.pv", ".attn.max", ".attn.exp", ".attn.den", ".attn.sink",
                  ".attn.normalize", ".attn.z_quant", ".ffn.softplus_sqrt", ".ffn.shared_swiglu", ".ffn.shared_quant")
DENSE_KEYS = ("a_proj", "wq_b", "wo_a", "wo_b", "router", "shared_gu", "cmp.wk")


def mappings():
    ag_merge_scale = 2.0          # a W=8 merge carries 8 x 512 candidates where the TP-4 graph carries 4 x 512
    hub_tp1 = dict(field={k: "tp1" for k in DENSE_KEYS} | {"experts_gu": "ep", "down": "ep"}, ep_dies=8,
                   issue_scale={s: 4.0 for s in ATT_HEAD_NODES}, group=8, board=FC4, ep_combine=True,
                   coll={s: ("remove",) for s in (".attn.a_allgather", ".attn.rows_allgather", ".attn.out_allreduce",
                                                  ".ffn.router_allgather", ".attn.idx.topk_merge", ".attn.cand.merge")}
                   | {".ffn.combine_allreduce": ("board_gather", 5120 * 4, M.ID_ORDER_SUM_S)},
                   _kmax_P=_kmax_fn(8), dispatch_s=_dispatch_fn(), cp=dict(W=1, stacks=4))
    c4 = copy.deepcopy({k: v for k, v in hub_tp1.items() if not callable(v)})
    c4.update(_kmax_P=_kmax_fn(8), dispatch_s=_dispatch_fn(), cp=dict(W=8, stacks=2))
    c4["coll"] = dict(c4["coll"])
    c4["coll"][".attn.idx.topk_merge"] = ("respan", ag_merge_scale, 8)
    c4["coll"][".attn.cand.merge"] = ("respan", ag_merge_scale, 8)
    tp8_attn = {".attn.out_allreduce": ("respan", 1.0, 8), ".attn.rows_allgather": ("respan", 1.0, 8),
                ".attn.idx.topk_merge": ("respan", ag_merge_scale, 8), ".attn.cand.merge": ("respan", ag_merge_scale, 8)}
    c3 = dict(field={k: "tp" for k in DENSE_KEYS} | {"experts_gu": "kalign", "down": "kalign"}, kalign_factor=16 / 9,
              tp_group=8, group=8, board=FC4, cp=dict(W=8, stacks=2),
              coll=tp8_attn | {".attn.a_allgather": ("respan", 1.0, 8), ".ffn.router_allgather": ("respan", 1.0, 8),
                               ".ffn.combine_allreduce": ("replace", [("all_reduce", 7 * 5120 * 4, 8)])})
    sym = dict(field={k: "tp" for k in DENSE_KEYS} | {"a_proj": "replicate", "router": "replicate",
                                                      "cmp.wk": "replicate"},
               tp_group=8, group=8, board=FC4, cp=dict(W=8, stacks=2),
               issue_scale={".ffn.softplus_sqrt": 4.0},     # every die computes all 384 sqrt(softplus) scores
               coll=tp8_attn | {".attn.a_allgather": ("remove",), ".ffn.router_allgather": ("remove",)})
    c4b = copy.deepcopy(sym)
    c4b["field"].update(experts_gu="ep", down="ep")
    c4b.update(ep_dies=8, _kmax_P=_kmax_fn(8), ep_combine=True)
    c4b["coll"][".ffn.combine_allreduce"] = ("a2a", 5120 * 4, M.ID_ORDER_SUM_S)
    c5r = copy.deepcopy(sym)
    c5r["coll"][".ffn.combine_allreduce"] = ("replace", [("all_gather", 8 * 7 * 304 * 4, 8),
                                                         ("all_gather", 5120 * 4, 8)])
    c5 = copy.deepcopy(sym)
    c5["field"].update({"a_proj": "tp", "router": "tp", "cmp.wk": "tp"})
    c5["issue_scale"] = {}
    c5["coll"].update({".attn.a_allgather": ("respan", 1.0, 8), ".ffn.router_allgather": ("respan", 1.0, 8)})
    c5["coll"][".ffn.combine_allreduce"] = ("replace", [("all_gather", 8 * 7 * 304 * 4, 8),
                                                        ("all_gather", 5120 * 4, 8)])
    c5h = dict(copy.deepcopy(c5), head_ways=8)
    c5hc = dict(copy.deepcopy(c5h), chase=True)
    c5hc4 = dict(copy.deepcopy(c5hc), cp=dict(W=8, stacks=4))
    return [
        ("M0_model_S58_TP4", None, None, "unified model as pinned (TP-4 rank dies, no PAR2 term): reference only"),
        ("C1_PP58_TP4_PAR2rows", "par2", None,
         "current: TP-4 ranks, each rank's matrices split by output rows over a 2-die package (PAR2 owner, fc4 quad)"),
        ("C1x_PAR2rows_exactMoE", "par2", dict(group=4, board="par2", coll={".ffn.combine_allreduce": (
            "replace", [("all_gather", 68096, 4), ("all_gather", 5120 * 4, 4)])}),
         "C1 with the MoE combine as the bit-exact two-gather row split (v41_tp_exact_reprice) instead of the "
         "modelled (inexact) FP32 K-split all-reduce"),
        ("C2_PP58_EP8_hubTP1", None, hub_tp1,
         "1 hub die (all dense weights TP-1, SU/Sinkhorn, attention, KV + index keys on its 4 stacks) + 8 expert "
         "dies holding whole experts; dispatch/combine over the board; no CP"),
        ("C3_PP58_TP8_megatron", None, c3,
         "TP-8 over 4 packages: column-parallel a_proj/router/gu, head-parallel attention, row-parallel (K-split) "
         "down with golden-chunk-aligned shares and an exact fixed-tree all-reduce of 7 per-expert partials"),
        ("C4_PP58_EP8_hub_CP8", None, c4, "C2 + index keys context-parallel over 8 expert dies' HBM, exact merge"),
        ("C4b_PP58_TP8sym_EP8_CP8", None, c4b,
         "symmetric: every die runs the replicated hub chain; a_proj/router replicated; head-parallel attention; "
         "routed experts whole (EP-8) with an all-gather combine summed in id order; CP-8 index keys"),
        ("C5r_hybrid_replicated_small", None, c5r,
         "C5 but a_proj/router/cmp.wk replicated on every die to drop their all-gathers (rejected sub-option)"),
        ("C5_PP58_TP8_hybrid", None, c5,
         "per-operator hybrid, TP-8 symmetric peers (no owner die): column-parallel a_proj/router + all-gather; "
         "head/o-group-parallel attention + aligned wo_b fixed-tree all-reduce; routed+shared experts output-row "
         "split (column gu, act all-gather, row down, y all-gather); CP-8 index keys; mHC/Sinkhorn/SU chain "
         "replicated bit-identically on every die"),
        ("C5h_hybrid_head8", None, c5h, "C5 + lm_head vocabulary split 8 ways over the 8 head dies"),
        ("C5hc_hybrid_head8_chase", None, c5hc,
         "C5h + streamed local top-k (dsrom_stage_balance_20261003 'chase'): RECOMMENDED"),
        ("C5hc4_hybrid_4stacks", None, c5hc4, "C5hc with 4 HBM stacks per physical die (sensitivity, 2x stacks)"),
    ]


def price(ctx, par2, cfg):
    cap = json.loads(CAP.read_text())
    rows = {r["stages"]: r for r in cap["all_stage_capacity_rows"]}
    saved = copy.deepcopy(u.PRESETS["proposal"])
    u.PRESETS["proposal"]["bf16_stripe_macros"] = 2 * rows[S]["BF16_pairs_per_die"]
    led, extra, plans = [], {}, []
    orig_cool, orig_occ = u._cons_cooling, u._cons_occupancy

    def cool(die_static, die_static_ungated, cats, pair_s, pp, dyn_scale, sat, S_, tot):
        lt = {k: v for k, v in tot.items() if k != "head"}
        extra["layer_cooling"] = orig_cool(die_static, die_static_ungated, cats, pair_s, pp, dyn_scale, sat, S_, lt)
        extra["layer_occ"] = lt
        return orig_cool(die_static, die_static_ungated, cats, pair_s, pp, dyn_scale, sat, S_, tot)
    u._cons_cooling = cool
    kw = dict(bf16="columns", clock_hz=u.PRODUCT_CLOCK_HZ, field_concurrency=u.FIELD_CONCURRENCY,
              added_latency=dict(u.SOFTPLUS_FIX, **u.W11_STREAM_SS, **u.PLUS_LAT), dyn_scale=u.PRODUCT_DYN_SCALE,
              slow_domain=(.9e9, "w18"), elem_stages=8, ss_wire=True, serial=u.PRODUCT_SERIAL,
              die=u.DIE_SHRUNK_INTERIM, vmh=u.VMC_FUSED, hub_block=u.PRODUCT_HUB)
    try:
        with u._cons_ctx(ctx):
            if par2:
                pcfg = X.default_cfg("owner", board="fc4")
                p2led = []
                with X._wrapped(pcfg, S, p2led):
                    if cfg is not None:
                        cfg = dict(cfg)
                        if cfg.get("board") == "par2":
                            cfg["_fabric"] = X._fabrics(pcfg)[1]
                        with M.wrapped(cfg, led):
                            p = u.cons_v41_rom(S, 8, 36, **kw)
                    else:
                        with M.wrapped(dict(coll={}), led):    # no-op mapping: only for the path ledger
                            p = u.cons_v41_rom(S, 8, 36, **kw)
            elif cfg is None:
                with M.wrapped(dict(coll={}), led):
                    p = u.cons_v41_rom(S, 8, 36, **kw)
            else:
                p = M.cons_v41_rom_mapping(S, 8, 36, mapping=cfg, ledgers=led, **kw)
    finally:
        u.PRESETS["proposal"].clear()
        u.PRESETS["proposal"].update(saved)
        u._cons_cooling, u._cons_occupancy = orig_cool, orig_occ
    lo = extra["layer_occ"]
    vals = list(lo.values())
    p1 = next(x for x in led if x["P"] == 1)
    return dict(ctx=ctx, ar_tok_s=p["ar_tokens_s_b1"], mtp_tok_s=p["mtp_tokens_s_b1"],
                ar_token_us=round(1e6 / p["ar_tokens_s_b1"], 2), ar_saturated_tok_s=p["ar_saturated_tokens_s"],
                mtp_saturated_tok_s=p["mtp_saturated_tokens_s"], busiest_stage=p["busiest_stage"],
                busiest_stage_us=p["busiest_stage_us"], stage_hops=p["stage_hops"],
                layer_stage_max_over_mean=round(max(vals) / (sum(vals) / len(vals)), 2),
                layer_stage_max_us=round(max(vals) * 1e6, 2), layer_stage_mean_us=round(sum(vals) / len(vals) * 1e6, 3),
                path_us=p1["path_us"], path_T_us=p1["T_us"],
                rank_layer_die_static_w=extra["layer_cooling"]["layer_die_static_w"],
                rank_layer_die_hottest_w=extra["layer_cooling"]["layer_die_busiest_w_saturated"],
                rank_layer_die_mean_w=extra["layer_cooling"]["layer_die_mean_w_saturated"],
                capacity_users_1m_model=p["capacity_users_1m"],
                fixed_part_ns=p1.get("fixed_part_ns")), led


def physical(cid, r_by_ctx):
    """Dies, packages, stacks, area, utilisation, power, links: per candidate (per physical die)."""
    hub = cid.startswith(("C2", "C4_"))
    per_stage = 9 if hub else 8
    layer_dies = per_stage * S
    head, table = 8, 36
    dies = layer_dies + head + table
    if hub:
        stacks = S * (4 if cid.startswith("C2") else 18) + 4 * head
    elif cid.startswith("C5hc4"):
        stacks = layer_dies * 4 + 4 * head
    elif cid.startswith(("C3", "C4b", "C5")):
        stacks = layer_dies * 2 + 4 * head
    else:
        stacks = 4 * (4 * S + head)       # model: 4 per rank (PAR2: on shard 0)
    # replicated small dense matrices (a_proj | router | cmp.wk) on every die of the stage: 7 extra copies
    c = u.A._env()["c"]
    D_ = c["hidden_size"]
    a_proj_B = 9.6e6          # full a_proj (wq_a | wkv | idx weights_proj | compressor), words x 33 B from the graph
    router_B = 384 * D_ * 2
    rep_B_per_die = 7 * (a_proj_B + router_B) * 40 / layer_dies if cid.startswith(("C4b", "C5r")) else 0.0
    pair_B = DIE["payload_B_per_die"] / DIE["pairs_per_die"]
    rep_pairs = math.ceil(rep_B_per_die / pair_B)
    screen = DIE["screen_reframed_mm2"] + rep_pairs * DIE["q_pair_mm2_reframed"]
    if hub:
        # 8 expert dies hold the stage's experts (5.0 GB / 8 = 0.62 GB <= 0.638 GB); the hub holds the stage's dense
        # (~0.69 layers x ~210 MB) on the same die design: same screen
        pass
    out = dict(layer_dies=layer_dies, total_dies=dies, packages=dies // 2, hbm_stacks=stacks,
               dies_per_stage=per_stage, replicated_bytes_per_die=round(rep_B_per_die), replicated_pairs_per_die=rep_pairs,
               per_die_screen_mm2=round(screen, 2), per_die_screen_pct_of_reticle=round(100 * screen / DIE["reticle_mm2"], 1),
               element_instance_utilisation=DIE["element_util_reframed"],
               element_utilisation_vs_ceiling="0.60 target (re-framed q/BF pairs); empirical closed 0.375, failures from 0.72")
    if cid.startswith("C1"):
        out["per_die_screen_mm2"] = DIE["screen_reframed_mm2"]
        out["note"] = "PAR2 as selected; option (c) re-frame assumed for every candidate"
    # power per physical die: the rank die's static (fixed services replicated on every physical die) + its share of
    # the hottest layer stage's dynamic power at saturation
    pw = {}
    for ctx, r in r_by_ctx.items():
        st, hot, mean = r["rank_layer_die_static_w"], r["rank_layer_die_hottest_w"], r["rank_layer_die_mean_w"]
        if hub:
            hub_w = st + 4 * 0.88 * (hot - st)       # the hub carries the 4 ranks' non-expert dynamic (88% of issue)
            exp_w = st + 0.12 * 4 * (hot - st) / 8 * 2
            pw[str(ctx)] = dict(hub_die_w=round(hub_w, 1), expert_die_w=round(exp_w, 1),
                                fits=hub_w <= DIE["cooling_limit_w"])
        else:
            phys = st + (hot - st) / 2
            pw[str(ctx)] = dict(hottest_die_w=round(phys, 1), mean_die_w=round(st + (mean - st) / 2, 1),
                                fits=phys <= DIE["cooling_limit_w"])
    out["power_w_saturated"] = pw
    layer_stacks = stacks - 4 * head
    out["kv_capacity_users"] = {str(ctx): int(r["capacity_users_1m_model"] * layer_stacks / (4 * 4 * S))
                                for ctx, r in r_by_ctx.items()}
    out["kv_capacity_basis"] = "unified model capacity_users_1m (at the run's context) x layer HBM stacks / 928"
    sat = r_by_ctx[1048576]["ar_saturated_tok_s"]
    b = BOUNDARIES.get(cid.split("_")[0], {})
    out["boundaries"] = b
    if b.get("board_bytes_per_layer_per_die"):
        out["board_link_utilisation_at_1M_saturation"] = round(
            b["board_bytes_per_layer_per_die"] * 40 * sat / layer_dies * per_stage / M.fabric(8, FC4).pkg_bw * 2, 4)
    return out


# Per-boundary traffic per layer (one position), from the mapping's collectives (payloads as priced above).
BOUNDARIES = {
    "M0": dict(note="model rank dies; collectives over 2 packages (mesh)"),
    "C1": dict(in_package_ucie="PAR2 owner crossing: 6 exposed steps a layer x 2 one-way (65.2 ns); 1,050 crossing "
                               "calls/token; need 0.91 TB/s of 4.2 TB/s (4.6x headroom; dsrom_par2_boundary_20261003)",
               board="TP-4 collectives over 4 packages (fc4): a_allgather, out_allreduce, router_allgather, "
                     "combine_allreduce (+ merges / rows on scan layers); 57 stage hops",
               board_bytes_per_layer_per_die=3648 + 20480 + 1536 + 20480),
    "C1x": dict(board="as C1 with the combine as act all-gather 68 KB + y all-gather 20 KB",
                board_bytes_per_layer_per_die=3648 + 20480 + 1536 + 68096 + 20480),
    "C2": dict(board="dispatch hub -> <=6 expert dies one way (205 ns + 5.4 KB); combine 6 x 20 KB FP32 into the hub "
                     "(205 ns + 104 ns at the hub package's 1.19 TB/s ingress) + id-order sum; 57 stage hops",
               board_bytes_per_layer_per_die=5440 + 6 * 20480),
    "C3": dict(board="TP-8 over 4 packages: a_allgather, router_allgather, out_allreduce, MoE all-reduce of 7 per-expert "
                     "partials 143 KB (823 ns on the fabric), rows/merges on scan layers",
               board_bytes_per_layer_per_die=3648 + 1536 + 20480 + 143360),
    "C4": dict(board="as C2 + CP merge 8 x 512 candidates to the hub on scan layers",
               board_bytes_per_layer_per_die=5440 + 6 * 20480),
    "C4b": dict(board="TP-8: out_allreduce 20 KB, EP all-gather combine (kmax 2.18 experts x 20 KB; 590 ns), rows "
                      "all-gather 215 KB / merges on scan layers", board_bytes_per_layer_per_die=20480 + 6 * 20480),
    "C5r": dict(board="as C5 without a_allgather / router_allgather", board_bytes_per_layer_per_die=20480 + 68096 + 20480),
    "C5": dict(board="TP-8 over 4 packages (2 dies/package UCIe + fc4 board): a_allgather 3.6 KB, router_allgather 1.5 "
                     "KB, out_allreduce 20 KB (fixed pairwise tree), act all-gather 68 KB, y all-gather 20 KB; rows "
                     "all-gather 215 KB and 8-way merges on scan layers; 57 stage hops (die-to-counterpart)",
               board_bytes_per_layer_per_die=3648 + 1536 + 20480 + 68096 + 20480),
}
for _k in ("C5h", "C5hc", "C5hc4"):
    BOUNDARIES[_k] = BOUNDARIES["C5"]


def link_table():
    clk = u.PRODUCT_CLOCK_HZ
    f8 = M.fabric(8, FC4)
    return dict(
        ucie_in_package=dict(one_way_ns=round(M.ucie_one_way_s(clk) * 1e9, 1), bytes_s=M.links()["rom_package_ucie"]["bw"],
                             src="technology.json links.rom_package_ucie (10 ns incl. 1.5 ns on-die) + 2 x 34 VM->PHY "
                                 "stages (W18b); uarch_model_par2_boundary one_way_s"),
        board_light_fec=dict(one_way_ns=round(M.board_one_way_s(clk) * 1e9, 1), link_bytes_s_fc4=f8.link_bw,
                             package_bytes_s=f8.pkg_bw,
                             src="arch_budget_v41.BASELINE board_hop_s 130 ns + 2 x 45 VM->SerDes stages; "
                                 "technology.json rom_board_serdes (90 lanes per 2-die package, fc4 = 5 links)"),
        fabric_8die_fc4_examples_ns={f"{op}_{pay}B": round(M._fcost(f8, op, pay, 8) * 1e9, 1) for op, pay in (
            ("all_gather", 3648), ("all_gather", 68096), ("all_gather", 20480), ("all_reduce", 20480),
            ("all_reduce", 143360), ("all_gather", 215040))},
        board_a2a_kmax_2p18_ns=round(sum(f8.combine_a2a(20480, 1, M.kmax(6, 8), 8)[k] for k in ("latency_s", "bytes_s")) * 1e9, 1))


EXACTNESS = {
    "M0_model_S58_TP4": dict(class_="model proxy", verdict="NOT exact as priced",
                             why="the graph prices the MoE combine as an FP32 all-reduce of intermediate-K partials "
                                 "(decode_critical_path v41_moe); FF=2304 = 9 golden chunks cannot be cut 4 ways on "
                                 "chunk boundaries, and the golden sums whole experts in id order "
                                 "(hdc_golden_v41.py csum 189-206, moe 980-990; v41_tp_exact_reprice docstring)"),
    "C1_PP58_TP4_PAR2rows": dict(class_="A for the PAR2 boundary", verdict="exact if the MoE is the row split",
                                 why="PAR2 cuts no reduction (model-r4 source_reduction_region_cut_count 0); the rate is "
                                     "priced on the model's all-reduce MoE combine (see M0)"),
    "C1x_PAR2rows_exactMoE": dict(class_="A", verdict="exact",
                                  why="output-row split of every matrix (full K per row) + id-order expert sum per row"),
    "C2_PP58_EP8_hubTP1": dict(class_="A", verdict="exact",
                               why="whole matrices and whole experts; the hub sums expert FP32 outputs in id order "
                                   "(golden seqsum), then the shared expert"),
    "C3_PP58_TP8_megatron": dict(class_="A only with aligned shares", verdict="exact but imbalanced",
                                 why="row-parallel down is a K split: exact only on golden chunk boundaries of the "
                                     "padded pairwise tree (FF 9 chunks -> shares [2,2,2,2,1,0,0,0]) and only if each "
                                     "expert's partials are tree-reduced separately in fixed order before the id-order "
                                     "sum (7 x 20 KB payload); a ring all-reduce or summing experts first is NOT exact"),
    "C4_PP58_EP8_hub_CP8": dict(class_="A", verdict="exact",
                                why="C2 + per-key index scores; local top-512 lists concatenated in position order into "
                                    "one tselect_final (golden topk_lowest_index tie order)"),
    "C4b_PP58_TP8sym_EP8_CP8": dict(class_="A", verdict="exact",
                                    why="replicated chains are bit-identical; head/o-group split cuts no reduction; wo_b "
                                        "K split = 4-chunk aligned subtrees of the 32-chunk padded tree, combined in "
                                        "fixed pairwise order; experts whole; id-order sum"),
    "C5_PP58_TP8_hybrid": dict(class_="A", verdict="exact",
                               why="as C4b for attention/replication/CP; experts output-row split with full K per row "
                                   "(no K cut), local id-order sum per row"),
}
EXACTNESS["C5r_hybrid_replicated_small"] = dict(EXACTNESS["C5_PP58_TP8_hybrid"])
for k in ("C5h_hybrid_head8", "C5hc_hybrid_head8_chase", "C5hc4_hybrid_4stacks"):
    EXACTNESS[k] = dict(EXACTNESS["C5_PP58_TP8_hybrid"], why=EXACTNESS["C5_PP58_TP8_hybrid"]["why"]
                        + "; lm_head vocabulary split 8 ways with a lowest-index argmax merge; chase streams the same "
                          "tselect (order unchanged)")
CP_ATTENTION_REJECTED = (
    "Context-parallel attention softmax is rejected: R = 128 window + 512 selected rows per head is independent of "
    "context (decode_critical_path v41_attention), so splitting it buys nothing, and a partial-softmax combine "
    "(running max rescale + split denominators) does not reproduce the golden's single-pass max, exp(s - max) and "
    "P=8-interleaved reduce_sum order (hdc_golden_v41.py 47, 444-457).  The only context-linear work is the index "
    "scan + top-k (dsrom_stage_balance_20261003: 17.02 of the 17.01 us 1M-200K difference), which CP splits exactly.")


RECOMMENDATION = dict(
    mapping="C5hc_hybrid_head8_chase",
    statement=(
        "Drop PAR2's owner/row-split boundary: make the 8 physical dies of each S58 stage symmetric TP-8 peers, each "
        "running the bit-identical hub chain (SU, mHC/Sinkhorn, norms) on a replicated residual.  Per operator: "
        "a_proj / router column-parallel + small all-gathers (replication priced worse: BF16 router on one die's "
        "BF pairs costs +29 us); attention head/o-group parallel (8 heads, 1 o-group per die) with wo_b's K split on "
        "4-chunk aligned subtrees and a fixed pairwise-tree all-reduce; routed and shared experts output-row split "
        "(column gu, act all-gather, full-K row down, local id-order sum, y all-gather), NOT EP (busiest-die read "
        "x2.9 at E[kmax]=2.18 and a 6x combine payload: -4.9% AR / -22% MTP) and NOT Megatron K-split (unaligned "
        "FF chunks: imbalance 1.78x and a 143 KB per-expert all-reduce: MTP -11%); index keys context-parallel over "
        "the 8 dies' HBM with the position-ordered exact merge and the streamed top-k (chase); attention softmax "
        "not split; lm_head 8 ways over the 8 head dies; PP over 58 stages; MTP m=1 time-multiplexed on the same "
        "mapping.  Same 508 dies / 254 packages / 960 stacks as the current system."),
    measure_first_in_rtl=[
        "8-die (4-package) all-gather and fixed-order pairwise all-reduce latency at the die's 64-B flit, including "
        "blocking COLL and backpressure (C7 found overlap worse than modelled: 8,622 -> 7,579 tok/s)",
        "the MoE two-gather schedule (act 68 KB after quant2, y 20 KB after the local id-order sum) against the "
        "golden at full shape (v41_tp_exact_reprice required_collective_bench)",
        "wo_b 8-way aligned K split + fixed tree reduce bit-exact against hdc_golden_v41 csum (chunk8)",
        "bit-identical replicated hub chains on 8 dies (same inputs, same order): a two-die lockstep check",
        "CP-8 index scan: striped key writer/scanner, position-ordered tselect_final at 8 x 512, tie order",
        "the streamed top-k (chase) in RTL",
        "lm_head 8-way vocabulary split + lowest-index argmax merge"],
    regenerate=[
        "tools/uarch_model.py cons_v41_rom: a TP-8 physical-die mode (group 8, 2 dies/package, fc4), the exact MoE "
        "two-gather in decode_critical_path.v41_moe, lm_head 8-way, CP-8 scans (today an extension only)",
        "results/uarch/dsrom_parallel_owner_binding_20261002 native_shard_choices (no owner shard: per-die TP-8 "
        "shares; head/o-group ownership)",
        "results/uarch/dsrom_reticle_fixed_debit_reconciliation_20261002 model-r4 PAR2 boundary / return-port "
        "ledger (the remote result port and activation packet disappear; collective ports instead)",
        "results/uarch/dsrom_4096_comparable_capacity_20261002 partition_token_options (per physical die rows)",
        "results/uarch/dsrom_par2_boundary_20261003 (superseded as the selected mapping; kept as evidence)",
        "results/uarch/dsrom_stage_balance_20261003 options (CP-8 and chase now part of the mapping)",
        "die HBM placement: 2 stacks per physical die (was 4 on the PAR2 shard-0 die), shoreline/PHY plan",
        "coordinated no-ECC model, macro inventory and physical contracts (AGENTS.md ROM policy)",
        "results/arch/v41_tp_exact_reprice.json at TP-8, and the C7 collective exposure campaign at 8 dies"],
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT / "model.json"))
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    cands = []
    for cid, par2, cfg, note in mappings():
        if a.only and cid not in a.only.split(","):
            continue
        rs = {}
        for ctx in CTXS:
            r, _ = price(ctx, par2, cfg)
            rs[ctx] = r
            print(json.dumps(dict(id=cid, ctx=ctx, ar=r["ar_tok_s"], mtp=r["mtp_tok_s"], us=r["ar_token_us"],
                                  sat=r["ar_saturated_tok_s"], bal=r["layer_stage_max_over_mean"], path=r["path_us"])),
                  flush=True)
        cands.append(dict(id=cid, note=note, par2=bool(par2),
                          mapping={k: v for k, v in (cfg or {}).items() if not k.startswith("_") and not callable(v)},
                          results={str(k): v for k, v in rs.items()}, physical=physical(cid, rs),
                          exactness=EXACTNESS.get(cid)))
    if a.only:
        return
    for ctx, (ar, mtp) in PINNED.items():
        b = next(c for c in cands if c["id"] == "M0_model_S58_TP4")["results"][str(ctx)]
        if (b["ar_tok_s"], b["mtp_tok_s"]) != (ar, mtp):
            raise SystemExit(f"baseline does not reproduce at {ctx}")
        c1 = next(c for c in cands if c["id"] == "C1_PP58_TP4_PAR2rows")["results"][str(ctx)]
        if (c1["ar_tok_s"], c1["mtp_tok_s"]) != PAR2_PINNED[ctx]:
            raise SystemExit(f"PAR2 record does not reproduce at {ctx}: {c1['ar_tok_s']} {c1['mtp_tok_s']}")
    ref = {ctx: next(c for c in cands if c["id"] == "C1_PP58_TP4_PAR2rows")["results"][str(ctx)] for ctx in CTXS}
    for c in cands:
        for ctx in CTXS:
            r, b = c["results"][str(ctx)], ref[ctx]
            r["ar_delta_pct_vs_C1"] = round(100 * (r["ar_tok_s"] / b["ar_tok_s"] - 1), 2)
            r["mtp_delta_pct_vs_C1"] = round(100 * (r["mtp_tok_s"] / b["mtp_tok_s"] - 1), 2)
    srcs = ["tools/uarch_model.py", "tools/uarch_model_parallelism.py", "tools/uarch_model_par2_boundary.py",
            "tools/dsrom_parallelism.py", "tools/decode_critical_path.py", "tools/arch_budget_v41.py",
            "tools/hdc_golden_v41.py", "configs/hardware/technology.json", str(CAP.relative_to(ROOT)),
            str(X.CHOICES.relative_to(ROOT))]
    rec = dict(schema="opentallas.dsrom.parallelism.v1", basis="DS4096 S58, unified model cons_v41_rom S58 settings",
               scope="Analytical only; dataflow levels 1-5; no RTL/P&R; nothing adopted.",
               source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in srcs},
               external_inputs=dict(
                   par2_boundary="origin/claude/dsrom-par2-boundary-20261003 aafbe3a75 results/uarch/"
                                 "dsrom_par2_boundary_20261003/model.json (reproduced here: C1)",
                   stage_balance="origin/claude/dsrom-stage-balance-20261003 91bb2323c results/uarch/"
                                 "dsrom_stage_balance_20261003 (chase, CP-8 scans, 8-way head)",
                   utilisation_review="/tmp/claude-review-20261003/dsrom_fit/dsrom_utilisation_redesign.{md,json} "
                                      "(option (c) re-frame 786.23 mm2; empirical ceiling 0.375 / 0.60 target)"),
               die=DIE, links=link_table(), baseline_reproduced=True, candidates=cands,
               cp_attention=CP_ATTENTION_REJECTED, recommendation=RECOMMENDATION)
    b = (json.dumps(rec, indent=1, sort_keys=True, default=str) + "\n").encode()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.read_bytes() != b:
        raise SystemExit(f"{out} exists with different bytes")
    out.write_bytes(b)
    print("wrote", out)


if __name__ == "__main__":
    main()
