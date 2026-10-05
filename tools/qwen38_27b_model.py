#!/usr/bin/env python3
"""Qwen3.8-27B: model-level study on the ROM accelerator, the HBM accelerator and GPU baselines (2026-10-03).

MODEL ONLY (owner decision 2026-10-03: third target, model level first).  No RTL, no place and route, no inference.
Inputs are committed records, each sha256-pinned in the output:

* configs/models/candidates/qwen3.8-27b.json + data/inventory/qwen3.8-27b.json: the header-only profile
  (tools/profile_hf.py --model qwen3.8-27b; config.json + safetensors headers by HTTP range read, no payload).
* data/inventory/qwen3-8b.json: the calibration model's per-layer bytes.
* results/speculative/qwen_rom_speculation_recheck_20261003/pricing.json: the measured Qwen3-8B ROM TP-4 layer
  (body 2,595 incl. 512 ME issue; one-stream all-reduce 624 = 368 fixed + 256 payload; near-HBM attention 1,700;
  non-layer 3,042; token 202,590 cycles = 5,923 tok/s at 8K) and the per-extra-verify-position increments.
* results/rtl/w15_collectives.json: the board all-gather fixed latency used for a stage hop.
* configs/hardware/technology.json: energy and idle-power constants.
* results/uarch/hbm_accelerator_study_20261003/ladder_model.py constants (restated with their line source): the
  HBM accelerator's measured 0.958 TB/s/stack streaming controller, right-sized 265.8 mm2 die with 4 stacks, SRAM
  mm2 per MiB, static power, boundary.

Method (the ROM model sweep of claude/rom-model-sweep-20261003 175d5f601, re-based on the newer measured layer):

ROM, TP-4 element replicated, S = D / 4 stages, only the active stage works on a token (1.2 GHz cycles):
  full layer = BODY_FIXED + W_layer / (4 * BW_DIE) + 2 * AR(H) + ATTN(q_in + K + V + drain + return [+ gate])
  GDN layer  = BODY_FIXED + W_layer / (4 * BW_DIE) + 2 * AR(H) + GDN unit chain (sized below; NEW unit)
  token      = sum(layers) + NONLAYER_FIXED + head / (4 * BW_DIE) + (S - 1) * stage hop
HBM accelerator (the ladder's bandwidth-bound composition, every matrix TP-sharded over n dies with 4 stacks):
  token = (streamed weight bytes + KV bytes + state bytes not in SRAM - SRAM-resident bytes) / BW + boundary
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "configs/models/candidates/qwen3.8-27b.json"
INV27 = ROOT / "data/inventory/qwen3.8-27b.json"
INV8 = ROOT / "data/inventory/qwen3-8b.json"
RECHECK = ROOT / "results/speculative/qwen_rom_speculation_recheck_20261003/pricing.json"
W15 = ROOT / "results/rtl/w15_collectives.json"
TECHP = ROOT / "configs/hardware/technology.json"
LADDER = ROOT / "results/uarch/hbm_accelerator_study_20261003/ladder_model.py"
OUT = ROOT / "results/uarch/qwen38_27b_model_20261003/model.json"

F = 1.2e9                     # streaming domain (AGENTS.md clock target)
F_SER = 0.9e9                 # serial-chain domain (AGENTS.md clock domains, LAT-3 FP32 add)
TECH = json.loads(TECHP.read_text())
_E = TECH["energy"]
_rc = json.loads(RECHECK.read_text())
_b = _rc["basis"]
_inc = _rc["increment_per_extra_position_per_layer"]
_w15 = json.loads(W15.read_text())["configs"]["v41p17_r0d1024_sweep"]

CAL = dict(
    body=_b["body"],                                   # 2,595 measured TP-4 layer body (incl. 512 ME issue)
    me_issue_8b=_inc["me_issue_total"],                # 512
    ar_fixed=_b["ar_fixed"],                           # 368 one-stream all-reduce fixed
    ar_payload_8b=_b["ar_onestream"] - _b["ar_fixed"],  # 256 at H = 4096
    attn=_b["attention_nearhbm"],                      # q_in 85, K 700, V 700, drain 76, ret_hub 139 at 8K, 16 stacks
    nonlayer=_b["nonlayer"],                           # 3,042
    token_8b=_b["token_ar_cycles"],                    # 202,590 (identity asserted)
    su_inc_8b=_inc["su_write_throughput"],             # 473 (hidden under ME issue with the overlap schedule)
    attn_inc_lanes=_inc["attention_m_attn_ge_p"],      # 112 per extra position when lanes cover it
    hop_cycles=_w15["fit"]["all_gather"]["fixed_cycles"] / _w15["clock_hz"] * F,   # 206: board stage hop (W15)
    stack_Bpc=0.9e12 / F,                              # 750 B/cycle: HBM3E 1.0 TB/s x 0.90 (uarch_model HBM_STACK_BPS)
    stack_cap_B=22.5e9 * 0.9,                          # HBM_STACK_B x HBM_CAP_EFF (uarch_model.py)
    rom_die_B=(560.0 - 6144 * (552.9 - 265.0 - (4 * 10.0 + 10.0 + 12.8)) / 6144) * 75.0e6 / 8,
    # ^ 3.14 GB: QWEN_AREA.array_mm2 less 6,144 groups of logic, at the 75 Mbit/mm2 no-ECC density (sweep CAL)
    rom_mm2_per_GB=8e3 / 75.0,                         # 106.7 mm2 of ROM array per GB at 75 Mbit/mm2
    rom_die_mm2=823.0,                                 # owner brief: ~823 mm2/die (reticle hard limit 858)
    hbm_stack_mm2=1089.0,                              # owner brief: HBM DRAM dies ~1,089 mm2 per stack
    hbm_die_mm2=265.8,                                 # ladder Q_DIE_RIGHT_MM2: right-sized HBM accelerator die, 4 stacks
    hbm_stack_Bps=0.958e12,                            # ladder Q_STACK_TBPS_MEASURED (refresh-aware controller)
    hbm_boundary_us_8b=0.3,                            # ladder Q_ABL_BOUNDARY_US: 154 exposed cycles, 36 layers
    sram_mm2_per_MiB=94.824 * 41.04 / 4096 * 1024 * 1.31 / 1e6 * 1024,   # ladder SRAM_MM2_PER_MB (128x256 macro x1.31)
    sram_w_per_mm2=0.005 + 8.5e-11 * F * 0.15,         # ladder SRAM_W_PER_MM2
    hbm_static_w_die=(22.52 + 23.81) / 2,              # economics.json qwen_hbm static (clock + leakage) per die
    rom_static_w_die=(200.0 - 16 * 2.8) / 4,           # economics.json qwen_rom static 200 W / 4 dies less 16 stacks
    stack_idle_w=TECH["power"]["memory_interface_idle_w_per_stack"]["value"],
    logic_leak_w_mm2=0.10,                             # technology.json static_leakage_w_per_mm2.logic (production)
    e_mac=_E["mac_energy_j_per_op"]["bf16"]["value"] * 2,
    e_fp32_op=_E["mac_energy_j_per_op"]["fp32"]["value"],
    e_rom_B=_E["rom_read_j_per_byte"]["value"] + _E["operand_delivery_j_per_byte"]["value"],
    e_hbm_B=_E["hbm_j_per_byte"]["value"],
    e_sram_B=_E["sram_read_j_per_byte"]["value"],
    e_board_bit=_E["link_j_per_bit"]["board_serdes_112g"]["value"],
)

# Serial-chain latencies, cycles of the 0.9 GHz serial domain.
LAT = dict(add=3,          # AGENTS.md: the measured LAT-3 FP32 add is the serial-domain root
           mul=3,          # ASSUMED equal to the add
           sfu=12)         # ASSUMED exp / sigmoid / softplus / rsqrt latency (an SU op is 6 to accept, measured)
# ASAP7 unit areas (results/arch/arch_budget_v41.json unit_areas_um2, closed or synthesised), placed at 50% density
UNIT_UM2 = dict(fp32_mac=1168.791, fp32_add=385.524, sfu_lane=34450.683)
PLACE_UTIL = 0.5           # uarch_model GPU_LOGIC_UTIL (std-cell placement density)
ATTN_LANE_SET_MM2 = 14.7   # recheck: +14.7 mm2/die per extra near-HBM attention lane set (Qwen3-8B)

# Speculation acceptance.  Published by the drafter card (z-lab/Qwen3.8-27B-DFlash2 README, H200 SGLang BF16, T 1.0,
# top-p 0.95, xhigh reasoning, 7 draft tokens a step).  MT-Bench is the general-purpose (chat) class and the
# primary figure; the five-task mean and range are the envelope.  Applied to 8-bit weights: ASSUMED transfer.
TAU7 = dict(
    mtp=dict(gsm8k=5.02, math500=4.72, humaneval=3.91, mbpp=3.99, mtbench=3.74),
    dflash2=dict(gsm8k=5.46, math500=5.28, humaneval=4.39, mbpp=4.79, mtbench=4.10),
    dspark=dict(gsm8k=4.36, math500=3.92, humaneval=3.30, mbpp=3.51, mtbench=3.01),
)
GPU_PUBLISHED = dict(   # same card, concurrency 1, output tok/s (H200, SGLang, FA3, BF16)
    ar=dict(gsm8k=68.9, math500=69.0, humaneval=69.0, mbpp=69.0, mtbench=68.9),
    mtp=dict(gsm8k=178.5, math500=172.8, humaneval=151.9, mbpp=153.1, mtbench=134.9),
    dflash2=dict(gsm8k=236.1, math500=230.7, humaneval=214.6, mbpp=226.9, mtbench=184.0),
    src="https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2 README (rev 50307d4c), Evaluation, Concurrency 1",
)
DFLASH2 = dict(params=1_924_404_480, layers=5, block=8, hidden=5120, heads=32, kv_heads=8, head_dim=128,
               window=2048, inter=17408, src="z-lab/Qwen3.8-27B-DFlash2 config.json + HF API safetensors count")
GPU_FIXED_S_8B = 1.46395e-3   # uarch_model GPU_FIT fixed_seconds_qwen (launch + sync, 36 layers; H200 NIM fit)
B200_REPO_TBPS = 5.25         # ladder constants B200_EFFECTIVE_TBPS (repo B200 fit to the DFlash paper 230 tok/s)
CTXS = (8192, 32768)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def geo_alpha(tau7, g=7):
    """Per-draft acceptance alpha with tau(g) = (1 - a^(g+1)) / (1 - a)  (i.i.d. geometric; DERIVED)."""
    lo, hi = 1e-6, 0.999999
    for _ in range(100):
        a = (lo + hi) / 2
        t = (1 - a ** (g + 1)) / (1 - a)
        lo, hi = (a, hi) if t < tau7 else (lo, a)
    return (lo + hi) / 2


def tau_at(tau7, g):
    a = geo_alpha(tau7)
    return (1 - a ** (g + 1)) / (1 - a)


# ------------------------------------------------------------------------------------------------------------------
# Model shapes
# ------------------------------------------------------------------------------------------------------------------
def shape_8b():
    inv = json.loads(INV8.read_text())
    lb = [v / 2 for v in inv["decode_layer_dense_bytes"].values()]
    head = inv["decode_dense_bytes"] / 2 - sum(lb)
    return dict(name="Qwen3-8B", L=36, H=4096, layer_B=lb, kinds=["full"] * 36, head_B=head,
                kv_pos_layer_B=2 * 8 * 128, q_per_kv=4, head_dim=128, gate=False, stored_B=inv["checkpoint_bytes"] / 2)


def shape_27b():
    p = json.loads(PROFILE.read_text())
    inv = json.loads(INV27.read_text())
    md = p["metadata"]
    la = md["linear_attention"]
    lb = [v / 2 for v in p["layer_dense_weight_bytes"]]                       # 8-bit: 1 B a parameter
    head = p["dense_weight_bytes"] / 2 - sum(lb)
    pc = inv["parameter_counts"]
    kinds = ["gdn" if t == "gated-deltanet" else "full" for t in md["attention_sequence"]]
    embed = md["vocab_size"] * p["hidden_size"]
    vision = pc["resident_only"] - embed
    return dict(name="Qwen3.8-27B", L=p["num_layers"], H=p["hidden_size"], layer_B=lb, kinds=kinds, head_B=head,
                kv_pos_layer_B=2 * md["num_key_value_heads"] * md["head_dim"],            # FP8 KV (contract)
                q_per_kv=md["num_attention_heads"] // md["num_key_value_heads"], head_dim=md["head_dim"], gate=True,
                embed_B=embed, mtp_B=pc["draft_dense"], vision_B=vision,
                stored_B=pc["decode_dense"] + embed + pc["draft_dense"],                  # text: decoder+head+embed+MTP
                gdn=dict(nk=la["key_heads"], nv=la["value_heads"], dk=la["key_dim"], dv=la["value_dim"],
                         kernel=la["conv_kernel"], conv_ch=la["conv_channels"], state_B=la["bytes_per_layer"],
                         ops=la["operations_per_layer_per_token"]),
                vocab=md["vocab_size"], mtp_layers=md["mtp_num_hidden_layers"])


def calibrate(q8):
    CAL["bw_die"] = q8["layer_B"][0] / 4 / CAL["me_issue_8b"]                 # 94.2 KB/cycle a die
    CAL["body_fixed"] = CAL["body"] - CAL["me_issue_8b"]                       # 2,083
    CAL["nonlayer_fixed"] = CAL["nonlayer"] - q8["head_B"] / (4 * CAL["bw_die"])
    CAL["kv_layer_8b_8k"] = 8192 * q8["kv_pos_layer_B"]                        # 16.8 MB over 16 stacks: K 700 + V 700


# ------------------------------------------------------------------------------------------------------------------
# The Gated DeltaNet unit (NEW: neither design has one)
# ------------------------------------------------------------------------------------------------------------------
def gdn_unit(m, lanes, k=4, stages=3, double_buffer=True):
    """Size one die's GDN unit: state per user, lanes, chain latency (streaming cycles), area.

    Golden order (HF torch_recurrent_gated_delta_rule, per value head): S *= exp(g); m = S^T k; d = (v - m) * beta;
    S += k d^T; o = S^T q -- two dependent dk-reductions with a rank-1 update between.  The unit keeps that order
    (class A).  Two passes over the die's state per token: pass A reads S, forms S*exp(g) and m; pass B re-reads S,
    recomputes S*exp(g) (same op, same rounding), adds k d^T, writes S, accumulates o.  The algebraic one-pass form
    o = (S*exp g)^T q + (k.q) d changes rounding (level 6, excluded) and is NOT priced.
    """
    g = m["gdn"]
    nv_die, nk_die = g["nv"] // k, g["nk"] // k
    elems = nv_die * g["dk"] * g["dv"]
    gdn_layers_stage = sum(1 for x in m["kinds"] if x == "gdn") / stages
    conv_B_die = g["conv_ch"] // k * (g["kernel"] - 1) * 2
    state_B_layer_die = elems * 4 + conv_B_die
    state_B_die_user = state_B_layer_die * math.ceil(gdn_layers_stage)
    tree = math.ceil(math.log2(g["dk"])) * LAT["add"]
    chain = dict(                      # serial-domain cycles on the dependent path
        conv_silu=LAT["mul"] + (g["kernel"] - 1) * LAT["add"] + LAT["sfu"] + LAT["mul"],
        l2norm_k=LAT["mul"] + tree + LAT["add"] + LAT["sfu"] + LAT["mul"],
        pass_a_tail=2 * LAT["mul"] + tree,                       # decay, x k, dk-tree (gate/beta in parallel)
        delta=LAT["add"] + LAT["mul"],
        pass_b_tail=3 * LAT["mul"] + LAT["add"] + tree,          # decay again, k d, add, x q, dk-tree
        gated_rmsnorm=LAT["mul"] + tree + LAT["mul"] + LAT["add"] + LAT["sfu"] + 3 * LAT["mul"],
    )
    pass_cyc = math.ceil(elems / lanes)
    fixed_ser = sum(chain.values())
    ar_ser = fixed_ser + 2 * pass_cyc
    per_pos_ser = 2 * pass_cyc + chain["pass_a_tail"] + chain["delta"] + chain["pass_b_tail"]   # recurrence only
    sfu_lanes = 8
    lane_um2 = UNIT_UM2["fp32_mac"] + UNIT_UM2["fp32_add"]       # MAC + its share of the dk reduction tree
    logic_mm2 = (lanes * lane_um2 + sfu_lanes * UNIT_UM2["sfu_lane"]) / PLACE_UTIL / 1e6
    sram_MiB = state_B_die_user * (2 if double_buffer else 1) / 2 ** 20
    sram_mm2 = sram_MiB * CAL["sram_mm2_per_MiB"]
    return dict(lanes_fp32=lanes, sfu_lanes=sfu_lanes, value_heads_per_die=nv_die, key_heads_per_die=nk_die,
                state_elems_per_layer_die=elems, gdn_layers_per_stage=gdn_layers_stage,
                state_B_per_layer_die=state_B_layer_die, state_B_per_user_die=state_B_die_user,
                chain_serial_cycles=chain, pass_cycles_serial=pass_cyc,
                ar_layer_cycles=round(ar_ser * F / F_SER, 1), ar_layer_ns=round(ar_ser / F_SER * 1e9, 1),
                per_extra_position_cycles=round(per_pos_ser * F / F_SER, 1),
                sram_bytes_per_cycle_needed=round(2 * lanes * 4 * F_SER / F),
                logic_mm2=round(logic_mm2, 2), sram_MiB=round(sram_MiB, 2), sram_mm2=round(sram_mm2, 2),
                double_buffered_for_speculation=double_buffer, area_mm2=round(logic_mm2 + sram_mm2, 2))


def gdn_state_in_hbm_cycles(m, s, k=4):
    """Alternative: state in the die's attached stacks: read + write the die's share every layer."""
    g = m["gdn"]
    b = 2 * (g["nv"] // k * g["dk"] * g["dv"] * 4)
    return b / (s * CAL["stack_Bpc"]) + CAL["attn"]["q_in"] + CAL["attn"]["drain"] + CAL["attn"]["ret_hub"]


# ------------------------------------------------------------------------------------------------------------------
# ROM accelerator
# ------------------------------------------------------------------------------------------------------------------
def ar_cycles(H, P=1):
    return CAL["ar_fixed"] + P * CAL["ar_payload_8b"] * H / 4096


def attn_cycles(m, ctx, kv_stacks, lane_sets, P=1, spread_stages=1):
    """Near-HBM two-phase attention; phases are the max of bandwidth and lanes (lane set = Qwen3-8B's, one position)."""
    a = CAL["attn"]
    kv_B = ctx * m["kv_pos_layer_B"]
    bw_phase = kv_B / (kv_stacks * CAL["stack_Bpc"]) / 2
    # MACs per KV byte = q heads per KV head (FP8 K/V); Qwen3-8B's lane set is matched to its stacks at 4 (GQA 32/8)
    comp_phase = bw_phase * (m["q_per_kv"] / 4) * P / lane_sets
    phase = max(bw_phase, comp_phase)
    c = a["q_in"] + 2 * phase + a["drain"] + a["ret_hub"] + (20 if m["gate"] else 0)   # +20: sigmoid output gate
    if spread_stages > 1:
        c += 2 * CAL["hop_cycles"]                                              # q out to every stage, merge back
    return c


def rom_token(m, ctx, s=4, spread=False, P=1, lanes=4096, attn_lane_sets=None, gdn_in_hbm=False):
    k = 4
    D = max(k, math.ceil(m["stored_B"] / CAL["rom_die_B"]))
    D = math.ceil(D / k) * k
    S = D // k
    if attn_lane_sets is None:
        attn_lane_sets = max(1.0, m["q_per_kv"] / 4)                          # bandwidth-matched for one position
    kv_stacks = (D if spread else k) * s
    gu = gdn_unit(m, lanes, k, S) if "gdn" in m else None
    parts = dict(body_fixed=0.0, weights=0.0, allreduce=0.0, attention=0.0, gdn=0.0)
    for i, kind in enumerate(m["kinds"]):
        parts["body_fixed"] += CAL["body_fixed"]
        parts["weights"] += P * m["layer_B"][i] / (k * CAL["bw_die"])
        parts["allreduce"] += 2 * ar_cycles(m["H"], P)
        if kind == "full":
            parts["attention"] += attn_cycles(m, ctx, kv_stacks, attn_lane_sets, P, S if spread else 1)
        else:
            if gdn_in_hbm:
                parts["gdn"] += P * gdn_state_in_hbm_cycles(m, s) + gu["ar_layer_cycles"]
            else:
                parts["gdn"] += gu["ar_layer_cycles"] + (P - 1) * gu["per_extra_position_cycles"]
    parts["nonlayer"] = CAL["nonlayer_fixed"] + P * m["head_B"] / (k * CAL["bw_die"])
    parts["stage_hops"] = (S - 1) * (CAL["hop_cycles"] + P * m["H"] * 2 / 64)
    cyc = sum(parts.values())
    return dict(k=k, s=s, kv_spread=spread, dies=D, stages=S, packages=math.ceil(D / 2), stacks=D * s,
                cycles=round(cyc), us=cyc / F * 1e6, tok_s=F / cyc,
                parts_us={x: round(v / F * 1e6, 2) for x, v in parts.items()},
                rom_fill=round(m["stored_B"] / (D * CAL["rom_die_B"]), 3), attn_lane_sets=attn_lane_sets)


def rom_spec(m, ctx, drafter, g, base_kw, rom_extra=None):
    """Speculative step on the ROM: draft (g tokens) + verify (P = g + 1 positions, back-to-back issue) + commit.

    Verify-layer increments follow the recheck's adopted configuration (widened all-reduce count, attention lanes
    covering P, SU overlap): per extra position ME issue + AR payload + attention lanes + GDN recurrence + head issue.
    """
    P = g + 1
    lane_sets = max(1.0, m["q_per_kv"] / 4) * P
    v = rom_token(m, ctx, P=P, attn_lane_sets=lane_sets, **base_kw)
    D, S = v["dies"], v["stages"]
    bw = 4 * CAL["bw_die"]
    if drafter == "mtp":
        # one native MTP layer (full gated-GQA layer + fc over [embed; hidden]) and the shared head, run g times in
        # sequence; its KV is the MTP layer's own (one full layer of KV)
        mtp_layer_B = m["mtp_B"] - m["H"] * 2 * m["H"]
        one = (CAL["body_fixed"] + mtp_layer_B / bw + 2 * m["H"] * m["H"] / bw + 2 * ar_cycles(m["H"])
               + attn_cycles(m, ctx, 4 * base_kw.get("s", 4), max(1.0, m["q_per_kv"] / 4))
               + CAL["nonlayer_fixed"] + m["head_B"] / bw)
        draft = g * one
    elif drafter == "dflash2":
        # one parallel pass: fc over 5 target hiddens, 5 drafter layers at P = block positions, head over g slots
        d = DFLASH2
        layer_B = (d["params"] - 5 * m["H"] * m["H"]) / d["layers"]
        kv_B = min(ctx, d["window"]) * 2 * d["kv_heads"] * d["head_dim"]
        Pd = d["block"]
        one = (CAL["body_fixed"] + Pd * layer_B / bw + 2 * ar_cycles(m["H"], Pd)
               + CAL["attn"]["q_in"] + kv_B / (16 * CAL["stack_Bpc"]) + CAL["attn"]["drain"] + CAL["attn"]["ret_hub"])
        draft = (5 * m["H"] * m["H"] / bw + d["layers"] * one + CAL["nonlayer_fixed"] + g * m["head_B"] / bw
                 + 200)                                          # +200: candidate-path selector, ASSUMED
    else:
        raise ValueError(drafter)
    cyc = v["cycles"] + draft + (S - 1) * CAL["hop_cycles"]       # draft output back to stage 0
    return dict(P=P, verify_cycles=v["cycles"], draft_cycles=round(draft), step_cycles=round(cyc),
                attn_lane_sets=lane_sets,
                # lane sets are matched to the die's own stacks: a Qwen3-8B set (s = 4) is 14.7 mm2, scaled by s / 4
                extra_attn_mm2_per_die=round((lane_sets - max(1.0, m["q_per_kv"] / 4)) * ATTN_LANE_SET_MM2
                                             * base_kw.get("s", 4) / 4, 1))


# ------------------------------------------------------------------------------------------------------------------
# HBM accelerator (ladder method) and energy / power
# ------------------------------------------------------------------------------------------------------------------
def hbm_accel(m, ctx, n, sram_MiB=0.0, mode="ar", drafter=None, g=7, gdn_exposed=False):
    stacks = 4 * n
    bw = stacks * CAL["hbm_stack_Bps"]
    W = sum(m["layer_B"]) + m["head_B"]
    kv = ctx * m["kv_pos_layer_B"] * sum(1 for x in m["kinds"] if x == "full")
    st = m["gdn"]["state_B"] * sum(1 for x in m["kinds"] if x == "gdn") if "gdn" in m else 0.0
    sram_B = sram_MiB * 2 ** 20
    # SRAM residency priority: GDN state first (read + write saved, 2 B of traffic a byte), then the head (read by
    # draft and verify under speculation), then decoder weights
    st_res = min(sram_B, st)
    rest = sram_B - st_res
    boundary = CAL["hbm_boundary_us_8b"] * m["L"] / 36 * 1e-6
    gdn_s = 0.0
    if gdn_exposed and "gdn" in m:     # sensitivity: the GDN chain NOT hidden under the weight stream
        gdn_s = sum(1 for x in m["kinds"] if x == "gdn") * gdn_unit(m, 4096, 4, 1)["ar_layer_ns"] * 1e-9
    if mode == "ar":
        head_res = min(rest, m["head_B"])
        w_res = min(rest - head_res, W - m["head_B"])
        traffic = W + kv + 2 * st - 2 * st_res - head_res - w_res
        t = traffic / bw + boundary + gdn_s
        return dict(dies=n, stacks=stacks, sram_MiB=round(sram_MiB), bytes=traffic, us=t * 1e6, tok_s=1 / t,
                    capacity_ok=W + m.get("embed_B", 0) + kv + st <= stacks * CAL["stack_cap_B"])
    # speculation: draft + one verify of P = g + 1 <= 16 positions on one weight fetch (16 MMA columns)
    if drafter == "dflash2":
        draft_B = DFLASH2["params"] + m["head_B"]
    else:                                                               # MTP: g sequential passes
        draft_B = g * (m["mtp_B"] + m["head_B"])
    head_res = min(rest, m["head_B"])
    w_res = min(rest - head_res, W - m["head_B"])
    head_reads = 2 if drafter == "dflash2" else g + 1
    traffic = W + kv + 2 * st + draft_B - 2 * st_res - head_reads * head_res - w_res
    t = traffic / bw + 2 * boundary + gdn_s * (g + 1)
    return dict(dies=n, stacks=stacks, sram_MiB=round(sram_MiB), bytes=traffic, step_us=t * 1e6, g=g)


def rom_energy(m, r, ctx, lanes_area):
    act = sum(m["layer_B"]) + m["head_B"]
    kv = ctx * m["kv_pos_layer_B"] * sum(1 for x in m["kinds"] if x == "full")
    st = m["gdn"]["state_B"] * sum(1 for x in m["kinds"] if x == "gdn") if "gdn" in m else 0.0
    gops = m["gdn"]["ops"] * sum(1 for x in m["kinds"] if x == "gdn") if "gdn" in m else 0.0
    e_dyn = (act * CAL["e_mac"] + act * CAL["e_rom_B"] + kv * (CAL["e_hbm_B"] + 2 * CAL["e_sram_B"])
             + 3 * st * CAL["e_sram_B"] + gops * CAL["e_fp32_op"]
             + 2 * m["L"] * m["H"] * 4 * 8 * CAL["e_board_bit"] * 3)
    D = r["dies"]
    p_static = D * (CAL["rom_static_w_die"] + r["s"] * CAL["stack_idle_w"]
                    + lanes_area["logic_mm2"] * CAL["logic_leak_w_mm2"] + lanes_area["sram_mm2"] * CAL["sram_w_per_mm2"])
    T = 1 / r["tok_s"]
    return dict(e_dyn_mJ=round(e_dyn * 1e3, 2), static_W=round(p_static, 1), system_W=round(p_static + e_dyn / T, 1),
                mJ_per_token=round((e_dyn + p_static * T) * 1e3, 2))


def hbm_energy(m, h, rate):
    act = sum(m["layer_B"]) + m["head_B"]
    sram_mm2 = h["sram_MiB"] * CAL["sram_mm2_per_MiB"]
    static = h["dies"] * CAL["hbm_static_w_die"] + h["stacks"] * CAL["stack_idle_w"] + sram_mm2 * CAL["sram_w_per_mm2"]
    e_dyn = h["bytes"] * CAL["e_hbm_B"] + h["sram_MiB"] * 2 ** 20 * CAL["e_sram_B"] + act * CAL["e_mac"]
    return dict(e_dyn_mJ=round(e_dyn * 1e3, 2), static_W=round(static, 1), system_W=round(static + e_dyn * rate, 1),
                mJ_per_token=round((e_dyn + static / rate) * 1e3, 2))


def rom_silicon(r, gdn_area):
    return r["dies"] * CAL["rom_die_mm2"] + r["stacks"] * CAL["hbm_stack_mm2"]


def hbm_silicon(n, sram_MiB):
    return n * (CAL["hbm_die_mm2"] + 4 * CAL["hbm_stack_mm2"]) + sram_MiB * CAL["sram_mm2_per_MiB"]


def hbm_iso_silicon(m, ctx, total_mm2):
    per = CAL["hbm_die_mm2"] + 4 * CAL["hbm_stack_mm2"]
    n = max(1, int(total_mm2 // per))
    spare = total_mm2 - n * per
    return n, spare / CAL["sram_mm2_per_MiB"]


# ------------------------------------------------------------------------------------------------------------------
def gpu_rows(m, ctx):
    """Tier 1: published H200 measurement (BF16, short context).  Tier 2: t = fixed + bytes / (eta x peak BW), the
    fixed launch/sync term scaled from the repo's H200 NIM fit by layer count, eta calibrated on the H200 point."""
    fixed = GPU_FIXED_S_8B * m["L"] / 36
    st = m["gdn"]["state_B"] * 48
    bf16_B = 2 * (sum(m["layer_B"]) + m["head_B"]) + 2 * st
    eta = bf16_B / (1 / GPU_PUBLISHED["ar"]["mtbench"] - fixed) / 4.8e12
    rows = [dict(gpu="1x H200 SXM, SGLang FA3, BF16, AR, short context (published)", tier=1,
                 ar_tok_s=GPU_PUBLISHED["ar"]["mtbench"], mtp7_tok_s=GPU_PUBLISHED["mtp"]["mtbench"],
                 dflash2_tok_s=GPU_PUBLISHED["dflash2"]["mtbench"],
                 dflash2_tok_s_range=[min(GPU_PUBLISHED["dflash2"].values()), max(GPU_PUBLISHED["dflash2"].values())],
                 power_W=700.0, power_note="H200 SXM TDP 700 W (published; decode draw lower, not measured)",
                 silicon_mm2=round(814 + 6 * CAL["hbm_stack_mm2"]), src=GPU_PUBLISHED["src"])]
    sp_mtp = GPU_PUBLISHED["mtp"]["mtbench"] / GPU_PUBLISHED["ar"]["mtbench"]
    sp_df = GPU_PUBLISHED["dflash2"]["mtbench"] / GPU_PUBLISHED["ar"]["mtbench"]
    for name, peak, power, si in (("B200", 8.0e12, 689.0, 2 * 800 + 8 * CAL["hbm_stack_mm2"]),
                                  ("H100 SXM", 3.35e12, 700.0, 814 + 5 * CAL["hbm_stack_mm2"])):
        fp8_B = (sum(m["layer_B"]) + m["head_B"]) + ctx * m["kv_pos_layer_B"] * 16 + 2 * st
        t = fixed + fp8_B / (eta * peak)
        row = dict(gpu=f"1x {name}, FP8 weights + FP8 KV, {ctx // 1024}K (tier-2 MODELLED, eta {eta:.2f} from H200)",
                   tier=2, ar_tok_s=round(1 / t, 1), mtp7_tok_s=round(sp_mtp / t, 1), dflash2_tok_s=round(sp_df / t, 1),
                   power_W=power, silicon_mm2=round(si),
                   power_note=("measured Qwen3-8B decode draw 689 W (ladder; TDP 1,000-1,200 W)" if name == "B200"
                               else "H100 SXM TDP 700 W (published)"),
                   spec_note="MTP-7 / DFlash2 speedups transferred from the H200 MT-Bench measurement (ASSUMED)")
        if name == "B200":
            row["ar_tok_s_repo_fit"] = round(1 / (fixed + fp8_B / B200_REPO_TBPS / 1e12), 1)
        rows.append(row)
    for r in rows:
        r["J_per_token_ar"] = round(r["power_W"] / r["ar_tok_s"], 2)
        r["J_per_token_dflash2"] = round(r["power_W"] / r["dflash2_tok_s"], 2)
    return rows, eta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    q8 = shape_8b()
    calibrate(q8)
    ident = rom_token(q8, 8192, s=4)
    # 202,590 recorded; the record rounds the K and V phases to 700 (699.05 from the bytes): 68 cycles, 0.03%
    assert abs(ident["cycles"] / CAL["token_8b"] - 1) < 5e-4, (ident["cycles"], CAL["token_8b"])
    m = shape_27b()
    D0 = rom_token(m, 8192)["dies"]
    free_rom_mm2_die = (D0 * CAL["rom_die_B"] - m["stored_B"]) / D0 / 1e9 * CAL["rom_mm2_per_GB"]

    # 1. GDN unit sizing sweep (die of the TP-4 element, S = 3 stages)
    lanes_sweep = []
    prev = None
    for lanes in (512, 1024, 2048, 4096, 8192):
        gu = gdn_unit(m, lanes)
        r = rom_token(m, 8192, lanes=lanes)
        row = dict(lanes=lanes, gdn_layer_cycles=gu["ar_layer_cycles"], token_tok_s=round(r["tok_s"], 1),
                   gain_vs_previous_pct=(round((r["tok_s"] / prev - 1) * 100, 2) if prev else None),
                   logic_mm2=gu["logic_mm2"], area_mm2_with_state=gu["area_mm2"])
        prev = r["tok_s"]
        lanes_sweep.append(row)
    # adopt the widest lane count whose step gains >= 1% (AGENTS.md adoption gate)
    lanes_adopt = lanes_sweep[0]["lanes"]
    for row in lanes_sweep[1:]:
        if row["gain_vs_previous_pct"] >= 1.0:
            lanes_adopt = row["lanes"]
    gu = gdn_unit(m, lanes_adopt)
    gu_hbm_state = rom_token(m, 8192, lanes=lanes_adopt, gdn_in_hbm=True)
    gu_sram_state = rom_token(m, 8192, lanes=lanes_adopt)
    full_layer_attn = attn_cycles(m, 8192, 16, max(1.0, m["q_per_kv"] / 4))
    gdn = dict(
        architecture=dict(layers=sum(1 for x in m["kinds"] if x == "gdn"), **m["gdn"]),
        state_per_user_B=m["gdn"]["state_B"] * 48, state_per_user_MB=round(m["gdn"]["state_B"] * 48 / 1e6, 1),
        fp32_state_B_per_layer=m["gdn"]["nv"] * m["gdn"]["dk"] * m["gdn"]["dv"] * 4,
        conv_state_B_per_layer=m["gdn"]["state_B"] - m["gdn"]["nv"] * m["gdn"]["dk"] * m["gdn"]["dv"] * 4,
        ops_per_token=m["gdn"]["ops"] * 48, ops_share_of_weight_ops=round(m["gdn"]["ops"] * 48 /
                                                                         (2 * (sum(m["layer_B"]) + m["head_B"])), 4),
        state_traffic_per_token_B=3 * m["gdn"]["state_B"] * 48,
        lanes_sweep=lanes_sweep, lanes_adopted=lanes_adopt, lanes_rule="widest lane count whose step adds >= 1% rate",
        unit_per_die=gu, rom_slack_mm2_per_die=round(free_rom_mm2_die, 1),
        fits_in_rom_slack=gu["area_mm2"] <= free_rom_mm2_die,
        where_state_lives=dict(
            sram_on_die=dict(tok_s_8k=round(gu_sram_state["tok_s"], 1), gdn_us=gu_sram_state["parts_us"]["gdn"]),
            attached_hbm_s4=dict(tok_s_8k=round(gu_hbm_state["tok_s"], 1), gdn_us=gu_hbm_state["parts_us"]["gdn"]),
            verdict="SRAM on die: fits in the ROM slack and saves the HBM round trip on every GDN layer"),
        gdn_layer_vs_full_layer_cycles=dict(gdn_unit=gu["ar_layer_cycles"], full_attention_8k=round(full_layer_attn)),
        batch_note=("state is 12.8 MB per user per die: the double-buffered single-user state plus spare slack holds "
                    f"~{int((free_rom_mm2_die - gu['logic_mm2']) / (gu['sram_mm2'] / 2))} users' state per die in SRAM; "
                    "beyond that it spills to the attached stacks (secondary throughput path)"),
        sweep_assumption_replaced="rom_model_sweep: 200 ASSUMED cycles + attention fixed + state via HBM per GDN layer",
    )

    # 2. ROM design points
    rom_pts = []
    for s in (1, 2, 4):
        for spread in (False, True):
            for ctx in CTXS:
                r = rom_token(m, ctx, s=s, spread=spread, lanes=lanes_adopt)
                rom_pts.append(dict(ctx=ctx, s=s, kv_spread=spread, dies=r["dies"], stacks=r["stacks"],
                                    tok_s=round(r["tok_s"], 1), us=round(r["us"], 1),
                                    silicon_mm2=round(rom_silicon(r, gu)), parts_us=r["parts_us"]))

    def pick(ctx, s, spread):
        return next(p for p in rom_pts if p["ctx"] == ctx and p["s"] == s and p["kv_spread"] == spread)

    gpus8, eta = gpu_rows(m, 8192)
    gpus32, _ = gpu_rows(m, 32768)
    results = {}
    for ctx in CTXS:
        res = {}
        for label, s, spread in (("rom_s4_local", 4, False), ("rom_s1_spread", 1, True), ("rom_s2_spread", 2, True)):
            r = rom_token(m, ctx, s=s, spread=spread, lanes=lanes_adopt)
            si = rom_silicon(r, gu)
            en = rom_energy(m, r, ctx, gu)
            slack = free_rom_mm2_die
            ar_attn_mm2 = (max(1.0, m["q_per_kv"] / 4) - 1.0) * ATTN_LANE_SET_MM2 * s / 4   # 1.5 sets: GQA 6 x 256
            # speculation on the ROM: best g per drafter, MT-Bench tau (primary) and the 5-task envelope
            spec = {}
            for drafter in ("mtp", "dflash2"):
                best = None
                for g in range(1, 8):
                    st = rom_spec(m, ctx, drafter, g, dict(s=s, spread=spread, lanes=lanes_adopt))
                    tau = tau_at(TAU7[drafter]["mtbench"], g)
                    rate = tau * F / st["step_cycles"]
                    if best is None or rate > best["tok_s"]:
                        best = dict(g=g, tau_mtbench=round(tau, 3), tok_s=round(rate, 1), **st)
                env = [round(tau_at(TAU7[drafter][b], best["g"]) * F / best["step_cycles"], 1) for b in TAU7[drafter]]
                best["tok_s_envelope_5tasks"] = [min(env), max(env)]
                best["speedup_vs_ar"] = round(best["tok_s"] / r["tok_s"], 3)
                drafter_rom_mm2 = (DFLASH2["params"] if drafter == "dflash2" else 0) / r["dies"] / 1e9 \
                    * CAL["rom_mm2_per_GB"]                               # MTP is already in stored_B
                need = gu["area_mm2"] + ar_attn_mm2 + best["extra_attn_mm2_per_die"] + drafter_rom_mm2
                best["die_area_ledger_mm2"] = dict(slack=round(slack, 1), gdn_unit=gu["area_mm2"],
                                                   attn_lanes_ar=round(ar_attn_mm2, 1),
                                                   attn_lanes_verify_extra=best["extra_attn_mm2_per_die"],
                                                   drafter_rom=round(drafter_rom_mm2, 1), total=round(need, 1),
                                                   fits=need <= slack)
                spec[drafter] = best
            # HBM accelerator at iso total silicon and at iso power
            n_iso, sram_iso = hbm_iso_silicon(m, ctx, si)
            h_iso = hbm_accel(m, ctx, n_iso, sram_iso)
            e_iso = hbm_energy(m, h_iso, h_iso["tok_s"])
            n_pw = 1
            while True:
                hh = hbm_accel(m, ctx, n_pw + 1, 0.0)
                if hbm_energy(m, hh, hh["tok_s"])["system_W"] > en["system_W"]:
                    break
                n_pw += 1
            h_pw = hbm_accel(m, ctx, n_pw, 0.0)
            e_pw = hbm_energy(m, h_pw, h_pw["tok_s"])
            hspec = {}
            for drafter in ("mtp", "dflash2"):
                best = None
                for g in range(1, 8):
                    st = hbm_accel(m, ctx, n_iso, sram_iso, mode="spec", drafter=drafter, g=g)
                    tau = tau_at(TAU7[drafter]["mtbench"], g)
                    rate = tau / (st["step_us"] * 1e-6)
                    if best is None or rate > best["tok_s"]:
                        best = dict(g=g, tau_mtbench=round(tau, 3), tok_s=round(rate, 1),
                                    step_us=round(st["step_us"], 1))
                hspec[drafter] = best
            h_exp = hbm_accel(m, ctx, n_iso, sram_iso, gdn_exposed=True)
            g_df = hspec["dflash2"]["g"]
            st_exp = hbm_accel(m, ctx, n_iso, sram_iso, mode="spec", drafter="dflash2", g=g_df, gdn_exposed=True)
            hspec["dflash2"]["tok_s_gdn_chain_exposed"] = round(tau_at(TAU7["dflash2"]["mtbench"], g_df)
                                                                / (st_exp["step_us"] * 1e-6), 1)
            best_rom = max(r["tok_s"], *(v["tok_s"] for v in spec.values()))
            best_hbm = max(h_iso["tok_s"], *(v["tok_s"] for v in hspec.values()))
            gpu = (gpus8 if ctx == 8192 else gpus32)[1]                            # B200 FP8 tier 2
            res[label] = dict(
                rom=dict(dies=r["dies"], stages=r["stages"], packages=r["packages"], stacks=r["stacks"],
                         die_area_ledger_ar_mm2=dict(slack=round(slack, 1), gdn_unit=gu["area_mm2"],
                                                     attn_lanes_ar=round(ar_attn_mm2, 1),
                                                     fits=gu["area_mm2"] + ar_attn_mm2 <= slack),
                         rom_fill=r["rom_fill"], silicon_mm2=round(si), ar_tok_s=round(r["tok_s"], 1),
                         ar_us=round(r["us"], 1), parts_us=r["parts_us"], energy=en,
                         kv_and_state_fit_users=int(r["stacks"] * CAL["stack_cap_B"]
                                                    // (ctx * m["kv_pos_layer_B"] * 16 + m["gdn"]["state_B"] * 48)),
                         spec=spec),
                hbm_iso_silicon=dict(dies=n_iso, stacks=4 * n_iso, sram_MiB=round(sram_iso),
                                     silicon_mm2=round(hbm_silicon(n_iso, sram_iso)), ar_tok_s=round(h_iso["tok_s"], 1),
                                     ar_tok_s_gdn_chain_exposed=round(h_exp["tok_s"], 1),
                                     capacity_ok=h_iso["capacity_ok"], energy=e_iso, spec=hspec),
                hbm_iso_power=dict(dies=n_pw, stacks=4 * n_pw, ar_tok_s=round(h_pw["tok_s"], 1), energy=e_pw,
                                   silicon_mm2=round(hbm_silicon(n_pw, 0))),
                ratios=dict(ar_iso_silicon=round(r["tok_s"] / h_iso["tok_s"], 2),
                            ar_iso_power=round(r["tok_s"] / h_pw["tok_s"], 2),
                            best_spec_iso_silicon=round(best_rom / best_hbm, 2),
                            energy_hbm_iso_si_over_rom=round(e_iso["mJ_per_token"] / en["mJ_per_token"], 2),
                            rom_ar_over_b200_fp8_ar=round(r["tok_s"] / gpu["ar_tok_s"], 1),
                            rom_best_over_b200_fp8_dflash2=round(best_rom / gpu["dflash2_tok_s"], 1),
                            hbm_best_over_b200_fp8_dflash2=round(best_hbm / gpu["dflash2_tok_s"], 1)),
            )
        results[str(ctx)] = res

    # 3. HBM accelerator on the silicon of one B200 package (2 dies, 8 stacks) for the GPU comparison
    b200_like = {}
    for ctx in CTXS:
        spare = 2 * (815.0 - CAL["hbm_die_mm2"])
        sram = spare / CAL["sram_mm2_per_MiB"]
        h = hbm_accel(m, ctx, 2, sram)
        best = max(((tau_at(TAU7["dflash2"]["mtbench"], g) / (hbm_accel(m, ctx, 2, sram, "spec", "dflash2", g)
                                                               ["step_us"] * 1e-6)), g) for g in range(1, 8))
        b200_like[str(ctx)] = dict(dies=2, stacks=8, sram_MiB=round(sram), ar_tok_s=round(h["tok_s"], 1),
                                   dflash2_tok_s=round(best[0], 1), dflash2_g=best[1],
                                   energy=hbm_energy(m, h, h["tok_s"]))

    srcs = [PROFILE, INV27, INV8, RECHECK, W15, TECHP, LADDER, Path(__file__)]
    rec = dict(
        schema="opentallas.uarch.qwen38_27b_model.v1", status="MODEL_ONLY_NOT_ADOPTED",
        scope=("Qwen3.8-27B per-user decode (batch 1) on the ROM accelerator, the HBM accelerator and GPU baselines; "
               "iso total silicon (HBM DRAM counted) and iso power; energy per token; Gated DeltaNet unit sizing. "
               "No RTL, no P&R, no inference."),
        model=dict(repo="Qwen/Qwen3.8-27B", revision="1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0", license="apache-2.0",
                   name_check="exact name exists on Hugging Face (created 2026-08-05); config read from it",
                   layers=m["L"], hidden=m["H"], layer_mix=dict(gated_deltanet=48, full_gated_gqa=16),
                   full_attention=dict(q_heads=24, kv_heads=4, head_dim=256, partial_rotary=0.25, output_gate="sigmoid",
                                       kv_fp8_B_per_pos_per_layer=m["kv_pos_layer_B"]),
                   ffn_intermediate=17408, vocab=m["vocab"], tied_embeddings=False, mtp_layers=m["mtp_layers"],
                   max_context=262144,
                   bytes_8bit=dict(decoder=sum(m["layer_B"]), head=m["head_B"], embed=m["embed_B"], mtp=m["mtp_B"],
                                   stored_text=m["stored_B"], vision_excluded=m["vision_B"]),
                   kv_MB_per_user={str(c): round(c * m["kv_pos_layer_B"] * 16 / 1e6, 1) for c in CTXS},
                   drafters=dict(native_mtp="1 layer, run recursively (card: 'built-in seven-token MTP')",
                                 dflash2=DFLASH2)),
        calibration=dict(CAL, identity=dict(qwen3_8b_rom_cycles=ident["cycles"], target=CAL["token_8b"])),
        latencies_serial=LAT, unit_um2=UNIT_UM2,
        acceptance=dict(tau_at_7_drafts=TAU7, primary="mtbench (general-purpose chat)",
                        smaller_g="DERIVED: i.i.d. geometric acceptance fitted to tau(7)",
                        grade="published on BF16 H200 at T 1.0; 8-bit transfer ASSUMED"),
        gdn_unit=gdn, rom_points=rom_pts, results=results,
        gpu=dict(ctx_8k=gpus8, ctx_32k=gpus32, eta_calibrated=round(eta, 3)),
        hbm_accel_on_one_b200_footprint=b200_like,
        sources={str(p.relative_to(ROOT)): sha(p) for p in srcs},
    )
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(lanes=lanes_adopt, gdn=gu, slack=free_rom_mm2_die), indent=1))
    for ctx, res in results.items():
        for lab, x in res.items():
            print(ctx, lab, "ROM", x["rom"]["dies"], x["rom"]["stacks"], x["rom"]["silicon_mm2"], x["rom"]["ar_tok_s"],
                  {k: (v["g"], v["tok_s"]) for k, v in x["rom"]["spec"].items()}, x["rom"]["energy"]["mJ_per_token"],
                  x["rom"]["energy"]["system_W"])
            print("    HBMiso", x["hbm_iso_silicon"]["dies"], x["hbm_iso_silicon"]["sram_MiB"],
                  x["hbm_iso_silicon"]["ar_tok_s"], {k: (v["g"], v["tok_s"]) for k, v in x["hbm_iso_silicon"]["spec"].items()},
                  x["hbm_iso_silicon"]["energy"]["mJ_per_token"], "HBMpw", x["hbm_iso_power"]["dies"],
                  x["hbm_iso_power"]["ar_tok_s"], x["ratios"])
    for g in gpus8:
        print(g["gpu"], g["ar_tok_s"], g["dflash2_tok_s"], g.get("ar_tok_s_repo_fit"))
    print(b200_like)


if __name__ == "__main__":
    main()
