#!/usr/bin/env python3
"""Top-down architecture budget of DeepSeek-V4.1-Flash: ROM array (packaging option b) and HBM comparator.

    python3 tools/arch_budget_v41.py [--out results/arch/arch_budget_v41.json] [--quick]

ONE BUDGET MODEL (unified 2026-09-27).  The specification document (docs/ARCH_SPEC_V41.md), the atlas's budget
sections and the adopted design point (tools/arch_utilization_v41.py -> arch_latency_ladder_v41.py ->
arch_hbm_best_v41.py -> arch_lanes_v41.py -> arch_hbm_switched_v41.py -> v41_rack_design.py) all read this module
and its record results/arch/arch_budget_v41.json.  It carries the 2026-09-27 user decisions: the official
checkpoint weight precision everywhere (FP8 per 32x32 block, FP4 routed experts, BF16 lm_head / router / compressor,
_precision_fix), online softmax adopted and norm folding rejected (lever "osm"), the measured hyper-connection depth
(126 cycles, 5,120 HC lanes per weight lane), MTP at the measured V4.1-Flash tau (TAU_HEADLINE, 3.65, read from
results/speculative/v41_flash_dspark_onpolicy_greedy.json; the published 3.5-4.1 band as sensitivities),
1M as the primary context and the validated static power terms.  Links: 4 HBM3E stacks per die, 130 ns light-FEC
board hop, 209 ns rack-cable stage hop.  Timing: decode_critical_path's pinned pre-pipeline RTL constants (K, FADD 5;
e6ba1efc).  Energy/power inputs: configs/hardware/technology.json.  The former split (a specification model here and
a design-point base in tools/arch_budget_v41_dp.py, ported from v41-rack-gates@0facdc17) is retired.

A vendor-style budget, in the order a product team writes one:

1. REQUIREMENT.  Tokens/s per user at batch 1 at 8K / 200K / 1M context, without and with MTP (DSpark),
   plus a batch curve to 64.  The requirement is the report's headline (packaging option (b):
   results/roofline/critical_path/decode_critical_path.json packaging_options), i.e. the silicon must deliver
   what the report publishes, or the report must change.
2. WORKLOAD.  One token's work from the model graph (configs/models/candidates/deepseek-v4.1-flash.json
   operator_config, the operator order of tools/hdc_golden_v41.py): MACs by op class, bytes by storage level,
   stream element-ops by function class, reductions with their sequential chain length under the golden's
   summation orders, top-k selections, collectives -- per token and per die (tensor group 4).
3. ROOFLINE per die: every resource's work per token against its rate, at the report's (DAG) widths and at
   the as-built RTL widths; which one binds at batch 1 (latency) and at batch 64 (occupancy).
4. BUDGET.  The token's dependency DAG (tools/decode_critical_path.v41_graph -- the report's own graph, so
   the budget and the headline share one structure) is re-priced node by node from a block SPEC (the widths
   and depths of every unit).  With every issue time zero the DAG gives the FIXED part of the token (unit
   pipeline depths, sequencer control, link latencies); what is left of the target is the ISSUE budget.
   It is split across the resources on the critical path by the area-optimal rule for serial stages,
   t_r ~ sqrt(area_r x work_r) (minimise sum area_r x work_r / t_r subject to sum t_r = budget), rounded
   to hardware granularity, and re-verified on the DAG (off-path branches can surface once widths shrink).
5. REQUIREMENTS per block (widths, latencies, bytes/cycle, buffers, issue rate), the chain-latency floor of
   every accumulation under the golden's orders (a sequential FP32 sum of n terms cannot finish in fewer than
   n x add-latency cycles however wide the engine), and the gap against the as-built RTL.
6. MTP: a verify pass of m = gamma+1 positions (weights read once per pass through an m-way lane multiplier;
   stream, attention and select work scale with m) plus the DSpark draft chain; tokens/s = tau / cycle, tau
   from configs/studies/speculative_profiles.json and results/roofline/speculative/hdc_design_faithful.json.
7. HBM comparator at iso total logic area: HBM3E stacks per die from beachfront, sustained efficiency,
   dense-weight prefetch across dependency points, and the data-dependent routed-expert fetch (the part
   routing makes hard) priced as exposed latency plus bytes.

Every constant names its source.  Areas are ASAP7 (the repository's node for routed evidence); the analytical
design's per-die compute area (N5) is used only as the envelope the block areas must fit.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

import decode_critical_path as D  # noqa: E402

SCHEMA = "opentallas.arch-budget-v41.v2"
OUT = ROOT / "results/arch/arch_budget_v41.json"
CONTEXTS = (8192, 200000, 1048576)
# User decision 2026-09-27: V4.1's primary context is 1M ("1M is the default for most agent APIs"); 200K is
# secondary, 8K tertiary.  The headline, the power check and the batch model's MTP design are taken at TARGET_CTX.
TARGET_CTX = 1048576
MTP_M_DESIGN = 2          # the lane multiplier; the knee rule picks m = 3 at 1M -- held at 2 pending the 1M push-the-rate study
BATCHES = (1, 2, 4, 8, 16, 32, 64)
HEADLINE_KEY = "b_two_die_group4_across_pair"
SPEC_PROFILES = ROOT / "configs/studies/speculative_profiles.json"
SPEC_FAITHFUL = ROOT / "results/roofline/speculative/hdc_design_faithful.json"
TECH = ROOT / "configs/hardware/technology.json"
PHYS = ROOT / "results/physical_abi3/asap7"

# -- measured unit constants (ASAP7) --------------------------------------------------------------------------------
def _phys(rel):
    p = PHYS / rel / "physical.json"
    return json.loads(p.read_text())["design"] if p.exists() else None


AREA_SRC = {
    "mac_bf16_um2": ("mac_bf16_fp32_pipe_round_stage", "pipelined BF16 x BF16 -> FP32 MAC, closed"),
    "blockdot_um2": ("hdc/v41/ot_hdc_blockdot", "FP8/FP4 32-element block dot + FP32 accumulate, closed"),
    "su_lane_um2": ("hdc/v41/ot_hdc_v41_su_lane", "V4.1 stream-unit lane (every function but the lane-0 ones), synthesis"),
    "su_lane0_um2": ("hdc/v41/ot_hdc_v41_su_lane_full", "V4.1 stream-unit lane 0 (all functions), synthesis"),
    "tselect16_um2": ("hdc/v41/ot_hdc_tselect_w16", "16-lane threshold select, K=512, routed, not closed"),
    "fp32_add_um2": ("hdc/ot_fp32_add_rne_pipe", "pipelined binary32 adder, closed"),
    "fp32_mul_um2": ("hdc/ot_hdc_fp32_mul_pipe", "pipelined binary32 multiplier"),
    "exp_um2": ("hdc/ot_hdc_exp_rebalanced_mul", "exp (49-cycle rebalanced)"),
    "recip_um2": ("hdc/ot_hdc_recip_rebalanced_mul", "reciprocal (28-cycle rebalanced)"),
    "sinkhorn_um2": ("hdc/v41/ot_hdc_sinkhorn", "one normalisation per unit clock"),
    "softplus_um2": ("hdc/v41/ot_hdc_softplus", "sqrt(softplus), closed"),
    "select_k512_um2": ("hdc/v41/ot_hdc_select_k512", "insertion top-512, 1 element/cycle, closed"),
    "engram_hash_um2": ("hdc/v41/ot_hdc_engram_hash", "Engram hash (reduced), closed"),
    "kv_stream_um2": ("hdc/kv/ot_hdc_kv_stream", "HBM KV streamer"),
}


def unit_areas():
    out, src = {}, {}
    for k, (rel, what) in AREA_SRC.items():
        d = _phys(rel)
        if d is None:
            d = _phys(rel.replace("hdc/", ""))
        out[k] = d["area_um2"] if d and d.get("area_um2") else None
        src[k] = dict(path=f"results/physical_abi3/asap7/{rel}/physical.json", what=what,
                      fmax_mhz=round(d["fmax_hz"] / 1e6, 1) if d and d.get("fmax_hz") else None,
                      closed=d.get("closed") if d else None)
    # derived per-width costs
    out["fp8_mac_um2"] = out["blockdot_um2"] / 32          # one block dot of 32 FP8/FP4 products per cycle
    out["fp32_mac_um2"] = out["fp32_add_um2"] + out["fp32_mul_um2"]
    # a stream lane without the transcendental functions: multiply, divide-free adds, max, rounding, reducer
    # partial -- two multipliers and three adders of the pipelined FP32 datapath plus 50% registers/muxing
    out["su_light_lane_um2"] = 1.5 * (2 * out["fp32_mul_um2"] + 3 * out["fp32_add_um2"])
    out["tselect_lane_um2"] = out["tselect16_um2"] / 16
    src["fp8_mac_um2"] = dict(what="blockdot area / 32 products per cycle")
    src["fp32_mac_um2"] = dict(what="fp32 add + fp32 mul pipes")
    src["su_light_lane_um2"] = dict(what="ESTIMATE: 1.5 x (2 fp32 mul + 3 fp32 add) -- no routed light lane exists")
    src["tselect_lane_um2"] = dict(what="tselect_w16 area / 16")
    return out, src


# sequencer / unit depths (cycles) the as-built RTL has, and the fast-FP set measured by agent a516a664
ADD_LAT = dict(as_built=5, fastfp=3)          # rtl/hdc/ot_fp32_add_rne_pipe (5); rtl/hdc/ot_hdc_fastfp.sv (3)
SFU_DEPTH = dict(as_built=dict(exp=92, rsqrt=61, sigmoid=128, recip=46, softplus=259, div=31),
                 fastfp=dict(exp=49, rsqrt=37, sigmoid=80, recip=28, softplus=259, div=31))
# KV state on the ROM die lives in HBM (user decision 2026-09-26).  STACKS PER DIE (user decision 2026-09-27, "no
# unrealistic assumptions"): 4 HBM3E stacks per die = 8 per two-die package, what a shipping B200/B300-class
# CoWoS-L interposer carries -- not the 5 per die the beachfront rule allows (10 per package has no shipping
# interposer).  The same cap applies to the HBM comparator's dies.  1.0 TB/s per stack (B200: 8 TB/s / 8), 22.5 GB
# per stack (B200: 180 GB / 8), 90% sustained with refresh on.  Non-layer dies carry no stacks (R-U1).
HBM_STACKS_PER_DIE_MAX = 4
ROM_DIE_HBM_STACKS = HBM_STACKS_PER_DIE_MAX
ROM_DIE_HBM_BPS = ROM_DIE_HBM_STACKS * 1.0e12 * 0.90
SERDES_LANES_PER_PACKAGE_2DIE = 84   # always-on 112G lanes per two-die package (rack study: 90 lanes, 6 spare)
PROVISION_FACTOR = 1.2             # provision at 1.2 x the worst case (research agent adae6788, 2026-09-27)
HC_DEPTH_CYC = 126         # hyper-connection projection depth, measured (results/rtl/hdc_v41x_hcp_campaign.json, 4,096 lanes)
HC_MTP_LANES = 5120.0     # HC FP32 lanes per weight lane: keeps the 6-position MTP verify's HC projection off the chain-attacked path
KV_GATHER_S_REQUIRED = 250e-9   # budgeted first-row latency of a data-dependent row gather (device ~100 ns +
                                # controller + PHY + NoC; the report's 100 ns is optimistic)
HBM_LAT_S = 1.0e-6        # ASSUMED first-access latency of a data-dependent HBM gather incl. controller queue
                          # (the report's hbm_gather_s is 100 ns; HBM3E row miss + controller + PHY ~ 0.3-1 us)


# -- 1. the requirement -------------------------------------------------------------------------------------------------
# User decision 2026-09-27: the V4.1 baseline is the best SHIPPABLE option -- packaging option (b) plus a
# light-FEC package link (130 ns hop, band 100-170, the same bandwidth; the packaging agent's lever 1) plus
# overlapped reductions (a collective's bytes stream behind its producer; lever 4).  Plain (b) stays a
# secondary row.
BASELINE = dict(name="b_lightfec_overlap", board_hop_s=130e-9, overlap_collectives=True,
                label="option (b) + light-FEC package link (130 ns) + overlapped reductions")
PLAIN_B = dict(name="b_plain", board_hop_s=None, overlap_collectives=False, label="option (b) as published")


def links_for(base):
    E = _env()
    if not base or base["board_hop_s"] is None:
        return E["links"]
    lk = dict(E["links"])
    lk["rom_board_serdes"] = dict(lk["rom_board_serdes"], hop=base["board_hop_s"])
    return lk


def headline():
    rec = json.loads((ROOT / "results/roofline/critical_path/decode_critical_path.json").read_text())
    o = rec["packaging_options"]["options"][HEADLINE_KEY]
    by = {int(k): v for k, v in o["by_context"].items()}
    return dict(option=o["id"], label=o["label"], packages=o["packages"], hbm_stacks_per_package=o["hbm_stacks_per_package"],
                placement={k: o["placement"][k] for k in ("dies", "group", "per_die_capacity_bytes", "layer_groups",
                                                          "layer_dies", "non_layer_dies", "dies_per_layer")},
                batch1=o["batch1"], batch64=o["batch64"],
                tokens_s_per_user={ctx: by[ctx]["batch1"]["tokens_s_per_user"] for ctx in CONTEXTS},
                tokens_s_per_user_b64={ctx: by[ctx]["batch64"]["tokens_s_per_user"] for ctx in CONTEXTS},
                source="results/roofline/critical_path/decode_critical_path.json packaging_options.options."
                       + HEADLINE_KEY)


# -- 2. workload characterisation -----------------------------------------------------------------------------------------
FP4 = 0.53125        # E2M1 + UE8M0 per 32
FP8 = 1 + 1 / 1024   # E4M3 + one UE8M0 scale per 32x32 weight block (the checkpoint's own layout)
# OFFICIAL PRECISION (user decision 2026-09-27): every weight at its dtype in the pinned release snapshot
# (dba1be0a..., safetensors headers; tools/audit_v41_weight_precision.py): FP8 E4M3 with a UE8M0 scale per
# 32x32 block (attention projections incl. wo_a, the indexer's wq_b, shared experts, Engram wkv, DSpark),
# FP4 E2M1 packed two per byte with a UE8M0 scale per row x 32 (routed experts), BF16 (embedding, lm_head,
# router gate, compressor wkv/wgate, indexer weights_proj/wk, norms, DSpark gate / Markov head), FP32
# (hyper-connection fn/base/scale, attention sink, router bias).
WIN_ROW_B = 528      # window KV row: 512 FP8 + scales (decode_critical_path v41_attention)
CKV_ROW_B = 288      # compressed row: 512 FP4 (E4M3 scale per 16) (ibid.)
IDX_KEY_B = 68       # index key: 128 FP4 + UE8M0 per 32 (ibid.)
ENGRAM_ROW_B = 264   # 256 E4M3 codes + scale + pad (results/rtl/hdc_v41_engram_rom_plan.json, agent a9484ffa)


def shape():
    return D.v41_shape()


def layer_kind(c, L):
    m = c["modes"][L]
    r = c["compress_ratios"][L]
    if not r:
        return "swa" + ("+engram" if L in c["engram_layer_ids"] else "")
    k = m["mode"]
    tag = {"full": "src", "reuse": "reuse", "reindex": "reindex"}[k] + f"_r{r}"
    if L == c["candidate_source_layer_id"]:
        tag += "+cand"
    if L in c["engram_layer_ids"]:
        tag += "+engram"
    return tag


def ops_of_layer(c, L, ctx, pos=None):
    """First-principles op inventory of layer L at context ctx (the decode position is ctx - 1).

    Each op: name, sub (hc/attn/ffn/engram), cls (the resource class), macs, fmt, bytes {rom, kv_sram,
    kv_hbm, idx, engram}, elems (stream element-ops), fn (none/exp/sigmoid/silu/div/rsqrt/softplus/max),
    chain (the longest sequential FP32 accumulation under the golden's orders: add-latency x chain is a
    latency floor), share (die share under tensor group G: 'tp' = 1/G, 'rep' = every die)."""
    pos = ctx - 1 if pos is None else pos
    D_, HC, H, HD, RD = c["hidden_size"], c["hc_mult"], c["num_attention_heads"], c["head_dim"], c["rope_head_dim"]
    QR, OG, OR = c["q_lora_rank"], c["o_groups"], c["o_lora_rank"]
    IH, IHD, TOPK, WIN = c["index_heads"], c["index_head_dim"], c["index_topk"], c["window_tokens"]
    NE, KE, FF = c["num_routed_experts"], c["experts_per_token"], c["moe_intermediate_size"]
    CB, CK = c["candidate_block_size"], c["candidate_topk_blocks"]
    mode, r = c["modes"][L], c["compress_ratios"][L]
    is_src = L in c["kv_source_layer_ids"]
    scans = bool(mode.get("scans_index"))
    n_comp = (pos + 1) // r if r else 0
    n_sel = min(TOPK, n_comp) if r else 0
    cap = mode.get("index_scan_entries_cap") or 0
    n_scan = (min(n_comp, cap) if cap else n_comp) if scans else 0
    T = min(WIN, pos + 1) + n_sel
    X = HC * D_
    ops = []

    def op(name, sub, cls, *, macs=0, fmt="", rom=0, kv_sram=0, kv_hbm=0, idx=0, engram=0, elems=0, fn="none",
           chain=0, share="tp", topk=None):
        ops.append(dict(name=name, sub=sub, cls=cls, macs=macs, fmt=fmt,
                        bytes=dict(rom=rom, kv_sram=kv_sram, kv_hbm=kv_hbm, idx=idx, engram=engram),
                        elems=elems, fn=fn, chain=chain, share=share, topk=topk))

    if L in c["engram_layer_ids"]:
        K_ = 24 * c["engram_head_dim"]
        op("engram.gather", "engram", "engram", engram=24 * ENGRAM_ROW_B, share="rep")
        op("engram.wkv", "engram", "weight", macs=(HC + 1) * D_ * K_, fmt="fp8", rom=(HC + 1) * D_ * K_ * FP8,
           chain=K_ // 32)
        op("engram.knorm", "engram", "su", elems=2 * X, chain=D_ // 8, share="rep")
        op("engram.gate_dots", "engram", "su", elems=3 * X, chain=D_ // 8, share="rep")
        op("engram.gate_fn", "engram", "sfu", elems=4 * 4, fn="sigmoid", share="rep")
        op("engram.add", "engram", "su", elems=X, share="rep")
    for sub in ("attn", "ffn"):
        s = f"{sub}.hc"
        op(f"{s}.sumsq", sub, "su", elems=X, chain=X // 4 // 8, share="rep")
        op(f"{s}.fn", sub, "hc_proj", macs=6 * HC * X, fmt="fp32", rom=6 * HC * X * 4, chain=X // 8, share="rep")
        op(f"{s}.mix", sub, "sfu", elems=6 * HC, fn="sigmoid", share="rep")
        op(f"{s}.sinkhorn", sub, "sinkhorn", elems=2 * c["hc_sinkhorn_iters"] * HC * HC, fn="div", share="rep")
        op(f"{s}.pre", sub, "su", elems=HC * D_, share="rep")
        op(f"{s}.norm", sub, "su", elems=2 * D_, chain=D_ // 64, share="rep")
        op(f"{s}.quant", sub, "su", elems=D_, share="rep")
        op(f"{s}.post", sub, "su", elems=(HC + 1) * X, share="rep")
    # attention
    op("attn.wq_a", "attn", "weight", macs=QR * D_, fmt="fp8", rom=QR * D_ * FP8, chain=D_ // 32)
    op("attn.wkv", "attn", "weight", macs=HD * D_, fmt="fp8", rom=HD * D_ * FP8, chain=D_ // 32)
    if scans:
        op("attn.idx.weights_proj", "attn", "weight", macs=IH * D_, fmt="bf16", rom=IH * D_ * 2, chain=D_)
    op("attn.q_norm", "attn", "su", elems=2 * QR, chain=QR // 64, share="rep")
    op("attn.wq_b", "attn", "weight", macs=H * HD * QR, fmt="fp8", rom=H * HD * QR * FP8, chain=QR // 32)
    op("attn.q_rope", "attn", "su", elems=H * RD, share="tp")
    op("attn.kv_norm_rope_qdq", "attn", "su", elems=4 * HD, chain=HD // 64, share="rep")
    if is_src:
        cw = (2 if r == 2 else 1) * HD
        op("attn.cmp.wkv", "attn", "weight", macs=cw * D_, fmt="bf16", rom=cw * D_ * 2, chain=D_)
        if r == 2:
            op("attn.cmp.pool", "attn", "sfu", elems=4 * HD, fn="exp", share="rep")
        op("attn.cmp.norm_rope_qdq", "attn", "su", elems=5 * HD, chain=HD // 64, share="rep")
        op("attn.cmp.wk", "attn", "weight", macs=IHD * HD, fmt="bf16", rom=IHD * HD * 2, chain=HD, share="rep")
        op("attn.cmp.k_norm_rope_qdq", "attn", "su", elems=4 * IHD, share="rep")
    if scans:
        op("attn.idx.wq_b", "attn", "weight", macs=IH * IHD * QR, fmt="fp8", rom=IH * IHD * QR * FP8,
           chain=QR // 32, share="rep")
        op("attn.idx.q_rope_qdq", "attn", "su", elems=2 * IH * IHD, share="rep")
        op("attn.idx.score", "attn", "indexer", macs=n_scan * IH * IHD, fmt="fp4", idx=n_scan * IDX_KEY_B,
           chain=IHD)
        op("attn.idx.relu_w_headsum", "attn", "su", elems=n_scan * IH, chain=IH // 8)
        op("attn.idx.topk", "attn", "select", elems=n_scan, topk=(n_scan, min(TOPK, n_scan)))
        if L == c["candidate_source_layer_id"]:
            op("attn.cand.blockmax", "attn", "select", elems=n_scan, fn="max")
            op("attn.cand.topk", "attn", "select", elems=-(-n_scan // CB), topk=(-(-n_scan // CB), CK))
    if r:
        op("attn.gather_rows", "attn", "kv", kv_hbm=n_sel * CKV_ROW_B, share="tp")
    op("attn.scores", "attn", "attention", macs=H * T * HD, fmt="bf16xfp8",
       kv_sram=min(WIN, pos + 1) * WIN_ROW_B + n_sel * CKV_ROW_B, chain=HD)
    op("attn.softmax_max", "attn", "su", elems=H * T, fn="max")
    op("attn.softmax_exp", "attn", "sfu", elems=H * T, fn="exp", chain=T // 8)
    op("attn.pv", "attn", "attention", macs=H * T * HD, fmt="bf16", chain=T)
    op("attn.normalize", "attn", "sfu", elems=H * HD + H * RD, fn="div")
    op("attn.wo_a", "attn", "weight", macs=OG * OR * (H // OG) * HD, fmt="bf16xfp8w", rom=OG * OR * (H // OG) * HD * FP8,
       chain=(H // OG) * HD // 2)
    op("attn.z_quant", "attn", "su", elems=OG * OR)
    op("attn.wo_b", "attn", "weight", macs=D_ * OG * OR, fmt="fp8", rom=D_ * OG * OR * FP8, chain=OG * OR // 32)
    # MoE
    op("ffn.router", "ffn", "weight", macs=NE * D_, fmt="bf16", rom=NE * D_ * 2, chain=D_ // 4)
    op("ffn.softplus_sqrt", "ffn", "sfu", elems=NE, fn="softplus")
    op("ffn.top6", "ffn", "select", elems=NE, topk=(NE, KE), share="rep")
    op("ffn.route_weights", "ffn", "sfu", elems=2 * KE, fn="div", share="rep")
    op("ffn.shared_w13", "ffn", "weight", macs=2 * FF * D_, fmt="fp8", rom=2 * FF * D_ * FP8, chain=D_ // 32)
    op("ffn.shared_swiglu", "ffn", "sfu", elems=FF, fn="silu")
    op("ffn.shared_w2", "ffn", "weight", macs=D_ * FF, fmt="fp8", rom=D_ * FF * FP8, chain=FF // 32)
    op("ffn.experts_w13", "ffn", "weight", macs=KE * 2 * FF * D_, fmt="fp4", rom=KE * 2 * FF * D_ * FP4, chain=D_ // 32)
    op("ffn.experts_swiglu", "ffn", "sfu", elems=KE * FF, fn="silu")
    op("ffn.experts_w2", "ffn", "weight", macs=KE * D_ * FF, fmt="fp4", rom=KE * D_ * FF * FP4, chain=FF // 32)
    op("ffn.combine", "ffn", "su", elems=(KE + 1) * D_)
    return ops, dict(layer=L, kind=layer_kind(c, L), T=T, n_comp=n_comp, n_sel=n_sel, n_scan=n_scan)


def head_ops(c):
    D_, HC, V = c["hidden_size"], c["hc_mult"], c["vocab_size"]
    return [dict(name="head.pre_norm", sub="head", cls="su", macs=0, fmt="", bytes=dict(rom=0, kv_sram=0, kv_hbm=0, idx=0, engram=0),
                 elems=HC * D_ + 2 * D_, fn="none", chain=D_ // 64, share="rep", topk=None),
            dict(name="head.lm_head", sub="head", cls="weight", macs=V * D_, fmt="bf16",
                 bytes=dict(rom=V * D_ * 2, kv_sram=0, kv_hbm=0, idx=0, engram=0), elems=0, fn="none",
                 chain=D_ // 32, share="tp", topk=None),
            dict(name="head.argmax", sub="head", cls="select", macs=0, fmt="", bytes=dict(rom=0, kv_sram=0, kv_hbm=0, idx=0, engram=0),
                 elems=V, fn="max", chain=0, share="tp", topk=(V, 1))]


def collectives_of_layer(c, L, G=4):
    """(name, op, payload bytes per user) of layer L under tensor group G (decode_critical_path v41_graph)."""
    D_, HC, HD, QR, IH, TOPK, CK = (c[k] for k in ("hidden_size", "hc_mult", "head_dim", "q_lora_rank", "index_heads",
                                                   "index_topk", "candidate_topk_blocks"))
    r = c["compress_ratios"][L]
    is_src = L in c["kv_source_layer_ids"]
    scans = bool(c["modes"][L].get("scans_index"))
    comp = (2 * HD * 4 if r == 2 else HD * 2) if is_src else 0
    out = [("attn.a_allgather", "all_gather", (QR + HD + IH) * 2 + comp),
           ("attn.rows_allgather", "all_gather", 0),         # rows: bytes counted in the KV traffic
           ("attn.out_allreduce", "all_reduce", D_ * 4),
           ("ffn.router_allgather", "all_gather", c["num_routed_experts"] * 4),
           ("ffn.combine_allreduce", "all_reduce", D_ * 4)]
    if scans:
        out.append(("attn.idx.topk_merge", "all_gather", G * TOPK * 8))
    if L == c["candidate_source_layer_id"]:
        out.append(("attn.cand.merge", "all_gather", G * CK * 8))
    return out


FN_CLASS = {"none": "linear", "max": "linear", "exp": "transcendental", "sigmoid": "transcendental",
            "silu": "transcendental", "softplus": "transcendental", "div": "divide", "rsqrt": "transcendental"}


def token_workload(c, ctx, G=4):
    """Per-token totals by class and per die (the die share of a layer times the layers a die group holds)."""
    layers = []
    tot = dict(macs={}, bytes=dict(rom=0, kv_sram=0, kv_hbm=0, idx=0, engram=0), elems={}, reductions=0,
               chain_max={}, topk=[], collectives=0, collective_bytes=0)
    die = dict(macs=0, rom=0, kv_sram=0, kv_hbm=0, idx=0, elems=0)

    def add(ops, weight=1.0):
        for o in ops:
            if o["macs"]:
                key = o["cls"] + ":" + o["fmt"]
                tot["macs"][key] = tot["macs"].get(key, 0) + o["macs"]
            for k, v in o["bytes"].items():
                tot["bytes"][k] += v
            if o["elems"] and o["cls"] in ("su", "sfu", "sinkhorn"):
                k = FN_CLASS.get(o["fn"], "linear")
                tot["elems"][k] = tot["elems"].get(k, 0) + o["elems"]
            if o["chain"]:
                tot["reductions"] += 1
                if o["chain"] > tot["chain_max"].get(o["cls"], (0,))[0]:
                    tot["chain_max"][o["cls"]] = (o["chain"], o["name"])
            if o["topk"]:
                tot["topk"].append((o["name"], o["topk"]))
            sh = 1.0 if o["share"] == "rep" else 1.0 / G
            die["macs"] += o["macs"] * sh * weight
            die["rom"] += o["bytes"]["rom"] * sh * weight
            die["kv_sram"] += o["bytes"]["kv_sram"] * weight          # rows all-gathered: every die reads all
            die["kv_hbm"] += o["bytes"]["kv_hbm"] * sh * weight
            die["idx"] += o["bytes"]["idx"] * sh * weight
            if o["cls"] in ("su", "sfu"):
                die["elems"] += o["elems"] * sh * weight
    for L in range(c["num_layers"]):
        ops, meta = ops_of_layer(c, L, ctx)
        add(ops)
        cl = collectives_of_layer(c, L, G)
        tot["collectives"] += len(cl)
        tot["collective_bytes"] += sum(p for _, _, p in cl)
        meta.update(macs=sum(o["macs"] for o in ops), rom_bytes=sum(o["bytes"]["rom"] for o in ops),
                    idx_bytes=sum(o["bytes"]["idx"] for o in ops), elems=sum(o["elems"] for o in ops
                                                                           if o["cls"] in ("su", "sfu")),
                    collectives=len(cl))
        layers.append(meta)
    add(head_ops(c))
    tot["macs_total"] = sum(tot["macs"].values())
    tot["chain_max"] = {k: dict(terms=v[0], op=v[1]) for k, v in tot["chain_max"].items()}
    tot["topk"] = sorted({(n.split(".", 1)[-1] if n.startswith("attn") else n, t) for n, t in tot["topk"]},
                         key=lambda x: -x[1][0])[:6]
    return tot, layers


def die_share(c, ctx, G=4, layers_per_group=40 / 28):
    """Per-die per-token work of the busiest layer group: layers_per_group layers at 1/G of the split ops."""
    tot, layers = token_workload(c, ctx, G)
    return tot


# -- 3/4. the spec and its pricing on the report's DAG -----------------------------------------------------------------
@dataclass
class Spec:
    """Per-die block widths and depths.  Rates are per core clock."""
    name: str
    weight_macs: float          # weight-matvec MAC lanes (one MAC per ROM weight per cycle, x lane_mult for MTP)
    bf16_macs: float            # of which BF16 / FP32-weight MACs/cycle (wo_a, compressor, router; the ME)
    rom_bytes: float            # weight ROM read bytes/cycle
    att_macs: float             # dynamic-operand MACs/cycle (q.k, p.v)
    kv_bytes: float             # KV row staging SRAM read bytes/cycle
    idx_macs: float             # indexer FP4 x FP4 MACs/cycle
    idx_bytes: float            # index-key read bytes/cycle (SRAM)
    su_lanes: int               # stream-unit elements/cycle, linear functions
    sfu_lanes: int              # stream-unit elements/cycle with exp / sigmoid / silu / divide
    sel_lanes: int              # threshold select scores/cycle
    sel_tail: str = "two_pass"  # two_pass: 2 x beats + LAT0 after the last score (ot_hdc_tselect)
                                # filter: streaming threshold filter + tselect over the survivors (proposed)
    hc_macs: float = 24.0       # hyper-connection projection FP32 MAC lanes
    chains: str = "none"        # "none": the DAG (no sequential-accumulation floor); "golden": the golden's orders
                                # at shipped shapes; "split<c>": every accumulation re-specified in chunks of <= c
    add_lat: int = 5            # FP32 add latency in a dependent chain
    sfu: str = "as_built"       # SFU depth set (SFU_DEPTH)
    chaining: bool = True       # vector chaining between producer and consumer units (DAG); False = drain
    seq_gap: int = 5            # sequencer cycles per issued instruction (decode_critical_path K seq_gap)
    lane_mult: int = 1          # positions per weight read (MTP verify / batching); ME lanes = weight_macs
    kv_gather_s: float = 100e-9 # first-row latency of the index-selected compressed-row gather from HBM


def dag_spec(mach, clock):
    """The report's assumptions: one MAC rate per die for weights, attention and indexer; HBM KV bandwidth."""
    mac = mach.mac_rate_per_die / clock
    kvb = mach.kv_bw_per_die / clock
    return Spec("dag", weight_macs=mac, bf16_macs=mac, rom_bytes=float("inf"), att_macs=mac, kv_bytes=kvb, idx_macs=mac,
                idx_bytes=kvb, su_lanes=mach.su_width, sfu_lanes=mach.su_width, sel_lanes=D.TS["lanes"],
                sel_tail="two_pass", hc_macs=float("inf"), chains="none", add_lat=5, sfu="as_built", chaining=True)


def as_built_spec():
    """The V4.1 RTL core (rtl/hdc/v41) as it is: ME 4 groups x 16 BF16 lanes (also runs attention and the
    indexer through head groups), QE 16 block-dot lanes (512 FP8/FP4 MACs/cycle, 16 x 33 B/cycle), stream unit
    8 lanes (lane 0 alone has rsqrt/sqrt/softplus), XU insertion select 1 element/cycle, HE 3 lanes x 8 chunks
    of FP32, 5-cycle FP32 adds, drain barriers between units (chase only stream->stream)."""
    return Spec("as_built", weight_macs=512.0, bf16_macs=64.0, rom_bytes=16 * 33.0, att_macs=64.0, kv_bytes=16 * 4 * 2.0,
                idx_macs=64.0, idx_bytes=16 * 4 * 2.0, su_lanes=8, sfu_lanes=8, sel_lanes=1, sel_tail="insertion",
                hc_macs=24.0, chains="golden", add_lat=5, sfu="as_built", chaining=False, seq_gap=6)


SFU_NODE = {  # DAG node suffix -> function class for the SFU-lane budget
    "exp": "exp", "sink": "exp", "softplus_sqrt": "softplus", "swiglu": "silu", "shared_swiglu": "silu",
    "pre_post": "sigmoid", "normalize": "div", "weights": "div", "gate": "sigmoid", "pool": "exp"}


def node_chain(name, nd, c, ctx, spec):
    """The sequential accumulation length a node carries under spec.chains (terms)."""
    if spec.chains == "none":
        return 0
    D_, HC, HD, QR = c["hidden_size"], c["hc_mult"], c["head_dim"], c["q_lora_rank"]
    L = nd["layer"]
    T = None
    if L is not None and 0 <= L < c["num_layers"]:
        r = c["compress_ratios"][L]
        n_sel = min(c["index_topk"], ctx // r) if r else 0
        T = min(c["window_tokens"], ctx) + n_sel
    tail = ".".join(name.split(".")[-2:])
    golden = {
        "hc.sumsq": HC * D_ // 4 // 8, "hc.fn": HC * D_ // 8,
        "norm.sumsq": D_ // 64, "q_norm.sumsq": QR // 64, "kv_norm.sumsq": HD // 64,
        "attn.a_proj": D_ // 32, "attn.wq_b": QR // 32, "attn.wo_a": (c["num_attention_heads"] // c["o_groups"]) * HD // 2,
        "attn.wo_b": c["o_groups"] * c["o_lora_rank"] // 32, "attn.scores": HD, "attn.pv": T or 0,
        "attn.den": (T or 0) // 8, "idx.score": c["index_head_dim"], "ffn.router": D_ // 4,
        "ffn.shared_gu": D_ // 32, "ffn.experts_gu": D_ // 32, "ffn.down": c["moe_intermediate_size"] // 32,
        "head.lm_head": D_ // 32, "eng.hh": D_ // 8, "eng.dot": D_ // 8,
    }
    key = tail if tail in golden else None
    if key is None:
        for k in golden:
            if name.endswith(k):
                key = k
                break
    if key is None:
        if name.endswith(".wkv") and name.startswith("E"):
            return 24 * c["engram_head_dim"] // 32 if spec.chains == "golden" else _split(24 * c["engram_head_dim"] // 32, spec)
        return 0
    n = golden[key]
    return n if spec.chains == "golden" else _split(n, spec)


def _split(n, spec):
    """Re-specified order: chunks of <= c terms, chunk sums by a pairwise tree: chain = c + log2(n / c)."""
    cmax = int(spec.chains[5:])
    if n <= cmax:
        return n
    return cmax + math.ceil(math.log2(n / cmax))


def die_fraction(name, c, G):
    """The die's share of a matvec node's full-matrix bytes/MACs (decode_critical_path splits)."""
    if name.endswith("hc.fn") or name.endswith("cmp.wk"):
        return 1.0
    if name.endswith("wq_b"):
        H, HD, QR, IH, IHD = (c[k] for k in ("num_attention_heads", "head_dim", "q_lora_rank", "index_heads",
                                             "index_head_dim"))
        L = int(name.split(".")[0][1:])
        scans = bool(c["modes"][L].get("scans_index"))
        full = H * HD * QR + (IH * IHD * QR if scans else 0)
        return (H * HD * QR / G + (IH * IHD * QR if scans else 0)) / full
    return 1.0 / G


def _precision_fix(name, c, nd):
    """The report DAG's weight bytes against the checkpoint's own dtypes: lm_head is BF16 (the DAG prices
    FP8), the router gate is BF16 (DAG: FP32), the ratio-2 compressor's wkv|wgate is BF16 (DAG: FP32).
    wo_a is FP8 in the checkpoint as the DAG has it (the release dequantises it to BF16 for its einsum, which
    is exact: this engine takes the FP8 codes and scales and multiplies exactly).
    Self-detecting: the factor is checkpoint bytes / the DAG's bytes, so it is 1 once decode_critical_path
    carries the checkpoint dtypes itself (fixed at source on the packaging branch, dee2f0a1)."""
    D_, HD = c["hidden_size"], c["head_dim"]
    full = nd["sweep"]["bytes"]
    if name.endswith("head.lm_head"):
        return c["vocab_size"] * D_ * 2 / full
    if name.endswith("ffn.router"):
        return c["num_routed_experts"] * D_ * 2 / full
    if name.endswith("attn.a_proj"):
        L = nd["layer"]
        if L in c["kv_source_layer_ids"] and c["compress_ratios"][L] == 2:
            fp32 = (c["q_lora_rank"] + HD) * D_ + c["index_heads"] * D_ * 2 + 2 * HD * D_ * 4
            if abs(full - fp32) < 0.5:                  # the DAG still prices the compressor at FP32
                return (full - 2 * HD * D_ * 2) / full
    return 1.0


def distinct_experts(tokens, E, k):
    """Expected distinct experts over `tokens` independent top-k draws of E (uniform routing: the router trace
    is synthetic, configs/models/candidates/deepseek-v4.1-flash.json router_trace_status)."""
    return E * (1 - (1 - k / E) ** max(1, tokens))


PLACEMENT_REC = ROOT / "results/arch/v41_die_placement.json"
EXPERT_NODES = ("ffn.experts_gu", "ffn.down")


def _placement_map():
    E = _env()
    if "_placement" not in E:
        P = json.loads(PLACEMENT_REC.read_text())
        frac, start = {}, {}
        for st in P["stages"]:
            for l in st["layers"]:
                frac.setdefault(l["layer"], []).append((st["stage"], l["fraction"]))
                start.setdefault(l["layer"], st["stage"])
        E["_placement"] = (frac, start, len(P["stages"]))
    return E["_placement"]


def stage_occupancy(g, units=None):
    """Busy (issue) seconds per pass on ONE die of each pipeline stage, by unit: the layer stages of the physical
    placement (results/arch/v41_die_placement.json, packed by ROM bytes) and the head group.  A layer's routed-expert
    matvecs split over the stages holding its bytes in the placement's fractions; every other node of the layer
    (attention, indexer scan, KV, norms, router, shared expert) runs on the stage where the layer starts, unless the
    node carries exec_stage (a helper group's share of a split index scan, tools/v41_stage_rebalance.py).  units: a
    {work class: unit} map (pooled units); None keeps each node's own work class."""
    frac, start, _n = _placement_map()
    occ = {}
    for name, nd in g.nodes.items():
        if nd["kind"] in ("collective", "hop"):
            continue
        L = nd.get("layer")
        w = nd.get("_work")
        u = (units or {}).get(w[0], w[0]) if w else "other"
        if nd.get("exec_stage") is not None:              # work moved off its layer's stage (v41_stage_rebalance)
            parts = [(nd["exec_stage"], 1.0)]
        elif L is None or L not in start:
            parts = [("head", 1.0)]
        elif name.endswith(EXPERT_NODES):
            tot = sum(f for _, f in frac[L])
            parts = [(s, f / tot) for s, f in frac[L]]
        else:
            parts = [(start[L], 1.0)]
        for s, f in parts:
            row = occ.setdefault(s, {})
            row[u] = row.get(u, 0.0) + nd["issue"] * f
    return occ


def stage_bound(g, slots, units=None, per_unit=False):
    """The occupancy bound of the busiest stage: slots microbatch passes per period through its die.  per_unit=False
    serialises every unit of the die (the budget's bound); True lets the units overlap (the busiest unit binds).
    Returns (seconds, busiest stage, its occupancy over the stage mean)."""
    occ = stage_occupancy(g, units)
    tot = {s: (max(v.values()) if per_unit else sum(v.values())) for s, v in occ.items()}
    busiest = max(tot, key=tot.get)
    layer = [v for s, v in tot.items() if s != "head"]
    mean = sum(layer) / len(layer) if layer else 0.0
    return tot[busiest] * slots, busiest, (tot[busiest] / mean if mean else 1.0)


def fill_machine(batch):
    """The pipeline-fill batch policy: S layer-group stages; b < S users ride one per stage, b >= S users
    share each stage in microbatches of b / S (every weight read serves the whole microbatch)."""
    m1 = dag_machine(1)
    S = m1.stages
    return replace(m1, batch=batch, microbatch=max(1.0, batch / S), slots=float(min(batch, S)))


CHAIN_LEVERS = ("osm", "fuse", "chain_all", "short_stages", "att_local")
ATT_NODES = ("attn.a_proj", "attn.wq_b", "attn.wo_a", "attn.wo_b", "attn.cmp.wk", "attn.scores", "attn.pv",
             "attn.idx.score", "attn.idx.topk_local", "attn.cand.topk_local")
ATT_COLL = ("attn.a_allgather", "attn.rows_allgather", "attn.out_allreduce", "attn.idx.topk_merge",
            "attn.cand.merge")


def price(spec, ctx=200000, batch=1, positions=1, *, links=None, keep=False, expert_overlap=0.0, hbm=None,
          fill=False, base=None, levers=(), exposure=None):
    """Re-price the report's DAG node by node from `spec`; returns T (critical path), the occupancy bound,
    tokens/s per user and the per-category / per-resource critical-path breakdown.

    positions > 1 prices an MTP verify pass of that many positions per user: MACs and stream elements scale
    with users x positions; weight ROM bytes are read once per pass per distinct weight (dense: once;
    routed experts: the union of the positions' experts, `expert_overlap` the fraction of the union's excess
    over k removed by correlated routing); KV rows and index keys are read once per user (the positions share
    them); spec.lane_mult multiplies every engine's lanes (the m-way core: m MAC lanes per weight lane,
    m-wide attention / indexer / stream / select), never the ROM read width.

    hbm = dict(bw_Bps, lat_s) prices the HBM comparator: every weight byte (and the index keys and KV rows)
    streams from the die's stacks at bw_Bps, and the routed experts' fetch pays lat_s after the router
    (their addresses exist only then); dense weights are prefetched across dependency points.

    levers (the dependency-chain attack, docs/ARCH_SPEC_V41.md 12):
      fuse         reductions off the critical path: an RMSNorm's rstd scales the NEXT matvec's outputs (the
                   sum of squares and rsqrt run beside the sweep) and the attention softmax is online (exp
                   streams behind the scores with a running-max rescale) -- decode_critical_path Params.fuse;
                   a change of the arithmetic contract (the golden must adopt it);
      chain_all    tile/row-granular chaining for every unit: matvecs, attention/indexer scans and the local
                   selects start on their producer's first tile instead of its last element;
      short_stages the measured short stages beyond the spec's fast FP: stream-unit base depth 21 (not 29),
                   reducer tail 25 (not 32), rsqrt path 58 (not 90), sqrt(softplus) 161 (not 259);
      att_local    attention and its projections on the two dies of ONE package (tensor group 2 for the
                   attention sublayer, UCIe collectives), MoE still striped over the four-die group.
    exposure: None (overlap as assumed), True (the committed measured terms, results/arch/
    v41_collective_exposure.json) or a terms dict: every streaming collective / stage hop is re-priced from its
    producer's last output with the RTL stage bench's exposed tail (gate C7 / O2, tools/collective_exposure.py)."""
    E = _env()
    clock = E["clock"]
    m = fill_machine(batch) if fill else dag_machine(batch)
    users = m.microbatch
    if positions > 1:
        m = replace(m, microbatch=users * positions)
    levers = set(levers)
    params = replace(E["p"], fuse=True) if "fuse" in levers else E["p"]
    b = D.Built(m, params, clock, D.v41_graph, E["c"], ctx)
    base = BASELINE if base is None else base
    fab = D.ArrayFabric(links or links_for(base), 2, "mesh", 4)
    if "att_local" in levers:
        for name, nd in b.g.nodes.items():
            if nd["kind"] == "collective" and name.split(".", 1)[-1] in ATT_COLL:
                nd["span"] = 2
    D.price_communication(b.g, fab, m.microbatch, clock)
    if base.get("overlap_collectives"):
        for nd in b.g.nodes.values():            # a collective's bytes stream behind its producer
            if nd["kind"] == "collective":
                nd["stream"] = True
    c, G, mb = E["c"], 4, m.microbatch
    NE, KE, FF, D_ = c["num_routed_experts"], c["experts_per_token"], c["moe_intermediate_size"], c["hidden_size"]
    lm = max(1, spec.lane_mult)
    tokens = max(1, round(mb))
    U = distinct_experts(tokens, NE, KE)
    U = U - expert_overlap * (U - KE)
    cyc = 1.0 / clock
    sd = SFU_DEPTH[spec.sfu]
    for name, nd in b.g.nodes.items():
        k = nd["kind"]
        if spec.name == "dag" and spec.chains == "none":
            nd["resource"] = _dag_resource(name, nd)
            continue
        if k == "matvec":
            sw = nd["sweep"]
            f = die_fraction(name, c, G)
            if "att_local" in levers and name.split(".", 1)[-1] in ATT_NODES:
                f *= 2
            hc = name.endswith("hc.fn")
            if hc:          # measured: the hcp block's depth (a6236a4f campaign, 4,096 lanes as 8 x 512: 126 cycles)
                nd["depth"] = max(nd["depth"], HC_DEPTH_CYC * cyc)
            wide = name.endswith(("wo_a", "cmp.wk", "router", "lm_head"))
            lanes = spec.hc_macs if hc else (spec.bf16_macs if wide else spec.weight_macs)
            macs = sw["macs"] * f                                   # the DAG's sweep MACs already carry mb
            full_b = sw["bytes"] * f * _precision_fix(name, c, nd)
            routed_b = 0.0
            if name.endswith("ffn.experts_gu"):
                routed_b = full_b
            elif name.endswith("ffn.down"):
                routed_b = KE * D_ * FF * FP4 * f
            dense_b = full_b - routed_b
            # dense weights: one read per ceil(mb / m) passes of the weight lanes; routed: each distinct
            # expert's weights once, its positions sharing the read only through the lane multiplier
            share = tokens * KE / U                                 # positions per distinct expert (mean)
            if hbm:                                                 # the die buffers a tile and reuses it
                reads_dense, reads_routed = 1.0, U / KE
            else:                                                   # a weight lane re-reads per m positions
                reads_dense = math.ceil(mb / lm)
                reads_routed = (U / KE) * max(1.0, share / lm)
            by = dense_b * reads_dense + routed_b * reads_routed
            if hbm:
                t_rom = by / (hbm["bw_Bps"] / clock)
                if name.endswith("ffn.experts_gu"):
                    nd["depth"] += hbm["lat_s"]
            else:
                t_rom = by / spec.rom_bytes if not hc else 0.0
            w_per_b = macs / max(1.0, mb) / max(1e-9, full_b)       # weights per byte of this op
            t_lanes = by * w_per_b / lanes if not hc else macs / (lanes * lm)
            t_m = macs / (lanes * lm)
            t = max(t_rom, t_lanes, t_m)
            issue = t * cyc
            nd["resource"] = ("hc" if hc else ("rom" if t_rom > max(t_lanes, t_m) else "weight"), t)
            nd["_work"] = ("hc", macs) if hc else ("bf16" if wide else "weight", max(macs / lm, by * w_per_b))
        elif k == "kvscan":
            if name.endswith("idx.score"):
                n_keys = int(nd["desc"].split()[2]) if nd["desc"].startswith("index scores") else 0
                if "att_local" in levers:
                    n_keys *= 2
                by = n_keys * IDX_KEY_B * users                      # keys read once per user per pass
                macs = n_keys * c["index_heads"] * c["index_head_dim"] * mb
                ib = min(spec.idx_bytes, (hbm["bw_Bps"] if hbm else ROM_DIE_HBM_BPS) / clock)
                t_b, t_m = by / ib, macs / (spec.idx_macs * lm)
                nd["resource"] = ("idx_mem" if t_b > t_m else "idx", max(t_b, t_m))
                nd["_work"] = ("idx", macs / lm)
            else:
                L = nd["layer"]
                r = c["compress_ratios"][L]
                n_sel = min(c["index_topk"], ctx // r) if r else 0
                R = min(c["window_tokens"], ctx) + n_sel
                hpd = math.ceil(c["num_attention_heads"] / (2 if "att_local" in levers else G))
                macs = hpd * R * c["head_dim"] * mb
                by = (min(c["window_tokens"], ctx) * WIN_ROW_B + n_sel * CKV_ROW_B) * users \
                    if name.endswith("scores") else 0
                kb = min(spec.kv_bytes, hbm["bw_Bps"] / clock) if hbm else spec.kv_bytes
                t_b, t_m = by / kb, macs / (spec.att_macs * lm)
                nd["resource"] = ("kv_sram" if t_b > t_m else "att", max(t_b, t_m))
                nd["_work"] = ("att", macs / lm)
            issue = nd["resource"][1] * cyc
        elif k in ("vector", "reduce"):
            n_el = round(nd["issue"] * clock * m.su_width / max(1e-9, mb))   # the DAG priced n x mb / su_width
            fn = SFU_NODE.get(name.split(".")[-1])
            lanes = (spec.sfu_lanes if fn else spec.su_lanes) * lm
            issue_c = math.ceil(n_el * mb / lanes)
            issue = issue_c * cyc
            nd["resource"] = ("sfu" if fn else "su", issue_c)
            nd["_work"] = ("sfu" if fn else "su", n_el * mb / lm)
            if spec.sfu != "as_built" and fn in ("exp", "sigmoid", "silu"):
                key = "sigmoid" if fn in ("sigmoid", "silu") else "exp"
                nd["depth"] = max(0.0, nd["depth"] - (SFU_DEPTH["as_built"][key] - sd[key]) * cyc)
        elif k == "op" and name.endswith(".gather"):
            nd["depth"] = spec.kv_gather_s
            nd["resource"] = None
            continue
        elif k == "select":
            issue, depth, rname, rwork = _select_price(name, nd, spec, c, ctx, mb / lm, clock,
                                                       ways=2 if "att_local" in levers else 4)
            nd["depth"] = depth
            nd["resource"] = (rname, rwork)
            nd["_work"] = ("sel", rwork * spec.sel_lanes)
        else:
            nd["resource"] = None
            continue
        ch = node_chain(name, nd, c, ctx, spec)
        if ch:
            floor = ch * spec.add_lat * cyc
            if floor > issue:
                nd["resource"] = ("chain", ch * spec.add_lat)
                issue = floor
        nd["issue"] = issue
        if k == "matvec":
            nd["issue_cat"] = "weight_sweep"
    if spec.seq_gap != 5:
        for nd in b.g.nodes.values():
            if nd["ctrl"] > 0:
                nd["ctrl"] += (spec.seq_gap - 5) * cyc
    if "osm" in levers and "fuse" not in levers:
        # online softmax only: exp streams behind the scores (running-max rescale), the norms keep their order
        for name, nd in b.g.nodes.items():
            if name.endswith("attn.exp"):
                pre = name[:-len("exp")]
                nd["deps"] = [pre + "scores"]
                nd["stream"] = True
    if "chain_all" in levers:
        for name, nd in b.g.nodes.items():
            if nd["kind"] in ("matvec", "kvscan") or (nd["kind"] == "select" and name.endswith("topk_local")):
                nd["stream"] = True
    if "short_stages" in levers:
        for name, nd in b.g.nodes.items():
            if nd["kind"] in ("vector", "reduce"):
                cut = 8 + (7 if nd["kind"] == "reduce" else 0)
                if name.endswith(".rsqrt"):
                    cut += 32 - 8
                if name.endswith("softplus_sqrt"):
                    cut += 98
                nd["depth"] = max(0.0, nd["depth"] - cut * cyc)
    if exposure and base.get("overlap_collectives"):     # after the producers' issue is priced (their window)
        D.expose_collectives(b.g, D.load_exposure_terms() if exposure is True else exposure)
    fin = b.g.solve(spec.chaining)
    T = fin[b.sink]
    path = b.g.path(b.sink)
    cats = dict.fromkeys(D.CATS, 0.0)
    for n in path:
        for k_, v in b.g.contrib[n].items():
            cats[k_] = cats.get(k_, 0.0) + v
    by_res = {}
    for n in path:
        nd = b.g.nodes[n]
        rr = nd.get("resource")
        if rr:
            part = b.g.contrib[n].get(nd["issue_cat"], 0.0) - (nd["depth"] if nd["depth_cat"] == nd["issue_cat"] else 0.0)
            nd["_issue_on_path"] = max(0.0, part)
            by_res[rr[0]] = by_res.get(rr[0], 0.0) + max(0.0, part)
    occ = sum(nd["issue"] for nd in b.g.nodes.values() if nd["kind"] not in ("collective", "hop"))
    # an autoregressive user has one token in flight: the occupancy bound counts the users actually in flight
    # (the stage MEAN: the specification sizing; the operating points re-bound on the busiest stage, stage_bound, in
    # tools/arch_utilization_v41.solve)
    occ_bound = occ * min(m.slots, batch) / max(1, m.stages)
    period = max(T, occ_bound)
    out = dict(T_s=T, occupancy_bound_s=occ_bound, period_s=period, tokens_s_per_user=1 / period,
               aggregate_tokens_s=batch / period, binding="critical_path" if T >= occ_bound else "occupancy",
               breakdown_us={k: v * 1e6 for k, v in cats.items()},
               critical_issue_us_by_resource={k: v * 1e6 for k, v in sorted(by_res.items(), key=lambda kv: -kv[1])},
               users_per_stage=users, stages=m.stages, distinct_experts=U)
    if keep:
        out["_built"] = b
    return out


def _dag_resource(name, nd):
    k = nd["kind"]
    if k == "matvec":
        return ("weight", nd["issue"])
    if k == "kvscan":
        return ("idx" if name.endswith("idx.score") else "att", nd["issue"])
    if k in ("vector", "reduce"):
        return ("sfu" if SFU_NODE.get(name.split(".")[-1]) else "su", nd["issue"])
    return None


def _select_price(name, nd, spec, c, ctx, mb, clock, ways=4):
    """(issue s, depth s, resource, work) of a select node under the spec's select unit."""
    cyc = 1.0 / clock
    TOPK, CK, CB = c["index_topk"], c["candidate_topk_blocks"], c["candidate_block_size"]
    if name.endswith("top6") or name.endswith("top6_order"):
        return nd["issue"], nd["depth"], "sel", 0
    L = nd["layer"]
    if L is None or L < 0 or L >= c["num_layers"]:
        return nd["issue"], nd["depth"], "sel", 0
    r = c["compress_ratios"][L]
    mode = c["modes"][L]
    n_comp = ctx // r if r else 0
    cap = mode.get("index_scan_entries_cap") or 0
    n_scan = min(n_comp, cap) if cap else n_comp
    per_die = math.ceil(n_scan / ways)
    W = max(1, spec.sel_lanes)
    lat0 = D.TS["lat0"]
    if ".cand." in name:
        k = CK
        n = math.ceil(per_die / CB) if name.endswith("topk_local") else 4 * CK
    else:
        k = TOPK
        n = per_die if name.endswith("topk_local") else 4 * TOPK
    k = min(k, n)
    if name.endswith("final") or name.endswith("merge"):
        n = 4 * k
    beats = math.ceil(n / W)
    if spec.sel_tail == "insertion":                    # ot_hdc_select: 1 element/cycle, k+2 (+k ascending)
        issue_c = n * mb
        tail = 2 * k + 2 + k
    elif spec.sel_tail == "filter":
        # streaming exact filter (running k-th threshold lower bound) keeps ~ k (1 + ln(n/k)) survivors,
        # then a two-pass tselect over the survivors
        surv = min(n, math.ceil(k * (1 + math.log(max(1.0, n / k)))))
        issue_c = beats * mb
        tail = 2 * math.ceil(surv / W) + lat0
    else:
        issue_c = beats * mb
        tail = 2 * beats + lat0
    if name.endswith("final"):
        tail += beats                                    # ingest of the concatenated local selections
        issue_c = 0
    return issue_c * cyc, tail * cyc, "sel", tail


_ENV = {}


def _env():
    if not _ENV:
        p = D.Params()
        tech = json.loads(D.TECH.read_text())
        links = D.link_consts(tech)
        clock, rows = D.routed_clock()
        p = replace(p, clock_hz=clock)
        points, designs = D.v41_study_rows()
        _ENV.update(p=p, links=links, clock=clock, clock_rows=rows, points=points, designs=designs, c=D.v41_shape(),
                    tech=tech)
    return _ENV


def dag_machine(batch=1):
    """The report's option-(b) machine at `batch`.  The analytical points exist at batch 1, 64 and 4,096; an
    intermediate batch keeps batch 1's slots (users in flight) with microbatch max(1, batch / slots)."""
    E = _env()
    try:
        return D.v41_machine("array", 4, batch, E["points"], E["designs"], E["p"], E["clock"], placement="packed")
    except KeyError:
        m1 = D.v41_machine("array", 4, 1, E["points"], E["designs"], E["p"], E["clock"], placement="packed")
        return replace(m1, batch=batch, microbatch=max(1.0, batch / m1.slots))


# -- 4. the budget: fixed part, issue budget, area-optimal widths ----------------------------------------------------
RESOURCES = ("weight", "bf16", "att", "idx", "su", "sfu", "hc")  # the select is sized by its ingest (select_lanes)
AREA_KEY = dict(weight="fp8_mac_um2", bf16="mac_bf16_um2", att="mac_bf16_um2", idx="fp8_mac_um2",
                su="su_light_lane_um2", sfu="su_lane_um2", sel="tselect_lane_um2", hc="fp32_mac_um2")
WIDTH_FIELD = dict(weight="weight_macs", bf16="bf16_macs", att="att_macs", idx="idx_macs", su="su_lanes",
                   sfu="sfu_lanes", sel="sel_lanes", hc="hc_macs")


def fixed_part(spec, ctx, positions=1, batch=1):
    """T with every issue time zero (unit depths, control, links, chain floors kept)."""
    big = replace(spec, name=spec.name + "_inf", weight_macs=1e15, bf16_macs=1e15, rom_bytes=1e15, att_macs=1e15, kv_bytes=1e15,
                  idx_macs=1e15, idx_bytes=1e15, su_lanes=10 ** 9, sfu_lanes=10 ** 9, sel_lanes=10 ** 9,
                  hc_macs=1e15)
    return price(big, ctx, positions=positions, batch=batch)


def critical_work(spec, ctx, positions=1, batch=1):
    """Per resource: the raw work (MACs, elements, select beats x lanes) of the critical-path nodes whose
    issue time is exposed on the path; issue = work / width, so this is the W of the allocation rule."""
    r = price(spec, ctx, positions=positions, batch=batch, keep=True)
    b = r["_built"]
    work = dict.fromkeys(RESOURCES, 0.0)
    for n in b.g.path(b.sink):
        nd = b.g.nodes[n]
        w = nd.get("_work")
        if not w or w[0] not in work or nd.get("_issue_on_path", 0.0) <= 0:
            continue
        rr = nd.get("resource")
        if rr and rr[0] == "chain":
            continue
        work[w[0]] += w[1] * min(1.0, nd["_issue_on_path"] / max(1e-15, nd["issue"]))
    return work, r


def round_width(r, w):
    if r in ("su", "sfu", "sel", "hc"):
        return 2 ** max(0, math.ceil(math.log2(max(1.0, w))))
    q = 256 if r in ("weight", "idx") else 64
    w = max(w, q)
    return q * math.ceil(w / q)


def select_lanes_for(spec, c):
    """The select's scores/cycle: at least the indexer's keys/cycle (the select ingests the scorer's stream
    without back-pressure), a power of two, at least 16 (the width that routes, ot_hdc_tselect_w16), at most 64."""
    keys = spec.idx_macs / (c["index_heads"] * c["index_head_dim"])
    return int(min(64, max(16, 2 ** math.ceil(math.log2(max(1.0, keys))))))


def _with_widths(spec, widths):
    """Apply widths and the bandwidths they imply: ROM bytes = weight MACs x FP8 bytes (one weight per MAC at
    batch 1), index-key bytes = keys/cycle x 68 B, KV staging = one 528-B row per 16 heads x 512 dims of MACs,
    select lanes from the indexer rate."""
    sp = replace(spec, **{WIDTH_FIELD[k]: v for k, v in widths.items()})
    c = _env()["c"]
    return replace(sp, rom_bytes=sp.weight_macs * FP8 + sp.bf16_macs * 2,
                   idx_bytes=min(sp.idx_macs / (c["index_heads"] * c["index_head_dim"]) * IDX_KEY_B,
                                 ROM_DIE_HBM_BPS / _env()["clock"]),
                   kv_bytes=max(64.0, sp.att_macs / (16 * c["head_dim"]) * WIN_ROW_B),
                   sel_lanes=select_lanes_for(sp, c))


def shrink(spec, ctx, target_s, areas, max_iter=40, positions=1, batch=1):
    """Halve the width whose halving costs the least time per area saved while the target still holds."""
    for _ in range(max_iter):
        best = None
        for k in RESOURCES:
            w = getattr(spec, WIDTH_FIELD[k])
            if w <= (16 if k in ("su", "sfu") else 256):
                continue
            cand = _with_widths(spec, {k: round_width(k, w / 2)})
            t = price(cand, ctx, positions=positions, batch=batch)["period_s"]
            if t <= target_s:
                saved = areas[AREA_KEY[k]] * (w - getattr(cand, WIDTH_FIELD[k]))
                if best is None or saved > best[0]:
                    best = (saved, cand)
        if best is None:
            return spec
        spec = best[1]
    return spec


def derive(target_s, ctx, base, areas, rounds=4, positions=1, batch=1):
    """Area-optimal widths meeting target_s at ctx, starting from `base` (chain policy, depths, select tail)."""
    fx = fixed_part(base, ctx, positions, batch)
    budget = target_s - fx["period_s"]
    spec = base
    hist = []
    if budget <= 0:
        return None, dict(fixed=fx, budget_s=budget, feasible=False, history=hist)
    clock = _env()["clock"]
    for it in range(rounds):
        work, r = critical_work(spec, ctx, positions, batch)
        a = {k: areas[AREA_KEY[k]] for k in RESOURCES}
        roots = {k: math.sqrt(a[k] * work[k]) for k in RESOURCES if work[k] > 0}
        s = sum(roots.values())
        B = budget * clock
        widths = {}
        for k in RESOURCES:
            if k in roots:
                t = B * roots[k] / s
                widths[k] = round_width(k, work[k] / t)
            else:
                widths[k] = getattr(spec, WIDTH_FIELD[k])
        spec = _with_widths(spec, widths)
        chk = price(spec, ctx, positions=positions, batch=batch)
        hist.append(dict(round=it, widths=widths, T_us=chk["period_s"] * 1e6, work_cycles={k: round(v) for k, v in work.items()}))
    # greedy repair: double the width with the best time saved per area until the target holds
    guard = 0
    while price(spec, ctx, positions=positions, batch=batch)["period_s"] > target_s and guard < 24:
        guard += 1
        best = None
        t0 = price(spec, ctx, positions=positions, batch=batch)["period_s"]
        for k in RESOURCES:
            cand = _with_widths(spec, {k: getattr(spec, WIDTH_FIELD[k]) * 2})
            dt = t0 - price(cand, ctx, positions=positions, batch=batch)["period_s"]
            da = areas[AREA_KEY[k]] * getattr(spec, WIDTH_FIELD[k])
            if dt > 0 and (best is None or dt / da > best[0]):
                best = (dt / da, cand, k)
        if best is None:
            break
        spec = best[1]
        hist.append(dict(round=f"repair{guard}", doubled=best[2], T_us=price(spec, ctx, positions=positions, batch=batch)["period_s"] * 1e6))
    spec = shrink(spec, ctx, target_s, areas, positions=positions, batch=batch)
    hist.append(dict(round="shrink", widths={k: getattr(spec, WIDTH_FIELD[k]) for k in RESOURCES},
                     T_us=price(spec, ctx, positions=positions, batch=batch)["period_s"] * 1e6))
    return spec, dict(fixed=fx, budget_s=budget, feasible=price(spec, ctx, positions=positions, batch=batch)["period_s"] <= target_s * 1.0005, history=hist)


def spec_area_mm2(spec, areas):
    rows = {}
    for k in WIDTH_FIELD:
        w = getattr(spec, WIDTH_FIELD[k])
        rows[k] = w * areas[AREA_KEY[k]] / 1e6 if math.isfinite(w) else float("inf")
    rows["total"] = sum(v for v in rows.values())
    return rows


# -- 6. MTP ------------------------------------------------------------------------------------------------------------------
# User decision 2026-09-28: MTP headlines at the V4.1-Flash-SPECIFIC tau we measured -- DSpark (the checkpoint's
# built-in drafter) at gamma 5, greedy, replayed exactly on the model's own continuations (on-policy), 36 prompts x 9
# workloads, 982 speculative cycles: tau 3.649 pooled, 95% CI 3.50-3.84 (results/speculative/
# v41_flash_dspark_onpolicy_greedy.json headline, tools/v41_dspark_onpolicy/).  ONE value, read from that record
# (rounded to the published 3.65); every V4.1 tool takes it from here.  The published V4.1-Flash figures bound the
# sensitivity band 3.5-4.1 (results/speculative/acceptance_tau.json: InferenceX 3.51 / 4.07, vLLM PR #57432 GSM8K
# greedy 3.82-3.89).  The earlier 5.0 (LMSYS/SGLang, DeepSeek-V4-PRO, workload unstated) is withdrawn as the headline.
V41_TAU_REC = ROOT / "results/speculative/v41_flash_dspark_onpolicy_greedy.json"
_TAU_H = json.loads(V41_TAU_REC.read_text())["headline"]
TAU_HEADLINE = round(_TAU_H["tau"], 2)
TAU_CI95 = tuple(round(x, 2) for x in _TAU_H["ci95_stratified_prompt_bootstrap"])
TAU_BAND = (3.5, 4.1)                       # published V4.1-Flash band (acceptance_tau.json deepseek_v4_family)
TAU_HEADLINE_LABEL = "V4.1-Flash on-policy greedy (measured)"
TAU_HEADLINE_SOURCE = ("results/speculative/v41_flash_dspark_onpolicy_greedy.json headline.tau: DeepSeek-V4.1-Flash "
                       "DSpark gamma 5, greedy, on-policy exact replay, 36 prompts x 9 workloads, 95%% CI %.2f-%.2f"
                       % TAU_CI95)


def tau_points():
    """tau (accepted tokens per verify cycle incl. the bonus token): the measured V4.1-Flash headline, the published
    V4.1-Flash band's ends, and the design-faithful remodel's literature points (V4-Pro) as further sensitivities."""
    fa = json.loads(SPEC_FAITHFUL.read_text()) if SPEC_FAITHFUL.exists() else None
    out = []
    if fa:
        for t in fa["tau"]["v41"]:
            out.append(dict(tau=t["tau"], gamma=t["gamma"], label=t["label"], grade=t["grade"], source=t["source"],
                            model=t.get("model"), workload=t.get("workload")))
    out = [p for p in out if p["label"] != "LMSYS SGLang ~5"]      # V4-Pro, withdrawn as the headline
    out.insert(0, dict(tau=TAU_HEADLINE, gamma=5, label=TAU_HEADLINE_LABEL, grade="measured",
                       model="DeepSeek-V4.1-Flash", workload="36 prompts x 9 workloads (acceptance_tau prompt set)",
                       source=TAU_HEADLINE_SOURCE))
    for t, lab in zip(TAU_BAND, ("low", "high")):
        out.append(dict(tau=t, gamma=5, label=f"V4.1-Flash published band, {lab} ({t:g})", grade="published",
                        model="DeepSeek-V4.1-Flash",
                        source="results/speculative/acceptance_tau.json: InferenceX 3.51 / 4.07, vLLM PR #57432 "
                               "3.82-3.89"))
    return out


def draft_cost_s(spec, ctx, gamma, c, hbm=None):
    """DSpark draft chain (agent adbe13f5's requirements): 3 MTP stages, each a full block over a block of gamma
    rows (window-only attention, 128-expert top-3 MoE), then gamma dependent (lm_head row, Markov bias, argmax,
    group all-gather) steps.  A stage is priced as the DAG's layer-0 (sliding-window) span at a microbatch of
    gamma under this spec; a Markov step as the vocabulary-split lm_head row + the rank-256 bias (2 x 129,280 x
    256 MACs) + argmax + one 219-ns group collective."""
    r = price(spec, ctx, positions=gamma, keep=True, hbm=hbm)
    b = r["_built"]
    fin = b.g.fin
    l0 = [n for n in b.g.nodes if b.g.nodes[n]["layer"] == 0]
    stage = max(fin[n] for n in l0) - min(fin[n] - b.g.nodes[n]["issue"] - b.g.nodes[n]["depth"] for n in l0)
    clock = _env()["clock"]
    V = c["vocab_size"]
    lanes = max(1.0, spec.weight_macs * max(1, spec.lane_mult))
    markov = 2 * V * 256 / 4 / lanes / clock
    lm = V * c["hidden_size"] / 4 / lanes / clock
    if hbm:
        lm = max(lm, V * c["hidden_size"] * FP8 / 4 / hbm["bw_Bps"])
    argmax = V / 4 / max(1, spec.su_lanes) / clock
    step = lm + markov + argmax + 219e-9 + 60 / clock
    # engine work of one draft on one head die, by unit class (the issue time the draft occupies each unit; the
    # span above also waits on collectives and dependencies): 3 stages of the layer-0 nodes, then gamma steps of
    # lm_head row + Markov bias on the weight lanes and argmax on the stream unit
    busy = {}
    for n in l0:
        w = b.g.nodes[n].get("_work")
        if w:
            busy[w[0]] = busy.get(w[0], 0.0) + 3 * b.g.nodes[n]["issue"]
    busy["weight"] = busy.get("weight", 0.0) + gamma * (lm + markov)
    busy["su"] = busy.get("su", 0.0) + gamma * argmax
    return dict(stage_s=stage, stages=3, markov_step_s=step, total_s=3 * stage + gamma * step, busy_s=busy,
                note="stage = layer-0 span of the DAG at microbatch gamma; step = lm_head + Markov + argmax + 219 ns")


def mtp_rows(spec, ctx, c, lane_mult, hbm=None, overlap=0.0):
    rows = []
    ar = price(spec, ctx, hbm=hbm)
    for gamma in (5, 7):
        s2 = replace(spec, lane_mult=lane_mult)
        v = price(s2, ctx, positions=gamma + 1, hbm=hbm, expert_overlap=overlap)
        d = draft_cost_s(s2, ctx, gamma, c, hbm=hbm)
        cyc = v["period_s"] + d["total_s"]
        for t in tau_points():
            tau = min(t["tau"], gamma + 1)
            rows.append(dict(gamma=gamma, positions=gamma + 1, tau=tau, tau_label=t["label"], tau_grade=t["grade"],
                             lane_mult=lane_mult, verify_us=v["period_s"] * 1e6, draft_us=d["total_s"] * 1e6,
                             cycle_us=cyc * 1e6, tokens_s_per_user=tau / cyc,
                             ar_tokens_s_per_user=ar["tokens_s_per_user"], speedup=tau / cyc * ar["period_s"],
                             distinct_experts=v["distinct_experts"]))
    return rows


OP_CLASS_ORDER = ("dense_gemv", "routed_experts", "hc_projection", "attention", "indexer", "stream", "fixed")


def op_class(name, nd):
    k = nd["kind"]
    if k == "matvec":
        if name.endswith("hc.fn"):
            return "hc_projection"
        if name.endswith(("ffn.experts_gu", "ffn.down")):
            return "routed_experts"
        return "dense_gemv"
    if k == "kvscan":
        return "indexer" if name.endswith("idx.score") else "attention"
    if k == "select":
        return "indexer" if (".idx." in name or ".cand." in name) else "stream"
    if k in ("vector", "reduce"):
        tail = name.split(".", 1)[-1]
        if tail.startswith("attn.") and tail.split(".")[-1] in ("max", "exp", "den", "sink", "normalize"):
            return "attention"
        if ".idx." in name:
            return "indexer"
        return "stream"
    return None


def per_operator(spec, ctx, B, hbm=None, overlap=0.0):
    """Per operator class: total busy time of its units per token (sum of issue over every node of the class,
    all layers, one die), the verify/plain ratio at B positions, the binding resource, and the critical-path
    time of the class (issue exposed on the path) plus the fixed part (depths, control, links) once per pass."""
    r1 = price(spec, ctx, keep=True, hbm=hbm)
    rB = price(spec, ctx, positions=B, keep=True, hbm=hbm, expert_overlap=overlap)
    rows = {}
    for tag, r in (("plain", r1), ("verify", rB)):
        b = r["_built"]
        path = set(b.g.path(b.sink))
        for name, nd in b.g.nodes.items():
            cl = op_class(name, nd)
            if cl is None:
                continue
            row = rows.setdefault(cl, dict(plain_busy_us=0.0, verify_busy_us=0.0, plain_path_us=0.0,
                                           verify_path_us=0.0, resources={}))
            row[f"{tag}_busy_us"] += nd["issue"] * 1e6
            if name in path:
                row[f"{tag}_path_us"] += nd.get("_issue_on_path", 0.0) * 1e6
            if tag == "verify" and nd.get("resource"):
                rr = nd["resource"][0]
                row["resources"][rr] = row["resources"].get(rr, 0.0) + nd["issue"]
    for cl, row in rows.items():
        row["ratio_busy"] = row["verify_busy_us"] / row["plain_busy_us"] if row["plain_busy_us"] else None
        row["binding_resource"] = max(row["resources"], key=row["resources"].get) if row["resources"] else None
        del row["resources"]
    fixed1 = r1["T_s"] - sum(v["plain_path_us"] for v in rows.values()) * 1e-6
    fixedB = rB["T_s"] - sum(v["verify_path_us"] for v in rows.values()) * 1e-6
    rows["fixed"] = dict(plain_path_us=fixed1 * 1e6, verify_path_us=fixedB * 1e6, ratio_busy=fixedB / fixed1,
                         binding_resource="latency (unit depths, control, collectives, hops)")
    return dict(B=B, plain_us=r1["T_s"] * 1e6, verify_us=rB["T_s"] * 1e6, ratio=rB["T_s"] / r1["T_s"],
                distinct_experts=rB["distinct_experts"],
                classes={k: rows[k] for k in OP_CLASS_ORDER if k in rows})


def mtp_design(req, ctx, B, areas, cap_mm2, c, rom_read_cap):
    """The MTP design point: the m-way core (every engine m times as wide, m MAC lanes per weight lane, the ROM
    read width unchanged) for m = 1, 2, 3, 4, 6; the chosen m is the largest whose block area fits cap_mm2.
    rom_read_cap is the ROM macro array's sweep rate (bytes/cycle): the weight lanes must not exceed it."""
    rows = []
    for m in (1, 2, 3, 4, 6):
        sp = replace(req, lane_mult=m)
        area = spec_area_mm2(req, areas)["total"] * m - spec_area_mm2(req, areas)["sel"] * (m - 1)
        v = price(sp, ctx, positions=B)["T_s"]
        d = draft_cost_s(sp, ctx, B - 1, c)["total_s"]
        rows.append(dict(m=m, area_mm2=area, fits=area <= cap_mm2, verify_us=v * 1e6, draft_us=d * 1e6,
                         rom_read_bytes_per_cycle=req.rom_bytes, rom_read_ok=req.rom_bytes <= rom_read_cap,
                         tokens_s_per_user={p["label"]: min(p["tau"], B) / (v + d) for p in tau_points()}))
    fit = [r for r in rows if r["fits"]]
    key = TAU_HEADLINE_LABEL
    design = rows[0]["m"]
    for a, b in zip(rows, rows[1:]):                    # the knee: stop when the next m buys < 15%
        if b["fits"] and b["tokens_s_per_user"][key] >= 1.15 * a["tokens_s_per_user"][key]:
            design = b["m"]
        else:
            break
    return dict(B=B, rows=rows, largest_fitting_m=max(r["m"] for r in fit) if fit else None, design_m=design,
                design_rule="the knee: the largest m whose step from m-1 still buys >= 15% at the headline tau, within the "
                            "area cap", cap_mm2=cap_mm2, rom_read_cap_bytes_per_cycle=rom_read_cap)


# -- 7. HBM comparator ---------------------------------------------------------------------------------------------------
def hbm_comparator(c, tech=None):
    """Iso total logic area: the ROM array's 188 x compute_mm2 of logic re-spent on logic-only dies with HBM3E.

    Per die: the analytical design's interconnect and overhead are kept, HBM PHYs fill the beachfront
    (technology.json hbm3e: 60% of the perimeter at 12 mm per stack), the rest is logic.  Weights, KV and index
    keys share the die's stacks; the sustained efficiency requirement is 90% with refresh on (agent a8c77c67)."""
    E = _env()
    tech = tech or E["tech"]
    h = tech["hbm"]["hbm3e"]
    per_stack_bw = h["stack_bandwidth_bytes_s"]["value"]
    cap = h["stack_capacity_bytes"]["value"]
    beach = h["stack_beachfront_mm"]["value"]
    util = h["max_beachfront_utilization"]["value"]
    phy = h["phy_area_mm2_per_stack"]["value"]
    d = E["designs"][D.ARRAY_DESIGN]["area_split_per_device"]
    die_mm2 = d["total_mm2"]
    edge = math.sqrt(die_mm2)
    stacks = min(int(4 * edge * util // beach), HBM_STACKS_PER_DIE_MAX)   # beachfront allows 5; shipping packages 4
    logic_per_die = die_mm2 - d["interconnect_mm2"] - d["overhead_mm2"] - stacks * phy
    rom_logic_total = 188 * d["compute_mm2"]
    dies = math.ceil(rom_logic_total / logic_per_die)
    eff = 0.90
    return dict(die_mm2=die_mm2, hbm_stacks_per_die=stacks, stack_bw_Bps=per_stack_bw, stack_capacity_B=cap,
                logic_mm2_per_die=logic_per_die, rom_array_logic_mm2=rom_logic_total, rom_compute_mm2_per_die=d["compute_mm2"],
                dies=dies, tensor_groups=dies // 4, capacity_B=dies * stacks * cap,
                weights_B=json.loads(D.V41_CONFIG.read_text())["checkpoint_bytes"],
                sustained_efficiency_required=eff, die_bw_Bps=stacks * per_stack_bw * eff,
                bw_Bps=stacks * per_stack_bw * eff, lat_s=HBM_LAT_S,
                note=("the DAG's 28 layer groups are kept for the token path (the comparator has ~25 groups of 4: "
                      "3 fewer package hops, < 1 us per token); every die carries the ROM die's block spec (its "
                      "extra logic area is headroom, used by the MTP lane multiplier)"),
                source="configs/hardware/technology.json hbm.hbm3e; area split of " + D.ARRAY_DESIGN)


def hbm_requirements(c, hb, lat_s=HBM_LAT_S):
    """Buffers and controller requirements of the HBM die: the dense-weight prefetch window covering the
    first-access latency at the die's sustained bandwidth, the routed-expert fetch after the router."""
    bw = hb["die_bw_Bps"]
    KE, FF, D_ = c["experts_per_token"], c["moe_intermediate_size"], c["hidden_size"]
    expert_b = 3 * FF * D_ * FP4
    per_die = KE * expert_b / 4
    return dict(prefetch_window_bytes=bw * lat_s,
                prefetch_window_note="latency x die bandwidth: the dense stream is issued this far ahead of its "
                                     "consumer across every dependency point whose addresses are static (all dense "
                                     "weights, the window KV rows)",
                expert_bytes=expert_b, routed_bytes_per_die_per_layer=per_die,
                routed_fetch_us_per_layer=(lat_s + per_die / bw) * 1e6,
                routed_note="the expert ids exist only after the router's top-6: the fetch is exposed (first-access "
                            "latency) and its bytes are on the critical path; 40 layers x this per token",
                queue_beats_per_pseudo_channel=64,
                queue_note="results/rtl/hdc_hbm_campaign.json refresh_study (commit be30614a, HBM comparator "
                           "branch; RTL, reduced vehicle, refresh on): refresh-aware REFpb (tRFCpb 200 ns) reaches "
                           "0.965-0.993 of the refresh-free rate with 64-beat queues; all-bank refresh needs >= 512 "
                           "beats (0.964-0.979) and falls to 0.852 at 64; >= 8 pseudo-channels per stream keep the "
                           "90% floor at the 350-ns tRFCpb band; a refreshing channel must not stall words that do "
                           "not touch it")


# -- 5. requirements and the gap ---------------------------------------------------------------------------------------------
def engram_requirement(c, slack_s, clock):
    """Engram gather: 48 rows x 264 B per token, prefetchable from token start (the hash reads token ids only).
    The consuming die's ingest must deliver them within the slack at batch 1 (agent a9484ffa: >= 3.57 us for
    layer 1 on the array); the port is sized to finish in a quarter of it."""
    rows = 2 * c["engram_hash_columns"]
    by = rows * ENGRAM_ROW_B
    cycles = slack_s / 4 * clock
    return dict(rows_per_token=rows, bytes_per_token=by, slack_us=slack_s * 1e6,
                required_bytes_per_cycle=by / cycles, port_bits=256,
                port_cycles=math.ceil(by / 32), as_built_port_bytes_per_cycle=rows * ENGRAM_ROW_B,
                note="one 264-B row per column bank per token: a per-bank slice at the ROM bank and a 256-bit "
                     "beat stream to the consumer (13 KB in ~400 cycles) replaces the 48 x 2,112-bit flat port")


def select_requirements(c, spec, clock):
    """Index top-512 at the three contexts, per die: ingest (scores/cycle = the indexer's keys/cycle), tail
    after the last score for the two-pass tselect and for the streaming filter."""
    rows = {}
    keys_per_cycle = spec.idx_macs / (c["index_heads"] * c["index_head_dim"])
    for ctx in CONTEXTS:
        per = {}
        for L in (2, 20, 24):
            r = c["compress_ratios"][L]
            cap = c["modes"][L].get("index_scan_entries_cap") or 0
            n = ctx // r
            n = min(n, cap) if cap else n
            per_die = math.ceil(n / 4)
            k = c["index_topk"]
            W = spec.sel_lanes
            two = 2 * math.ceil(per_die / W) + D.TS["lat0"]
            surv = min(per_die, math.ceil(k * (1 + math.log(max(1, per_die / k)))))
            filt = 2 * math.ceil(surv / W) + D.TS["lat0"]
            per[f"L{L}"] = dict(scores_per_die=per_die, two_pass_tail_cycles=two, filter_tail_cycles=filt,
                                filter_survivors=surv, scan_cycles=per_die / max(1e-9, keys_per_cycle))
        rows[str(ctx)] = per
    CB = c["candidate_block_size"]
    return dict(ingest_scores_per_cycle=keys_per_cycle, lanes=spec.sel_lanes, by_context=rows,
                candidate=dict(score_lanes=spec.sel_lanes, block_lanes=max(1, spec.sel_lanes // CB), k=c["candidate_topk_blocks"],
                               note="the layer-20 candidate mask is consumed only by the reindex layers (24-36), "
                                    ">= 4 layers later: its latency budget is ~4 layer times, so its width follows "
                                    "the ingest rate (P = keys/cycle, blocks/cycle = P/8), not a 64 x 64 array"))


def required_base():
    """The non-width requirements every derived spec carries: re-specified accumulation orders (chunks of <= 8
    terms, then a pairwise tree), the 3-cycle fast FP32 add and the rebalanced SFU depths (rtl/hdc/
    ot_hdc_fastfp.sv, agent a516a664), producer->consumer vector chaining across units, the streaming-filter
    select, a 768-lane (24 outputs x 32 chunks) hyper-connection projection."""
    return replace(as_built_spec(), name="required", chains="split8", add_lat=ADD_LAT["fastfp"], sfu="fastfp",
                   chaining=True, seq_gap=5, sel_tail="filter", sel_lanes=16, hc_macs=24 * 32,
                   kv_gather_s=KV_GATHER_S_REQUIRED)


def block_table(req, built, c, areas, clock, sel, eng):
    """Requirement vs as-built per block (per die), with the ratio and the area the requirement costs."""
    rows = [
        ("weight engine (FP8/FP4 block-dot)", "MACs/cycle", req.weight_macs, built.weight_macs,
         "QE: 16 block-dot lanes x 32"),
        ("BF16/FP32 weight engine (ME)", "MACs/cycle", req.bf16_macs, built.bf16_macs, "ME: 4 groups x 16 lanes"),
        ("weight ROM read", "bytes/cycle", req.rom_bytes, built.rom_bytes,
         "QE word 16 x 33 B; ROM macro sweep 2.96 TB/s/mm2 x 289 mm2 = 830 KB/cycle available"),
        ("attention engine (q.k, p.v)", "MACs/cycle", req.att_macs, built.att_macs, "ME head groups"),
        ("KV row staging SRAM", "bytes/cycle", req.kv_bytes, built.kv_bytes, "KV SRAM 16 x 4 B x 2 ports"),
        ("indexer engine (FP4 x FP4)", "MACs/cycle", req.idx_macs, built.idx_macs, "ME head groups"),
        ("index-key read", "bytes/cycle", req.idx_bytes, built.idx_bytes, "KV SRAM"),
        ("stream unit, linear lanes", "elements/cycle", req.su_lanes, built.su_lanes, "8 lanes"),
        ("stream unit, SFU lanes (exp/sigmoid/silu/div)", "elements/cycle", req.sfu_lanes, built.sfu_lanes,
         "8 lanes (rsqrt/sqrt/softplus/gate lane 0 only)"),
        ("index top-512 select", "scores/cycle", req.sel_lanes, 1, "XU insertion select, 1 element/cycle"),
        ("hyper-connection projection", "FP32 MACs/cycle", req.hc_macs, built.hc_macs, "HE: 3 lanes x 8 chunks"),
        ("accumulation chain (longest)", "terms", _split(2560, req), 2560, "golden HC_SPLIT = 8: 2,560-term chains"),
        ("FP32 add latency", "cycles", req.add_lat, built.add_lat, "ot_fp32_add_rne_pipe 5 -> ot_hdc_fastfp 3"),
        ("exp / sigmoid depth", "cycles", f"{SFU_DEPTH['fastfp']['exp']} / {SFU_DEPTH['fastfp']['sigmoid']}",
         f"{SFU_DEPTH['as_built']['exp']} / {SFU_DEPTH['as_built']['sigmoid']}", "stream pads exp/rsqrt (e8a585e5)"),
        ("producer -> consumer", "", "vector chaining", "drain barriers", "wait masks drain the unit"),
        ("Engram gather ingest", "bytes/cycle", round(eng["required_bytes_per_cycle"], 1),
         eng["as_built_port_bytes_per_cycle"], "48 x 2,112-bit flat ports, 16,559 IO pins"),
    ]
    out = []
    for blk, unit, rq, ab, basis in rows:
        ratio = rq / ab if isinstance(rq, (int, float)) and isinstance(ab, (int, float)) and ab else None
        out.append(dict(block=blk, unit=unit, required=rq, as_built=ab, ratio=ratio, as_built_basis=basis,
                        meets=(ratio is not None and ratio <= 1.0) if blk not in ("FP32 add latency",
                                                                                  "accumulation chain (longest)") else
                        (isinstance(rq, (int, float)) and rq >= ab)))
    return out


def replay_summary():
    p = ROOT / "results/arch/v41_replay.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    keep = {k: d[k] for k in d if k in ("three_layer", "attribution", "validation", "estimated_ops",
                                        "token_totals", "summary")}
    return keep or dict(present=True)


# -- 8. batch and energy: one model with the speculation analysis --------------------------------------------------------
TAU_DEFAULT = TAU_HEADLINE
BATCH_SWEEP = (1, 2, 4, 8, 16, 28, 32, 64, 128, 256, 512, 1024)


def _v(x):
    return x["value"] if isinstance(x, dict) else x


def energy_terms(tech):
    e = tech["energy"]
    op = {k: v["value"] for k, v in e["mac_energy_j_per_op"].items()}
    return dict(mac_op=op, rom=e["rom_read_j_per_byte"]["value"], deliver=e["operand_delivery_j_per_byte"]["value"],
                sram=e["sram_read_j_per_byte"]["value"], hbm=e["hbm_j_per_byte"]["value"],
                clock=tech["power"]["clock_energy_j_per_mm2_per_cycle"]["value"],
                link_pj_per_bit=dict(ucie=_v(e["link_j_per_bit"]["ucie_advanced"]) * 1e12,
                                     board=_v(e["link_j_per_bit"]["board_serdes_112g"]) * 1e12),
                source="configs/hardware/technology.json energy.* (MAC energies and link_j_per_bit validated "
                       "2026-09-27, results/arch/power_assumptions.json) and power.clock_energy_j_per_mm2_per_cycle")


def energy_per_token(spec, ctx, users, positions=1, hbm=None, gated=False, rate_tokens_s=None, areas=None):
    """Joules per emitted position (token) of the whole array: MACs at the report's per-format op energy (2 ops
    per MAC), weight bytes at ROM read + operand delivery (ROM array) or HBM (comparator) with each weight read
    once per microbatch pass (routed experts: the union over users x positions), KV rows and index keys at HBM
    energy once per user per pass (positions share them), stream elements at ~3 FP32 ops, collectives at the
    link energy, and the clock of every die's block area over the time the token takes on the array
    (ungated: every die clocks every cycle; gated: only the dies in the token's stage)."""
    E = _env()
    c, clock = E["c"], E["clock"]
    et = energy_terms(E["tech"])
    tot, _ = token_workload(c, ctx)
    tokens = max(1.0, users * positions)
    NE, KE, FF, D_ = c["num_routed_experts"], c["experts_per_token"], c["moe_intermediate_size"], c["hidden_size"]
    U = distinct_experts(round(tokens), NE, KE)
    routed_b = c["num_layers"] * KE * 3 * FF * D_ * FP4
    dense_b = tot["bytes"]["rom"] - routed_b
    w_bytes = dense_b / tokens + routed_b * (U / KE) / tokens
    # routed experts are FP4 weights x FP8 activations: the W4A8 op (technology.json mac_energy_j_per_op.w4a8);
    # the indexer is FP4 x FP4 (fp4); wo_a's FP8 weights meet BF16 activations on the BF16 engine (bf16)
    fmt_op = {"fp8": "fp8", "fp4": "fp4", "bf16": "bf16", "fp32": "fp32", "bf16xfp8": "bf16", "bf16xfp8w": "bf16"}
    fmt_of = lambda k: "w4a8" if k == "weight:fp4" else fmt_op.get(k.split(":")[1], "bf16")
    mac_j = sum(v * 2 * et["mac_op"][fmt_of(k)] for k, v in tot["macs"].items())
    w_j = w_bytes * (et["hbm"] if hbm else (et["rom"] + et["deliver"]))
    kv_j = (tot["bytes"]["kv_hbm"] + tot["bytes"]["idx"]) / positions * et["hbm"] + tot["bytes"]["kv_sram"] * et["sram"]
    el = sum(tot["elems"].values())
    su_j = el * 3 * et["mac_op"]["fp32"]
    link_j = tot["collective_bytes"] * 8 * 1e-12 * (et["link_pj_per_bit"]["board"] + et["link_pj_per_bit"]["ucie"]) * 4
    areas = areas or unit_areas()[0]
    die_mm2 = spec_area_mm2(replace(spec, lane_mult=1), areas)["total"] * max(1, spec.lane_mult)
    dies = hbm["dies"] if hbm else 188
    rate = rate_tokens_s or 1.0
    stage_frac = 4 / dies if gated else 1.0
    clk_j = et["clock"] * die_mm2 * clock * dies * stage_frac / rate
    parts = dict(mac=mac_j, weights=w_j, kv_index=kv_j, stream=su_j, links=link_j, clock=clk_j)
    return dict(total_j=sum(parts.values()), parts_j=parts, distinct_experts=U, weight_bytes_per_token=w_bytes)


def batch_model(req, hb, ctx, mtp_m, tau=TAU_DEFAULT, gamma=5, batches=BATCH_SWEEP, areas=None):
    """Per-user rate, array throughput and energy per token at each batch for the ROM array and the HBM
    comparator, without and with MTP -- the same price() as the speculation analysis: users x positions
    share weight reads, routed experts cost their union, KV and index keys are per user."""
    E = _env()
    c = E["c"]
    hbm_kw = dict(bw_Bps=hb["bw_Bps"], lat_s=hb["lat_s"], dies=hb["dies"])
    out = {}
    for mach, kw in (("rom", None), ("hbm", hbm_kw)):
        rows = []
        for bt in batches:
            m = fill_machine(bt)
            users = m.microbatch
            ar = price(req, ctx, batch=bt, hbm=kw, fill=True)
            sp = replace(req, lane_mult=mtp_m)
            v = price(sp, ctx, batch=bt, positions=gamma + 1, hbm=kw, fill=True)
            d = draft_cost_s(sp, ctx, gamma, c, hbm=kw)["total_s"]
            cyc = v["period_s"] + d
            rate_mtp = tau / cyc
            e_ar = energy_per_token(req, ctx, users, 1, hbm=kw, rate_tokens_s=ar["aggregate_tokens_s"], areas=areas)
            e_ar_g = energy_per_token(req, ctx, users, 1, hbm=kw, gated=True, rate_tokens_s=ar["aggregate_tokens_s"],
                                      areas=areas)
            e_v = energy_per_token(sp, ctx, users, gamma + 1, hbm=kw, rate_tokens_s=rate_mtp * bt, areas=areas)
            # a verify pass spends B positions' work per tau emitted tokens; the draft adds ~3/40 of a token's
            # layer work per draft row
            e_mtp = (e_v["total_j"] - e_v["parts_j"]["clock"]) * (gamma + 1) / tau * (1 + 3 / 40) + e_v["parts_j"]["clock"]
            rows.append(dict(batch=bt, fits_capacity=bt <= users_held(ctx, mach),
                             users_per_stage=users, ar_tokens_s_per_user=ar["tokens_s_per_user"],
                             ar_aggregate_tokens_s=ar["aggregate_tokens_s"], ar_binding=ar["binding"],
                             ar_energy_j_per_token=e_ar["total_j"], ar_energy_j_per_token_gated=e_ar_g["total_j"],
                             ar_energy_parts_j=e_ar["parts_j"], distinct_experts_ar=ar["distinct_experts"],
                             mtp_tokens_s_per_user=rate_mtp, mtp_aggregate_tokens_s=rate_mtp * bt,
                             mtp_energy_j_per_token=e_mtp, distinct_experts_verify=v["distinct_experts"],
                             verify_us=v["period_s"] * 1e6, draft_us=d * 1e6, mtp_binding=v["binding"]))
        out[mach] = rows
    return dict(ctx=ctx, tau=tau, gamma=gamma, mtp_lane_mult=mtp_m, rows=out)


def hbm_capacity_efficiency(tech=None):
    """technology.json efficiencies.hbm_capacity: the fraction of physical HBM left for checkpoint and KV after the
    runtime workspace, allocator and safety reserve (the Qwen3 budget applies the same entry)."""
    e = (tech or _env()["tech"])["efficiencies"]["hbm_capacity"]
    return e["value"] if isinstance(e, dict) else e


def capacity_limit(c, hb, ctx):
    """Users whose KV + index state fits one die's HBM (the busiest die: the layer-20 group), both machines, after
    the capacity reserve (technology.json efficiencies.hbm_capacity) on the usable stack bytes."""
    r20 = 1
    rows = ctx // r20
    per_user_die = (rows * CKV_ROW_B + rows * IDX_KEY_B) / 4 + c["window_tokens"] * WIN_ROW_B * 2
    eff = hbm_capacity_efficiency()
    raw_rom = ROM_DIE_HBM_STACKS * hb["stack_capacity_B"]
    raw_hbm = hb["hbm_stacks_per_die"] * hb["stack_capacity_B"] - hb["weights_B"] / hb["dies"]
    rom_cap = eff * raw_rom
    hbm_cap = eff * hb["hbm_stacks_per_die"] * hb["stack_capacity_B"] - hb["weights_B"] / hb["dies"]
    return dict(per_user_bytes_busiest_die=per_user_die, rom_users=int(rom_cap // per_user_die),
                hbm_users=int(hbm_cap // per_user_die), capacity_efficiency=eff,
                capacity_efficiency_source="configs/hardware/technology.json efficiencies.hbm_capacity",
                rom_users_without_reserve=int(raw_rom // per_user_die),
                hbm_users_without_reserve=int(raw_hbm // per_user_die),
                note="layer-20 group: 1 compressed row (288 B) + 1 index key (68 B) per position, split over the "
                     "group's 4 dies, plus 2 window rings; ROM layer die: 4 HBM3E stacks for KV; HBM die: its stacks less "
                     "its weight share; usable bytes = capacity efficiency x physical (the reserve)")


def users_held(ctx, machine="rom"):
    """Users whose KV + index state the machine holds at ctx after the capacity reserve (capacity_limit)."""
    E = _env()
    key = ("_users_held", ctx, machine)
    if key not in E:
        cap = capacity_limit(E["c"], hbm_comparator(E["c"]), ctx)
        E[key] = cap["rom_users" if machine == "rom" else "hbm_users"]
    return E[key]


def point_batch(tag, batch, ctx, machine="rom"):
    """The batch an operating point actually runs: a SATURATED point ('sat*') runs min(its nominal batch, the users
    the machine holds at ctx) -- a user whose KV does not fit cannot be in flight; every other point runs as named."""
    return min(batch, users_held(ctx, machine)) if str(tag).startswith("sat") else batch


def kv_state_requirements(c, req, clock):
    """Per-user KV state in the ROM die's HBM (user decision 2026-09-26): what one die streams per token for the
    index scan and the row gathers, the stack count that bandwidth needs at each context, and the capacity."""
    out = {}
    per_stack = 1.0e12 * 0.90
    for ctx in CONTEXTS:
        rows = {}
        for L in (2, 20, 24):
            r = c["compress_ratios"][L]
            cap = c["modes"][L].get("index_scan_entries_cap") or 0
            n = ctx // r
            n = min(n, cap) if cap else n
            keys_die = math.ceil(n / 4)
            scan_b = keys_die * IDX_KEY_B
            t_scan = keys_die / (req.idx_macs / (c["index_heads"] * c["index_head_dim"]))   # cycles at spec rate
            bw = scan_b / (t_scan / clock) if t_scan else 0.0
            rows[f"L{L}"] = dict(keys_per_die=keys_die, scan_bytes_per_die=scan_b, scan_cycles=t_scan,
                                 stream_Bps=bw, stacks_at_90pct=bw / per_stack,
                                 gather_bytes_per_die=min(c["index_topk"], n) * CKV_ROW_B / 4)
        out[str(ctx)] = rows
    return dict(stacks_per_die=ROM_DIE_HBM_STACKS, sustained_Bps_per_die=ROM_DIE_HBM_BPS, by_context=out,
                key_precision=("index keys stored as the model's FP4 (E2M1) codes + one UE8M0 scale per 32 = 68 B "
                               "per key: the golden QDQs every key to FP4 before use (qdq_fp4_e8m0), so this is "
                               "lossless and 3.8x fewer bytes than BF16"),
                kv_gather_latency_s=KV_GATHER_S_REQUIRED,
                prefetch=("window rows and reuse-layer selections have static addresses: prefetched one layer "
                          "ahead; index-source selections gather after the top-512 (exposed first-row latency); "
                          "the key scan streams sequential 68-B keys in 4 KB bursts"),
                controller=("refresh-aware per-bank refresh (tRFCpb 200 ns), >= 64-beat queues per pseudo-channel "
                            "(256 under all-bank refresh), no head-of-line blocking across channels, "
                            "with the scan's sustained efficiency >= 90% measured with "
                            "refresh on (agent a8c77c67's RTL findings on the HBM comparator)"))


def choose_target_context(rec):
    """User decision 2026-09-26: the design target context is 200K or 1M, whichever maximises the ROM:HBM
    advantage -- per-user rate first (with MTP at the headline tau, then without), energy and throughput reported."""
    rows = {}
    for ctx in ("200000", "1048576"):
        b = rec["batch"][ctx]["rows"]
        r1, h1 = b["rom"][0], b["hbm"][0]
        r64 = next(r for r in b["rom"] if r["batch"] == 64)
        h64 = next(r for r in b["hbm"] if r["batch"] == 64)
        rs = max((r for r in b["rom"] if r.get("fits_capacity", True)), key=lambda r: r["ar_aggregate_tokens_s"])
        hs = max((r for r in b["hbm"] if r.get("fits_capacity", True)), key=lambda r: r["ar_aggregate_tokens_s"])
        rows[ctx] = dict(
            rom_ar=r1["ar_tokens_s_per_user"], hbm_ar=h1["ar_tokens_s_per_user"],
            rom_mtp=r1["mtp_tokens_s_per_user"], hbm_mtp=h1["mtp_tokens_s_per_user"],
            ratio_user_mtp=r1["mtp_tokens_s_per_user"] / h1["mtp_tokens_s_per_user"],
            ratio_user_ar=r1["ar_tokens_s_per_user"] / h1["ar_tokens_s_per_user"],
            ratio_energy_b1_gated=h1["ar_energy_j_per_token_gated"] / r1["ar_energy_j_per_token_gated"],
            ratio_aggregate_b64=r64["ar_aggregate_tokens_s"] / h64["ar_aggregate_tokens_s"],
            ratio_aggregate_saturated=rs["ar_aggregate_tokens_s"] / hs["ar_aggregate_tokens_s"])
    pick = max(rows, key=lambda k: (round(rows[k]["ratio_user_mtp"], 3), rows[k]["ratio_user_ar"]))
    return dict(chosen=TARGET_CTX, secondary=200000, tertiary=8192, rows=rows, ratio_rule_pick=int(pick),
                rule="user decision 2026-09-27: 1M is the primary context (the default of most agent APIs); the "
                     "earlier rule (max ROM:HBM per-user rate with MTP, then without) is kept as ratio_rule_pick")


def power_requirements(rec, req, areas):
    """Per-die power at the target against the die's cooling limit: the per-class limits of a two-die package
    (configs/hardware/power_scenarios.json cooling classes via tools/power_scenarios.cooling_limits: a shipping
    package's rating less its own stacks, per die; the air class binds the margin, liquid is reported beside it).
    The former 0.5 W/mm2 x 815 mm2 rule (technology.json thermal, an A100 module rating over its die) is withdrawn.

    Batch 1, stage clock gating: a die is active only while its layer group holds the token (about T/28 of
    the token time); its dynamic power then is its share of the token's non-clock energy over that window
    plus the clock of its block area.  Saturated batch: every die is busy all the time, so the array power is
    the aggregate rate x energy per token.  Static: the analytical design's leakage estimate (N5, per die) and
    the ASAP7 sign-off leakage density, both reported; the HBM stacks' interface power from the analytical
    design."""
    E = _env()
    c, clock = E["c"], E["clock"]
    d = E["designs"][D.ARRAY_DESIGN]
    die_mm2 = d["area_split_per_device"]["total_mm2"]
    import power_scenarios as PS
    lims = PS.cooling_limits(PS.load_cfg())
    cool_cls = {cls: v["2"]["die_w"] for cls, v in lims.items()}
    cool = cool_cls[PS.V41_COOLING]                  # liquid baseline (user decision 2026-09-28); air a sensitivity
    stat = d["static_power"]["detail"]
    et = energy_terms(E["tech"])
    rows = {}
    b = rec["batch"][str(TARGET_CTX)]["rows"]["rom"]
    b1 = b[0]
    sat = max((r for r in b if r.get("fits_capacity", True)), key=lambda r: r["ar_aggregate_tokens_s"])
    T = 1.0 / b1["ar_tokens_s_per_user"]
    nonclock = sum(v for k, v in b1["ar_energy_parts_j"].items() if k != "clock")
    layer_dies = 112.0                                          # 28 groups x 4 dies hold the 40 layers
    stages = 28
    # the HOTTEST die, not the average: its share of the per-die work over the layer-die mean (power_scenarios.
    # v41_hottest_die on the placement's stages, scenario B inputs); batch 1 keeps the average stage window
    pcfg = PS.load_cfg()
    hot_b1 = PS.v41_hottest_die(pcfg, "B_proposed_production", sys.modules[__name__], E, TARGET_CTX, 1, 1, 1.0, 0.0)
    hot_sat = PS.v41_hottest_die(pcfg, "B_proposed_production", sys.modules[__name__], E, TARGET_CTX,
                                 fill_machine(sat["batch"]).microbatch, 1, 1.0, 0.0, batch=sat["batch"])
    for m in (1, 2):
        blk = spec_area_mm2(req, areas)["total"] * m
        clk_w = et["clock"] * blk * clock
        active_avg = nonclock / layer_dies / (T / stages)
        sat_avg = sat["ar_aggregate_tokens_s"] * sat["ar_energy_j_per_token"] / 188
        active = active_avg * hot_b1["hottest_over_layer_mean"] + clk_w
        sat_w = sat_avg * hot_sat["hottest_over_layer_mean"] + (clk_w if m > 1 else 0.0)
        rows[f"m{m}"] = dict(block_mm2=blk, clock_w_active=clk_w, active_die_dynamic_w_b1=active,
                             saturated_die_dynamic_w=sat_w,
                             average_die=dict(active_dynamic_w_b1=active_avg + clk_w,
                                              saturated_dynamic_w=sat_avg + (clk_w if m > 1 else 0.0)))
    # STATIC, from the validated technology values (research agent adae6788, 2026-09-27, results/arch/
    # power_assumptions.json): leakage per mm2 of logic / ROM array; HBM interface = idle per stack + active I/O
    # energy x the die's HBM traffic (worst case: the die's sustained 3.6 TB/s); always-on package SerDes lanes
    # (84 per two-die package at the board-SerDes energy x 112 Gb/s); UCIe idle at 15% of its peak.
    P = E["tech"]["power"]
    lk = P["static_leakage_w_per_mm2"]
    lk = {k: (v["value"] if isinstance(v, dict) else v) for k, v in (lk.items() if isinstance(lk, dict) else [])}
    logic_mm2, rom_mm2 = stat["logic_mm2_per_device"], stat["rom_array_mm2_per_device"]
    leak = logic_mm2 * lk["logic"] + rom_mm2 * lk["rom_array"]
    idle_stack = P["memory_interface_idle_w_per_stack"]["value"]
    act_jb = P["memory_interface_active_j_per_bit"]["value"] if isinstance(P["memory_interface_active_j_per_bit"], dict) \
        else P["memory_interface_active_j_per_bit"]
    hbm_idle = ROM_DIE_HBM_STACKS * idle_stack
    hbm_worst = hbm_idle + act_jb * 8 * ROM_DIE_HBM_BPS
    serdes_j_bit = et["link_pj_per_bit"]["board"] * 1e-12
    serdes_w = SERDES_LANES_PER_PACKAGE_2DIE * 112e9 * serdes_j_bit / 2        # per die, always on
    ucie_idle = 0.15 * E["links"]["rom_package_ucie"]["bw"] * 8 * et["link_pj_per_bit"]["ucie"] * 1e-12
    static = leak + hbm_idle + serdes_w + ucie_idle
    dyn_worst = max(r["saturated_die_dynamic_w"] for r in rows.values())    # the hottest die
    worst = dyn_worst + leak + hbm_worst + serdes_w + ucie_idle
    ro = P["rack_overheads"]
    ro = {k: (v["value"] if isinstance(v, dict) else v) for k, v in ro.items() if k != "purpose"}
    wall = 1.0 / (ro["vr_efficiency_48v_to_core"] * ro["psu_efficiency"]) * (1 + ro["cdu_fraction_of_it"] + ro["fan_fraction_of_it"])
    provisioned = PROVISION_FACTOR * worst * wall
    return dict(cooling_limit_w_per_die=cool, cooling_limit_w_per_die_by_class=cool_cls,
                cooling_basis="configs/hardware/power_scenarios.json cooling classes, 2-die package, AIR class "
                              "(tools/power_scenarios.cooling_limits); liquid in cooling_limit_w_per_die_by_class",
                die_mm2=die_mm2,
                static_w_per_die=dict(leakage=leak, hbm_interface_idle=hbm_idle, serdes_always_on=serdes_w,
                                      ucie_idle=ucie_idle, total=static),
                hbm_interface_worst_w_per_die=hbm_worst,
                static_leakage_w_per_die_n5_analytical=leak, hbm_interface_w_per_die=hbm_worst,
                token_time_us_b1=T * 1e6, nonclock_energy_per_token_j_b1=nonclock, by_lane_mult=rows,
                hottest_die=dict(basis="power_scenarios.v41_hottest_die (scenario B inputs): the hottest die's work "
                                       "over the layer-die mean, applied to the array-average dynamic power",
                                 batch1=dict(die=hot_b1["hottest"], factor=hot_b1["hottest_over_layer_mean"]),
                                 saturated=dict(die=hot_sat["hottest"], factor=hot_sat["hottest_over_layer_mean"],
                                                batch=sat["batch"])),
                worst_case_die_w=worst, margin=cool / worst,
                margin_by_class={k: v / worst for k, v in cool_cls.items()},
                wall_factor=wall, provisioned_wall_w_per_die=provisioned,
                provisioning_rule=f"{PROVISION_FACTOR} x worst case / (VR x PSU) x (1 + CDU + fans): "
                                  "technology.json power.rack_overheads",
                requirement=("per-die power <= the cooling limit at every batch with stage clock gating: an idle "
                             "stage's clock tree gated (ICG at the block boundaries), its ROM macros and engines "
                             "quiescent; the worst case is the saturated array (every die busy)"),
                note="ASAP7 unit areas; the analytical design's 48 W/die clock term charges all 525 mm2 of logic "
                     "at 1 GHz ungated and is the upper bound if nothing gates")


def chain_ladder(req, c, areas=None):
    """The dependency-chain attack in the user-approved order: each step adds one lever to the previous; us per
    token and tokens/s per user at batch 1.  Step 4 (attention on one package) is priced at the spec's widths
    and with its attention, indexer and weight engines doubled (it doubles their per-die work); MTP (m = 2,
    headline tau) goes on top of the best step that keeps the spec's area."""
    areas = areas or unit_areas()[0]
    L3 = ("osm", "chain_all", "short_stages")
    steps = [("0 spec (baseline links)", (), req),
             ("1 reductions off the path: online softmax (norm folding rejected)", ("osm",), req),
             ("1x norm folding as well (REJECTED: changes the FP8 quantisation point)", ("fuse",), req),
             ("2 chaining for every unit", ("osm", "chain_all"), req),
             ("3 shorter stages", L3, req),
             ("4a attention on one package, spec widths", L3 + ("att_local",), req),
             ("4b attention on one package, attention/indexer/weight engines x2", L3 + ("att_local",),
              _with_widths(req, dict(att=req.att_macs * 2, idx=req.idx_macs * 2, weight=req.weight_macs * 2,
                                     bf16=req.bf16_macs * 2))),
             ("4c same engines x2, attention kept on the four-die group", L3,
              _with_widths(req, dict(att=req.att_macs * 2, idx=req.idx_macs * 2, weight=req.weight_macs * 2,
                                     bf16=req.bf16_macs * 2)))]
    out = []
    for tag, lv, sp in steps:
        row = dict(step=tag, levers=list(lv), area_mm2=spec_area_mm2(sp, areas)["total"])
        for ctx in CONTEXTS:
            r = price(sp, ctx, levers=lv)
            row[str(ctx)] = dict(us=r["T_s"] * 1e6, tokens_s_per_user=r["tokens_s_per_user"],
                                 breakdown_us={k: round(v, 2) for k, v in r["breakdown_us"].items()})
        out.append(row)
    mt = dict(step=f"5 MTP m = 2, tau {TAU_HEADLINE:g}, on step 3", levers=list(L3) + ["mtp_m2"],
              area_mm2=2 * spec_area_mm2(req, areas)["total"])
    for ctx in CONTEXTS:
        sp = replace(req, lane_mult=2)
        v = price(sp, ctx, positions=6, levers=L3)
        d = draft_cost_s(sp, ctx, 5, c)["total_s"]
        mt[str(ctx)] = dict(verify_us=v["period_s"] * 1e6, draft_us=d * 1e6,
                            tokens_s_per_user=TAU_HEADLINE / (v["period_s"] + d))
    out.append(mt)
    return out


def collective_exposure_rows(req, c):
    """Gate C7 / O2: the spec and its chain-ladder top re-priced with the RTL stage bench's measured collective
    exposure (results/arch/v41_collective_exposure.json terms; tools/collective_exposure.py) instead of bytes that
    stream behind their producer from its start.  The width derivation above keeps the overlap-assumed pricing
    (the exposure is latency, not width); these rows are the rates to quote."""
    if not D.COLLECTIVE_EXPOSURE_REC.exists():
        return None
    terms = D.load_exposure_terms()
    L3 = ("osm", "chain_all", "short_stages")
    out = dict(source=str(D.COLLECTIVE_EXPOSURE_REC.relative_to(ROOT)),
               terms_residual_cycles={k: v["residual_cycles"] for k, v in terms.items()})
    for tag, lv in (("spec", ()), ("ladder_step3", L3)):
        row = {}
        for ctx in CONTEXTS:
            r0, r1 = price(req, ctx, levers=lv), price(req, ctx, levers=lv, exposure=terms)
            row[str(ctx)] = dict(overlap_assumed=r0["tokens_s_per_user"], measured_exposure=r1["tokens_s_per_user"],
                                 us=[r0["T_s"] * 1e6, r1["T_s"] * 1e6],
                                 breakdown_us={k: round(v, 3) for k, v in r1["breakdown_us"].items()})
        out[tag] = row
    mt = {}
    for ctx in CONTEXTS:
        sp = replace(req, lane_mult=2)
        d = draft_cost_s(sp, ctx, 5, c)["total_s"]
        v0 = price(sp, ctx, positions=6, levers=L3)["period_s"]
        v1 = price(sp, ctx, positions=6, levers=L3, exposure=terms)["period_s"]
        mt[str(ctx)] = dict(overlap_assumed=TAU_HEADLINE / (v0 + d), measured_exposure=TAU_HEADLINE / (v1 + d))
    out["ladder_mtp_m2_headline_tau"] = mt
    out["tau"] = TAU_HEADLINE
    return out


def hc_mtp_sizing(req, c, areas):
    """The hyper-connection projection under the MTP verify (6 positions, m = 2) at 200K, with the measured depth:
    HC lanes per weight lane against the step-5 (chain-attacked) and the spec-only MTP rate, HC nodes on the
    critical path, and the area of the m = 2 core's HC lanes.  6 positions x 24 x 20,480 FP32 MACs per HC op."""
    L3 = ("osm", "chain_all", "short_stages")
    rows = []
    for hc in (2048.0, 4096.0, 5120.0, 6144.0, 8192.0):
        sp = replace(req, lane_mult=2, hc_macs=hc)
        out = {}
        for tag, lv in (("step5", L3), ("spec", ())):
            v = price(sp, 200000, positions=6, levers=lv, keep=True)
            b = v["_built"]
            path = set(b.g.path(b.sink))
            hcn = [n for n in b.g.nodes if n.endswith("hc.fn")]
            d = draft_cost_s(sp, 200000, 5, c)["total_s"]
            out[tag] = dict(tokens_s_per_user=TAU_HEADLINE / (v["period_s"] + d), verify_us=v["period_s"] * 1e6,
                            hc_on_path=sum(1 for n in hcn if n in path), hc_ops=len(hcn))
        work = 6 * 24 * c["hidden_size"] * c["hc_mult"]
        rows.append(dict(hc_per_weight_lane=hc, lanes_m2=2 * hc, hc_area_m2_mm2=2 * hc * areas[AREA_KEY["hc"]] / 1e6,
                         six_position_cycles=work / (2 * hc) + HC_DEPTH_CYC, **out))
    return dict(rows=rows, depth_cycles=HC_DEPTH_CYC, chosen=HC_MTP_LANES,
                rule="the smallest HC width per weight lane that keeps the step-5 MTP rate within 0.2% of unlimited "
                     "HC lanes; the unified MAC fabric may supply these lanes if it gives the HC op this issue rate "
                     "during the verify's side-branch window")


def build(quick=False):
    E = _env()
    c, clock = E["c"], E["clock"]
    areas, area_src = unit_areas()
    hl = headline()
    dag = dag_spec(dag_machine(1), clock)
    hl = dict(hl, baseline=BASELINE, plain_b=PLAIN_B,
              tokens_s_per_user_plain_b=dict(hl["tokens_s_per_user"]),
              tokens_s_per_user={ctx: price(dag, ctx)["tokens_s_per_user"] for ctx in CONTEXTS},
              tokens_s_per_user_b64={ctx: price(dag_spec(dag_machine(64), clock), ctx, batch=64)["tokens_s_per_user"]
                                     for ctx in CONTEXTS},
              source="decode_critical_path's option-(b) DAG re-priced at the baseline (light-FEC 130 ns package "
                     "link, overlapped reductions); plain (b) from " + hl["source"])
    built = as_built_spec()
    rec = dict(schema=SCHEMA, tool="tools/arch_budget_v41.py", clock_hz=clock,
               clock_basis="the report's clock: slowest routed token-path unit (decode_critical_path routed_clock)",
               requirement=dict(headline=hl, statement=(
                   "Batch-1 tokens/s per user at 8K / 200K / 1M context on packaging option (b) at least the "
                   "report's headline (no MTP); with MTP (DSpark gamma 5, 6 verified positions) a verify cycle "
                   "within the die's area; batch-64 per-user rate reported against batch 1.")),
               unit_areas_um2=areas, unit_area_sources=area_src)
    # 2. workload
    rec["workload"] = {}
    for ctx in CONTEXTS:
        tot, layers = token_workload(c, ctx)
        rec["workload"][str(ctx)] = dict(totals=tot, per_layer=layers if ctx == 200000 else None)
    rec["layer20_ops_200k"] = ops_of_layer(c, 20, 200000)[0]
    rec["collectives_per_layer"] = {str(L): collectives_of_layer(c, L) for L in (0, 2, 3, 20, 24)}
    # 3. the DAG and the as-built widths on the same graph
    rec["priced"] = {str(ctx): {sp.name: dict(tokens_s_per_user=r["tokens_s_per_user"], T_us=r["T_s"] * 1e6,
                                              breakdown_us=r["breakdown_us"],
                                              critical_issue_us_by_resource=r["critical_issue_us_by_resource"])
                                for sp in (dag, built) for r in [price(sp, ctx)]}
                     for ctx in CONTEXTS}
    # 4. budget per context, then the spec that holds at all three
    base = required_base()
    budgets, derived = {}, {}
    for ctx in CONTEXTS:
        target = 1.0 / hl["tokens_s_per_user"][ctx]
        fx = {k: fixed_part(sp, ctx) for k, sp in (("dag", dag), ("required_orders", base),
                                                    ("golden_orders", replace(base, chains="golden")),
                                                    ("as_built", built))}
        entry = dict(target_us=target * 1e6, target_tokens_s=1 / target,
                     fixed_us={k: v["T_s"] * 1e6 for k, v in fx.items()},
                     fixed_breakdown_us={k: v["breakdown_us"] for k, v in fx.items()},
                     issue_budget_us=(target - fx["required_orders"]["T_s"]) * 1e6)
        sp, info = derive(target, ctx, base, areas)
        entry.update(history=info["history"], feasible=info["feasible"])
        if sp:
            entry.update(spec=asdict(sp), area_mm2=spec_area_mm2(sp, areas),
                         priced_at_contexts={str(k): price(sp, k)["tokens_s_per_user"] for k in CONTEXTS})
            derived[ctx] = sp
        budgets[str(ctx)] = entry
    # batch 64: the report's per-user rate at 64 users (the occupancy bound joins the critical path)
    for c64 in (200000, TARGET_CTX):
        t64 = 1.0 / hl["tokens_s_per_user_b64"][c64]
        sp64, info64 = derive(t64, c64, derived[c64], areas, batch=64)
        budgets[f"{c64}_b64"] = dict(target_us=t64 * 1e6, target_tokens_s=1 / t64, feasible=info64["feasible"],
                                     history=info64["history"], spec=asdict(sp64) if sp64 else None,
                                     area_mm2=spec_area_mm2(sp64, areas) if sp64 else None)
        if sp64:
            derived[f"b64_{c64}"] = sp64
    rec["budget"] = budgets
    req = derived[200000]
    for sp in derived.values():
        req = _with_widths(req, {k: max(getattr(req, WIDTH_FIELD[k]), getattr(sp, WIDTH_FIELD[k])) for k in RESOURCES})
    # the MTP verify (6 positions, m = 2) on the chain-attacked core (ladder step 5): with the measured 126-cycle
    # depth, 2 x 4,096 HC lanes put 45 of 80 HC projections on the path (-0.7%); 2 x 5,120 take them off
    # (hc_mtp_sizing below).  The batch-1 MTP rate is the requirement, so the HC floor is 5,120 per weight lane.
    req = _with_widths(req, {"hc": max(req.hc_macs, HC_MTP_LANES)})
    rec["required_spec"] = asdict(req)
    rec["required_area_mm2"] = spec_area_mm2(req, areas)
    rec["compute_envelope_mm2"] = E["designs"][D.ARRAY_DESIGN]["area_split_per_device"]["compute_mm2"]
    rec["required_priced"] = {}
    for ctx in CONTEXTS:
        r = price(req, ctx)
        rec["required_priced"][str(ctx)] = dict(tokens_s_per_user=r["tokens_s_per_user"], T_us=r["T_s"] * 1e6,
                                                target=hl["tokens_s_per_user"][ctx], breakdown_us=r["breakdown_us"],
                                                critical_issue_us_by_resource=r["critical_issue_us_by_resource"])
    rec["batch_curve"] = {str(bt): dict(required=price(req, 200000, batch=bt)["tokens_s_per_user"],
                                        required_aggregate=price(req, 200000, batch=bt)["aggregate_tokens_s"],
                                        dag=price(dag_spec(dag_machine(bt), clock), 200000, batch=bt)["tokens_s_per_user"],
                                        as_built=price(built, 200000, batch=bt)["tokens_s_per_user"])
                          for bt in BATCHES}
    rec["select"] = select_requirements(c, req, clock)
    rec["engram"] = engram_requirement(c, 3.57e-6, clock)
    rec["blocks"] = block_table(req, built, c, areas, clock, rec["select"], rec["engram"])
    abl = {}
    for tag, sp in (("required", req),
                    ("golden_orders", replace(req, chains="golden")),
                    ("add_latency_5", replace(req, add_lat=5)),
                    ("sfu_depths_as_built", replace(req, sfu="as_built")),
                    ("no_chaining", replace(req, chaining=False)),
                    ("select_two_pass", replace(req, sel_tail="two_pass")),
                    ("su_as_built_8", replace(req, su_lanes=8, sfu_lanes=8)),
                    ("weight_engines_as_built", replace(req, weight_macs=512.0, bf16_macs=64.0, rom_bytes=528.0)),
                    ("attention_on_64_lanes", replace(req, att_macs=64.0, kv_bytes=128.0)),
                    ("indexer_on_64_lanes", replace(req, idx_macs=64.0, idx_bytes=128.0)),
                    ("seq_gap_6", replace(req, seq_gap=6))):
        abl[tag] = {str(ctx): price(sp, ctx)["tokens_s_per_user"] for ctx in CONTEXTS}
    rec["ablations_tokens_s_per_user"] = abl
    # 6. MTP on the ROM array
    hb = hbm_comparator(c)
    hbm_kw = dict(bw_Bps=hb["bw_Bps"], lat_s=hb["lat_s"], dies=hb["dies"])
    cap = rec["compute_envelope_mm2"]
    mtp = dict(tau_points=tau_points(), rom={}, hbm={}, speculation={}, design={})
    for ctx in CONTEXTS:
        mtp["rom"][str(ctx)] = {f"m{m}": mtp_rows(req, ctx, c, m) for m in (1, 6)}
        mtp["hbm"][str(ctx)] = {f"m{m}": mtp_rows(req, ctx, c, m, hbm=hbm_kw) for m in (1, 6)}
        mtp["speculation"][str(ctx)] = {
            "rom_m1": per_operator(req, ctx, 6), "rom_m6": per_operator(replace(req, lane_mult=6), ctx, 6),
            "hbm_m1": per_operator(req, ctx, 6, hbm=hbm_kw),
            "hbm_m6": per_operator(replace(req, lane_mult=6), ctx, 6, hbm=hbm_kw)}
    mtp["correlated_routing_sensitivity"] = {
        f"overlap_{ov}": dict(rom_m6_verify_us=price(replace(req, lane_mult=6), 200000, positions=6,
                                                     expert_overlap=ov)["T_s"] * 1e6,
                              hbm_m6_verify_us=price(replace(req, lane_mult=6), 200000, positions=6, hbm=hbm_kw,
                                                     expert_overlap=ov)["T_s"] * 1e6,
                              distinct=price(req, 200000, positions=6, expert_overlap=ov)["distinct_experts"])
        for ov in (0.0, 0.25, 0.5)}
    rom_cap = 2.96e12 * E["designs"][D.ARRAY_DESIGN]["area_split_per_device"]["rom_mm2"] / clock
    rec["rom_read_capacity_bytes_per_cycle"] = rom_cap
    for ctx in CONTEXTS if not quick else (200000,):
        mtp["design"][str(ctx)] = mtp_design(req, ctx, 6, areas, cap, c, rom_cap)
    rec["mtp"] = mtp
    # 7. HBM comparator
    hb["requirements"] = hbm_requirements(c, hb)
    hb["priced"] = {}
    for ctx in CONTEXTS:
        hr = price(req, ctx, hbm=hbm_kw)
        hb["priced"][str(ctx)] = dict(tokens_s_per_user=hr["tokens_s_per_user"], T_us=hr["T_s"] * 1e6,
                                      breakdown_us=hr["breakdown_us"],
                                      critical_issue_us_by_resource=hr["critical_issue_us_by_resource"],
                                      rom_over_hbm=price(req, ctx)["tokens_s_per_user"] / hr["tokens_s_per_user"])
    hb["batch_curve"] = {str(bt): price(req, 200000, batch=bt, hbm=hbm_kw)["tokens_s_per_user"] for bt in BATCHES}
    hb["efficiency_sensitivity_1m"] = {
        str(e): price(req, TARGET_CTX, hbm=dict(hbm_kw, bw_Bps=hb["bw_Bps"] / 0.9 * e))["tokens_s_per_user"]
        for e in (0.75, 0.85, 0.9, 0.95)}
    hb["efficiency_sensitivity_200k"] = {
        str(e): price(req, 200000, hbm=dict(hbm_kw, bw_Bps=hb["bw_Bps"] / 0.9 * e))["tokens_s_per_user"]
        for e in (0.75, 0.85, 0.9, 0.95)}
    rec["hbm_comparator"] = hb
    # 8. batch x MTP x energy, one model (m = 2 is the MTP design point: the knee of the m sweep)
    m_design = MTP_M_DESIGN
    rec["batch"] = {str(ctx): batch_model(req, hb, ctx, m_design, areas=areas)
                    for ctx in (CONTEXTS if not quick else (200000,))}
    rec["capacity"] = {str(ctx): capacity_limit(c, hb, ctx) for ctx in CONTEXTS}
    rec["kv_state"] = kv_state_requirements(c, req, clock)
    if not quick:
        rec["target_context"] = choose_target_context(rec)
    # the secondary row: plain option (b) -- the published links, no overlapped reductions
    rec["plain_b"] = dict(
        label=PLAIN_B["label"],
        dag_tokens_s_per_user={str(k): v for k, v in hl["tokens_s_per_user_plain_b"].items()},
        required_ar={str(ctx): price(req, ctx, base=PLAIN_B)["tokens_s_per_user"] for ctx in CONTEXTS},
        required_mtp_m2_headline_tau={str(ctx): TAU_HEADLINE / (price(replace(req, lane_mult=2), ctx, positions=6, base=PLAIN_B)[
            "period_s"] + draft_cost_s(replace(req, lane_mult=2), ctx, 5, c)["total_s"]) for ctx in CONTEXTS},
        hbm_ar={str(ctx): price(req, ctx, hbm=hbm_kw, base=PLAIN_B)["tokens_s_per_user"] for ctx in CONTEXTS})
    if not quick:
        rec["power"] = power_requirements(rec, req, areas)
    rec["chain_ladder"] = chain_ladder(req, c, areas)
    rec["collective_exposure"] = collective_exposure_rows(req, c)
    rec["hc_mtp_sizing"] = hc_mtp_sizing(req, c, areas)
    rec["replay"] = replay_summary()
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--quick", action="store_true", help="MTP design point at 200K only")
    a = ap.parse_args()
    rec = build(quick=a.quick)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=lambda o: None) + "\n")
    rp = rec["required_priced"]
    print("required spec:", {k: rec["required_spec"][k] for k in ("weight_macs", "bf16_macs", "att_macs", "idx_macs",
                                                                  "su_lanes", "sfu_lanes", "sel_lanes")})
    print("tokens/s/user:", {k: round(v["tokens_s_per_user"]) for k, v in rp.items()},
          "area mm2:", round(rec["required_area_mm2"]["total"], 1))


if __name__ == "__main__":
    main()
