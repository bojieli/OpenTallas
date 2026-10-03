#!/usr/bin/env python3
"""Re-check of speculative decoding on the Qwen3-8B ROM die against the CURRENT measured design (2026-10-03).

    python3 tools/qwen_rom_speculation_recheck.py [--out DIR] [--burst-gate JSON]

The 2026-09-29 decision (USER: the Qwen ROM die is AR only, no DFlash drafter in ROM) rested on
results/speculative/dflash_step_timing.json: "m=1 never beats AR: the Qwen token is lane-bound; weight
issue is ~36% of the step".  Since then the measured TP4 layer is 3,930 cycles with the one-stream
all-reduce (results/rtl/qwen_rom_TP4_allreduce_oneseg_20261003, branch claude/qwen-allreduce-oneseg-20261003
@ 7d736e8e6), and only 512 of those cycles are matrix-engine ISSUE: the rest is fixed latency (112-cycle
wire stages per ME op, the all-reduce round trip, the SU chain).  A verify position pays the issue and the
per-position throughput terms, not the fixed latencies.  This tool prices that.

Per-layer decomposition (cycles at 1.2 GHz), AR at an 8K context with near-HBM attention (selected):
  body      2,595  measured: 3,930 (one-stream layer) - 87 (pos-0 attention span) - 2 x 624 (all-reduces)
  AR        2 x 624 measured one-stream all-reduce (256 words + 368 round trip)
  attention 1,700  model (near-HBM, two-pass exact; 700 K + 700 V phases bandwidth-bound at 0.9 TB/s/stack)
  layer     5,543; nonlayer 3,042 (head 2,998 measured + 44); token 36 x 5,543 + 3,042 = 202,590 cycles

Increment per extra verify position, per layer:
  ME issue   512  = sum of tiles x k x IL over the four projections of the TP4 program
                   (QKV 1x8x8 = 64, O 3x2x8 = 48, gate/up 1x32x8 = 256, down 3x6x8 = 144); the burst gate
                   (tools/qwen_rom_verify_burst_gate.py) measures that back-to-back copies on the unmodified
                   engine cost issue (+ the 1-cycle issue gap) each and are bit-identical to solo issue.
  SU         473  = measured su_writes 30,236 per layer / 64 lanes (a lower bound of SU write throughput);
                   "overlap" schedules hide it under ME issue (it chases the ME), "serial" adds it.
  AR         existing RTL: a 256-word descriptor per position, one at a time (+624 per AR); widened
                   descriptor count (an RTL change like ENABLE_AR256): +256 words per AR.
  attention  m_attn = 1 (lanes sized for one position, the selected design): both phases become compute
                   bound, +1,400 + 40 (q serialise) + 72 (P.V/Z partials return) per position;
                   m_attn >= p: +112 per position.  Partial: phases = 700 x ceil(p / m_attn).
  head       +1,584 issue per extra argmax position (37,984 rows/die x 4,096 / 98,304 lanes).
ME lane multiplier m (weight-broadcast lanes, like rtl/hdc/ot_hdc_qwen_m5_verify_array.sv): issue x ceil(p/m).

Step = draft + verify(B) + commit.  DFlash draft (z-lab/Qwen3-8B-DFlash-b16: fc + 5 Qwen3-8B-shaped layers,
shared embedding and lm_head): fc and the drafter's context K/V over the tau committed positions, 5 drafter
layers at p = B (anchor + B-1 mask slots, the drafter's attention reads its own 8K context KV near-HBM), the
lm_head + argmax over the B-1 draft slots.  Verify = 36 target layers at p = B + the lm_head at p = B.
DSpark = the DFlash backbone + a Markov head (r = 256; arXiv 2607.05147): its slots' argmaxes are
sequential, priced as (B-1) x 1,000 cycles (ASSUMED: a 396-issue low-rank correction + ~600 latency).
Drafter weights: ROM (+30.4 mm2/die model formula, 15.4 with r2's macro count) or attached HBM
(262 MB/die INT8 streamed per step at 3.6 TB/s/die, MACs on the near-HBM lanes).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCEPT = ROOT / "results/speculative/dflash_block_acceptance.json"
OUT = ROOT / "results/speculative/qwen_rom_speculation_recheck_20261003"
CLOCK = 1.2e9
L = 36

# ---- calibrated per-layer basis (cycles) -------------------------------------------------------------------
MEASURED_LAYER_ONESTREAM = 3930      # results/rtl/qwen_rom_TP4_allreduce_oneseg_20261003/measured.json, L1 run B/C
POS0_ATTENTION = 87                  # near-hbm-selected-r1.json composition (on-core pos-0 attention span)
AR_ONESTREAM = 624                   # Verilator gate + runtime (369 saved/AR against 2 x 490)
AR_WORDS = 256                       # 4,096 FP32 / 16 lanes
AR_FIXED = AR_ONESTREAM - AR_WORDS   # 368: LAT 339 + fold 17 + handoff 12
BODY = MEASURED_LAYER_ONESTREAM - POS0_ATTENTION - 2 * AR_ONESTREAM   # 2,595
ATTN = dict(q_in=85, K=700, V=700, drain=76, ret_hub=139)            # near-hbm-selected-r1.json primary
ATTN_TOTAL = sum(ATTN.values())      # 1,700
ATTN_Q_SERIAL = 40                   # q serialise term inside q_in (45 wire + 40), grows with p
ATTN_RET_BITS, LINK_BITS = 37120, 512  # partials out of each stack per position-layer; link width
NONLAYER = 3042                      # head 2,998 measured + 44 (near-hbm-selected-r1.json)
HEAD_MEASURED = 2998
HEAD_ISSUE = 1584                    # lm_head issue per position per die (37,984 rows, as_built unit_busy)
ME_ISSUE = dict(qkv=1 * 8 * 8, o=3 * 2 * 8, gate_up=1 * 32 * 8, down=3 * 6 * 8)   # 512
SU_PER_POS = -(-30236 // 64)      # 473: measured su_writes per layer / SU width
ISSUE_GAP = 1                        # core issue gap (ot_hdc_core_vector_weight.sv), per back-to-back op

# ---- drafter ------------------------------------------------------------------------------------------------
DRAFT_LAYERS = 5
FC_ISSUE_PER_POS = round(4096 * 5 * 4096 / 4 / 98304)            # 213
DKV_ISSUE_PER_POS = round(DRAFT_LAYERS * 2 * 1024 * 4096 / 4 / 98304)  # 107: drafter context K/V projections
FC_FIXED = 250                       # ASSUMED: one ME op's fill + wire (the measured per-op 188-336)
DSPARK_SERIAL_PER_SLOT = 1000        # ASSUMED (see module docstring)
DRAFTER_BYTES_PER_DIE = 1_048_626_432 / 4   # INT8, the BF16 safetensors parameter count, TP4
HBM_BPS_PER_DIE = 4 * 0.9e12
NEARHBM_LANES = 12288
DRAFT_LAYER_BYTES = (DRAFTER_BYTES_PER_DIE - 4096 * 5 * 4096 / 4) / DRAFT_LAYERS
COMMIT = 10                          # accept compares + bonus + DYN (ot_hdc_accept), a few cycles

# ---- area (mm2 per die) -------------------------------------------------------------------------------------
AREA = dict(
    drafter_rom_model=30.36,         # (1536-24) tiles x 2 macros x 7,663.9 um2 x 1.31 (uarch_model QWEN_AREA)
    drafter_rom_r2_macros=15.4,      # r2 tile slot holds 10 macros: +1 macro per tile
    dspark_markov_head_rom=1.13,     # 151,936 x 256 INT8 / 4 dies, at the drafter's ROM density
    me_lanes_per_extra_m=51.9,       # 98,304 lanes x 528.08 um2 (ot_hdc_lane_copy, routed)
    attn_lanes_per_extra_m=14.7,     # 13.17 lanes + 0.97 exp + 0.2 score SRAM + 0.39 tree (nearhbm pricing)
    widened_ar_count=0.05,           # count field + DEPTH 1,024 macro FIFO (AR256 record: 0.111 at 1,024)
)
BUDGET = dict(margin_to_815=23.0, shoreline_free=20.29, io_spare=9.11)   # floorplan r2 (ced04cd96)

# ---- workloads (USER 2026-10-03: eight equal-weight classes) ------------------------------------------------
CLASSES = {
    "chat": ["chat_mt_bench"],
    "reasoning": ["reasoning_math500", "reasoning_aime25"],
    "coding": ["reasoning_humaneval"],
    "long_doc_rag": None,
    "multilingual": None,
    "long_agentic": ["agentic_swe_agent", "agentic_tau_bench", "agentic_mind2web"],
    "assistant_structured": ["agentic_bfcl", "agentic_json_mode"],
    "creative": None,
}
# DSpark / DFlash on (tau - 1), Qwen3-8B, gamma 7, T = 1 (arXiv 2607.05147 Table 1)
DSPARK_T1 = {"GSM8K": (5.33, 6.17), "MATH": (4.91, 5.78), "AIME25": (4.07, 5.01), "MBPP": (4.36, 5.16),
             "HumanEval": (4.64, 5.52), "LiveCodeBench": (4.39, 5.17), "MT-Bench": (3.11, 3.72),
             "Alpaca": (2.98, 3.58), "Arena-Hard": (2.81, 3.21)}


def gain(name):
    d, s = DSPARK_T1[name]
    return (s - 1) / (d - 1)


DSPARK_CLASS_GAIN = {
    "chat": gain("MT-Bench"),
    "reasoning": (gain("MATH") + gain("AIME25")) / 2,
    "coding": (gain("HumanEval") + gain("MBPP") + gain("LiveCodeBench")) / 3,
    "long_agentic": min(gain(k) for k in DSPARK_T1),          # not in the paper: its smallest gain
    "assistant_structured": min(gain(k) for k in DSPARK_T1),
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def taus():
    b = json.loads(ACCEPT.read_text())["blocks"]
    out = {1: {c: 1.0 for c, w in CLASSES.items() if w}}
    for B, v in b.items():
        w = v["workloads"]
        out[int(B)] = {c: sum(w[x]["tau_direct"] for x in ws) / len(ws) for c, ws in CLASSES.items() if ws}
    return dict(sorted(out.items()))


# ---- cycle model --------------------------------------------------------------------------------------------
def ceil_div(a, b):
    return -(-a // b)


def attention(p, m_attn):
    reps = ceil_div(p, m_attn)
    ret = ceil_div(ATTN_RET_BITS * p, LINK_BITS) - ceil_div(ATTN_RET_BITS, LINK_BITS)
    return ATTN_TOTAL + (reps - 1) * (ATTN["K"] + ATTN["V"]) + (p - 1) * ATTN_Q_SERIAL + ret


def layer(p, m=1, m_attn=1, ar="widened", su="serial"):
    """One target-shaped layer over p positions."""
    reps = ceil_div(p, m)
    me = (reps - 1) * (sum(ME_ISSUE.values()) + len(ME_ISSUE) * ISSUE_GAP)
    su_add = (p - 1) * SU_PER_POS
    if su == "overlap":                       # SU chases the ME: per stage the larger of the two
        su_add = max(0, su_add - me)
    if ar == "existing":                      # one 256-word descriptor per position, serialised
        ar_add = 2 * (p - 1) * AR_ONESTREAM
    else:                                     # one stream of 256p words
        ar_add = 2 * (p - 1) * AR_WORDS
    return BODY + 2 * AR_ONESTREAM + attention(p, m_attn) + me + su_add + ar_add


def head(p, m=1):
    return HEAD_MEASURED + (ceil_div(p, m) - 1) * (HEAD_ISSUE + ISSUE_GAP)


def ar_token():
    return L * layer(1) + NONLAYER


def draft(B, tau, cfg, method):
    if B == 1:
        return 0
    m, m_attn, ar, su, home = cfg["m"], cfg["m_attn"], cfg["ar"], cfg["su"], cfg["drafter_home"]
    tc = max(1, round(tau))
    fc = FC_FIXED + tc * (FC_ISSUE_PER_POS + DKV_ISSUE_PER_POS) + AR_ONESTREAM + (tc - 1) * AR_WORDS
    if home == "rom":
        layers = DRAFT_LAYERS * layer(B, m, m_attn, ar, su)
    else:                                     # weights streamed from attached HBM, MACs on near-HBM lanes
        stream = math.ceil(DRAFT_LAYER_BYTES / HBM_BPS_PER_DIE * CLOCK)
        macs = math.ceil(DRAFT_LAYER_BYTES * B / NEARHBM_LANES)
        fc = max(fc, math.ceil(4096 * 5 * 4096 / 4 / HBM_BPS_PER_DIE * CLOCK))
        layers = DRAFT_LAYERS * (max(stream, macs) + layer(B, m, m_attn, ar, su) - BODY)   # streamed matvecs replace the ROM body; SU, AR and attention stay
    lm = HEAD_MEASURED + (ceil_div(B - 1, m) - 1) * (HEAD_ISSUE + ISSUE_GAP)
    extra = (B - 1) * DSPARK_SERIAL_PER_SLOT if method == "dspark" else 0
    return fc + layers + lm + extra


def step(B, tau, cfg, method):
    v = L * layer(B, cfg["m"], cfg["m_attn"], cfg["ar"], cfg["su"]) + head(B, cfg["m"]) + NONLAYER - HEAD_MEASURED
    d = draft(B, tau, cfg, method)
    return dict(draft=d, verify=v, commit=COMMIT if B > 1 else 0, total=d + v + (COMMIT if B > 1 else 0))


def area(cfg, method):
    a = 0.0
    if cfg["drafter_home"] == "rom":
        a += AREA["drafter_rom_model"]
    if method == "dspark":
        a += AREA["dspark_markov_head_rom"] if cfg["drafter_home"] == "rom" else 0.0
    a += (cfg["m"] - 1) * AREA["me_lanes_per_extra_m"]
    a += (cfg["m_attn"] - 1) * AREA["attn_lanes_per_extra_m"]
    a += AREA["widened_ar_count"] if cfg["ar"] == "widened" else 0.0
    return round(a, 2)


def fits(cfg, method):
    """Tile-field items (drafter ROM, ME lanes) take the 23.0 mm2 margin; attention engines may take the
    shoreline free area (20.29) first."""
    field = (AREA["drafter_rom_model"] if cfg["drafter_home"] == "rom" else 0) + \
        (cfg["m"] - 1) * AREA["me_lanes_per_extra_m"] + \
        (AREA["dspark_markov_head_rom"] if method == "dspark" and cfg["drafter_home"] == "rom" else 0)
    field_lo = field - (AREA["drafter_rom_model"] - AREA["drafter_rom_r2_macros"] if cfg["drafter_home"] == "rom" else 0)
    attn = (cfg["m_attn"] - 1) * AREA["attn_lanes_per_extra_m"]
    spill = max(0.0, attn - BUDGET["shoreline_free"])
    return dict(tile_field_mm2=round(field, 2), tile_field_mm2_r2_macro_count=round(field_lo, 2),
                shoreline_mm2=round(attn - spill, 2), margin_used_mm2=round(field + spill, 2),
                fits_r2=field + spill <= BUDGET["margin_to_815"],
                fits_r2_with_r2_macro_count=field_lo + spill <= BUDGET["margin_to_815"])


CONFIGS = {
    # existing RTL path: no new hardware but per-position DYN offsets; serial AR descriptors; selected attention
    "existing_rtl_m1": dict(m=1, m_attn=1, ar="existing", su="serial", drafter_home="rom"),
    "m1_widenedAR": dict(m=1, m_attn=1, ar="widened", su="serial", drafter_home="rom"),
    "m1_widenedAR_attn2": dict(m=1, m_attn=2, ar="widened", su="serial", drafter_home="rom"),
    "m1_widenedAR_attn2_overlap": dict(m=1, m_attn=2, ar="widened", su="overlap", drafter_home="rom"),
    "m1_widenedAR_attn4": dict(m=1, m_attn=4, ar="widened", su="serial", drafter_home="rom"),
    "m1_widenedAR_attn4_overlap": dict(m=1, m_attn=4, ar="widened", su="overlap", drafter_home="rom"),
    "m2_widenedAR_attn2": dict(m=2, m_attn=2, ar="widened", su="serial", drafter_home="rom"),
    "m2_widenedAR_attn2_overlap": dict(m=2, m_attn=2, ar="widened", su="overlap", drafter_home="rom"),
    "m4_widenedAR_attn4_overlap": dict(m=4, m_attn=4, ar="widened", su="overlap", drafter_home="rom"),
    "hbm_drafter_m1_widenedAR_attn2": dict(m=1, m_attn=2, ar="widened", su="serial", drafter_home="hbm"),
    "hbm_drafter_m1_widenedAR_attn2_overlap": dict(m=1, m_attn=2, ar="widened", su="overlap", drafter_home="hbm"),
}


def tau_for(method, cls, B, T):
    t = T[B][cls]
    if method == "dspark" and B > 1:
        t = min(B, 1 + (t - 1) * DSPARK_CLASS_GAIN[cls])
    return t


def price():
    T = taus()
    ar = ar_token()
    ar_rate = CLOCK / ar
    measured = [c for c, w in CLASSES.items() if w]
    missing = [c for c, w in CLASSES.items() if not w]
    res = {}
    for method in ("dflash", "dspark"):
        res[method] = {}
        for name, cfg in CONFIGS.items():
            rows = []
            for B in T:
                per = {}
                for c in measured:
                    tau = tau_for(method, c, B, T)
                    s = step(B, tau, cfg, method)
                    per[c] = dict(tau=round(tau, 4), step_cycles=s["total"], draft=s["draft"], verify=s["verify"],
                                  tokens_s=round(tau * CLOCK / s["total"], 1))
                rates = [per[c]["tokens_s"] for c in measured]
                blend5 = sum(rates) / len(rates)
                fill = min(rates)
                blend8 = (sum(rates) + fill * len(missing)) / (len(rates) + len(missing))
                harm5 = len(rates) / sum(1 / r for r in rates)
                rows.append(dict(block=B, classes=per, blended_5_measured=round(blend5, 1),
                                 blended_8_missing_at_min=round(blend8, 1), blended_5_equal_tokens=round(harm5, 1),
                                 speedup_5=round(blend5 / ar_rate, 4), speedup_8_pessimistic=round(blend8 / ar_rate, 4),
                                 envelope=[round(min(rates) / ar_rate, 4), round(max(rates) / ar_rate, 4)]))
            best = max(rows, key=lambda r: r["blended_5_measured"])
            res[method][name] = dict(config=cfg, area_added_mm2=area(cfg, method), fit=fits(cfg, method),
                                     sweep=rows, best_block=best["block"], best_speedup_5=best["speedup_5"],
                                     best_speedup_8_pessimistic=best["speedup_8_pessimistic"],
                                     best_envelope=best["envelope"], best_tokens_s=best["blended_5_measured"])
    return T, ar, res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--burst-gate", type=Path, default=OUT / "verify_burst_gate.json")
    a = ap.parse_args()
    T, ar, res = price()
    gate = json.loads(a.burst_gate.read_text()) if a.burst_gate.exists() else None
    rec = {
        "schema": "opentallas.qwen-rom-speculation-recheck.v1",
        "status": "MODEL_PRICED_PROPOSAL_NOT_ADOPTED",
        "question": "with the measured TP4 one-stream layer (3,930 cycles, mostly fixed latency), does DFlash or "
                    "DSpark now beat AR on the Qwen3-8B ROM die, and at what area?",
        "prior_decision": "USER 2026-09-29: Qwen ROM die AR only; drafter excluded from ROM "
                          "(results/speculative/dflash_step_timing.json: m=1 never beats AR)",
        "basis": dict(clock_hz=CLOCK, layers=L, body=BODY, ar_onestream=AR_ONESTREAM, ar_fixed=AR_FIXED,
                      attention_nearhbm=ATTN, nonlayer=NONLAYER, layer_ar=layer(1), token_ar_cycles=ar,
                      ar_tokens_s=round(CLOCK / ar, 1)),
        "increment_per_extra_position_per_layer": dict(
            me_issue=ME_ISSUE, me_issue_total=sum(ME_ISSUE.values()), issue_gap_per_op=ISSUE_GAP,
            su_write_throughput=SU_PER_POS,
            allreduce_existing_rtl=2 * AR_ONESTREAM, allreduce_widened_count=2 * AR_WORDS,
            attention_m_attn_1=attention(2, 1) - attention(1, 1), attention_m_attn_ge_p=attention(2, 2) - attention(1, 1),
            head_issue=HEAD_ISSUE,
            layer_increment=dict(existing_rtl=layer(2, ar="existing") - layer(1),
                                 widened_ar=layer(2) - layer(1),
                                 widened_ar_attn2=layer(2, m_attn=2) - layer(1),
                                 widened_ar_attn2_overlap=layer(2, m_attn=2, su="overlap") - layer(1),
                                 m2_widened_ar_attn2_overlap=layer(2, m=2, m_attn=2, su="overlap") - layer(1)),
            layer_ar=layer(1),
            prior_record_claim="weight issue ~36% of the step; measured issue is 512 of 3,930 (13.0%), of 5,543 at 8K (9.2%)"),
        "rtl_multi_position_support": {
            "matrix_engine": "ot_qwen_w12_matvec / ot_qwen_me_array_w12 has NO multi-column mode: each issue cycle "
                             "multiplies one weight word by ONE x element per group; the IL = 8 slots are 8 output "
                             "row-words (mmode 0).  The (j >> jsh) weight-word sharing with x linear in j exists for "
                             "KV-sourced attention (mmode 1), not for INT8 matrices with a row scale.",
            "back_to_back": "ready = !active && !pend: the issue loop takes the next op the cycle after its last "
                            "element; the core issues independent ME ops at a 1-cycle gap "
                            "(ot_hdc_core_vector_weight.sv).  P positions of one projection are P back-to-back "
                            "descriptors: fill + wire + tree paid once, issue paid P times.",
            "burst_gate": gate and {k: gate[k] for k in ("status", "engine", "negative_control_rejected")} | {
                "rows": [{k: r.get(k) for k in ("case", "P", "issue_cycles", "spacing_min", "solo_latency",
                                                 "burst_span", "increment_per_position", "passed")}
                         for r in gate["rows"]]},
            "b16_note": "tools/uarch_model.py SM_ELEM['qwen'] cols = 16 ('16 columns = the DFlash b16 verify block') "
                        "is the GPU-organised HBM comparator's SM element, not the ROM tile; it is not in ROM RTL.",
            "m5_verify_array": "rtl/hdc/ot_hdc_qwen_m5_verify_array.sv: 5 position lane sets sharing one ROM word "
                               "(the lane multiplier m = 5); standalone, not in the W12 runtime.",
            "missing_for_a_verify_layer": [
                "per-position DYN offsets (RoPE row, KV write slot, context length) for back-to-back copies",
                "causal in-block attention on the near-HBM unit (position i sees the block's positions < i)",
                "all-reduce of 256p words: the 8-bit descriptor count and the one-descriptor-at-a-time TP sequencer",
                "lm_head argmax per position and the accept/commit path (rtl/hdc/ot_hdc_accept.sv exists)"]},
        "acceptance": {"source": str(ACCEPT.relative_to(ROOT)), "sha256": sha(ACCEPT),
                       "classes": CLASSES, "missing_classes": [c for c, w in CLASSES.items() if not w],
                       "tau_by_block_class": {str(B): {c: round(t, 4) for c, t in v.items()} for B, v in T.items()},
                       "grade": "MEASURED greedy BF16 HF reference dflash_generate run at each block "
                                "(drafter trained at block 16)",
                       "dspark": {"source": "arXiv 2607.05147 Table 1, Qwen3-8B, gamma 7, T = 1",
                                  "dflash_vs_dspark_tau": DSPARK_T1,
                                  "class_gain_on_tau_minus_1": {k: round(v, 4) for k, v in DSPARK_CLASS_GAIN.items()},
                                  "grade": "DERIVED: our measured DFlash tau(B) with (tau - 1) scaled by the paper's "
                                           "DSpark/DFlash ratio per class (agentic/assistant: the paper's smallest "
                                           "ratio); temperature 1 in the paper vs greedy here; capped at B"}},
        "area_mm2_per_die": AREA, "floorplan_budget_r2": BUDGET,
        "results": res,
        "sources_sha256": {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), ACCEPT]},
        "claim_boundary": "Analytical pricing on measured per-layer terms.  Measured: the one-stream layer, the "
                          "all-reduce, su_writes, the burst gate (ME issue, reduced GT).  Modelled: near-HBM "
                          "attention, the p-position SU overlap, the widened all-reduce, the drafter step, the "
                          "DSpark sequential term (ASSUMED 1,000/slot), areas.  No verify layer has run in RTL.",
    }
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "pricing.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("AR", ar, round(CLOCK / ar, 1))
    for m in res:
        for n, r in res[m].items():
            print(f"{m:7s} {n:42s} B={r['best_block']:2d} x{r['best_speedup_5']:.3f} (8-cls pess x{r['best_speedup_8_pessimistic']:.3f}) "
                  f"env {r['best_envelope']} area {r['area_added_mm2']} fit {r['fit']['fits_r2']}/{r['fit']['fits_r2_with_r2_macro_count']}")


if __name__ == "__main__":
    main()
