#!/usr/bin/env python3
"""HBM inference ACCELERATOR study (user decision 2026-10-03): the priced improvement ladder on top of the
GPU-organised HBM comparator (kept as the ablation), for DeepSeek-V4.1-Flash (1M and 200K), Qwen3-8B (8K) and a
quick Qwen3.8-27B row, plus the composed best design against the ablation, real GPUs and the ROM designs.

MODEL ONLY.  No RTL, no P&R, no inference.  Every input is a committed record (sha256 pinned below where it is in
this tree) or a branch record cited by commit; every ASSUMED constant is labelled.  The rungs are additive us
deltas on the W19 composed token (the selected HBM_W19 authority in tools/uarch_model.py), applied per verify width
P from the speculation branch's measured-union compositions.  Run:

    python3 results/uarch/hbm_accelerator_study_20261003/ladder_model.py  [--out ladder.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

# --------------------------------------------------------------------------------------------------------------
# Inputs (sources inline).  B = branch-only record cited by commit; T = in-tree record (sha256 pinned at run time).
# --------------------------------------------------------------------------------------------------------------
F_FAST = 1.2e9                     # streaming domain (AGENTS.md clock target)
F_SER = 0.9e9                      # serial-chain domain (AGENTS.md clock domains)

# W19 fused composed AR token, TP-96, 1M (B: claude/w19-hbm-token 71b3ffc52
# results/uarch/w19_hbm_token_ar_fused_wsel256.json result.parts_us; = HBM_W19 in tools/uarch_model.py)
W19_AR = dict(sm=70.58, barrier=22.29, collective=240.46, local=103.48, fetch=5.33)
W19_COLL_COUNT = dict(total=265, all_reduce=40, gather_like=225)   # 32 x 6 + 8 x 9 + head 1; o-group AR x 40
W19_COLL_FIT = dict(ar_fixed_cyc=988.74, ag_fixed_cyc=932.8, hz=1200480192.08,    # w15_hbm_nvls.json hbm_p48_ss(_prod)
                    src="W19 record result.collective_model (W15b P=48 NVLS fits)")
W19_BOUNDARY_CYC = 78               # 62 measured barrier + 16 x-broadcast tail (results/rtl/gpu_supply_barrier.json)
W19_BARRIER_ARRIVE_CYC, W19_BARRIER_RELEASE_CYC = 32, 31     # hbm_gpu.json designs.v41.barrier (floorplan-derived)

# Verify passes with the MEASURED expert union, P = 1..6 (B: claude/v41-hbm-speculation-20261003 d2aff19ef
# results/speculative/v41_hbm_speculation_methods_20261003/v41_hbm_speculation_methods.json
# contexts.1048576.verify_by_P.*.parts_measured_us); P = 1 is the W19 AR token.
VERIFY_PARTS = {
    1: W19_AR,
    2: dict(sm=82.3, barrier=22.29, collective=256.34, local=122.71, fetch=14.69),
    3: dict(sm=92.55, barrier=22.29, collective=275.8, local=141.94, fetch=20.12),
    4: dict(sm=101.88, barrier=22.29, collective=291.47, local=161.18, fetch=25.07),
    5: dict(sm=110.39, barrier=22.29, collective=310.93, local=180.41, fetch=29.57),
    6: dict(sm=118.32, barrier=22.29, collective=326.81, local=199.64, fetch=33.78),
}
DRAFT_PARTS = dict(sm=9.59, barrier=2.04, collective=23.89, local=14.86, fetch=1.49)   # 51.88 us, same record
CTX_200K_RATIO = 441.3 / 442.14     # same record contexts.200000.ar_us / 1M ar_us (index scan candidate-capped)
TAU = {   # same record rates.* (mixed n36 = repository headline 3.649; agentic pilots = exact replay)
    "mixed_n36": {1: 1.8187, 2: 2.4684, 3: 2.9653, 4: 3.3431, 5: 3.6486},
    "agentic_multiturn": {1: 1.9042, 2: 2.6629, 3: 3.225, 4: 3.7487, 5: 4.0222},
    "agentic_all5_n30": {1: 1.9382, 2: 2.7736, 3: 3.469, 4: 4.1126, 5: 4.5554},
}

# Service-term review (/tmp/claude-review-20261003/dshbm_term/dshbm_service_term.json; in-tree copy
# results/uarch/v41_hbm_service_term_20261003/): routed-expert first access after top-6, ns.
FETCH_NS = dict(postponed=133.2, central=469.5, high=526.4)        # results/rtl/w19_expert_fetch.json exposed_ns
FETCH_CDC_NS = 6.4                                                  # v41_link_cdc_campaign.json, 2 crossings
FETCH_STALL_NS = 0.1                                                # M/D/1 central
SERVICE_CYC_PER_BOUNDARY = 4                                        # ACK 2 + fence 1 + owner compare 1 (central)
ROUTED_FETCHES = 40

GPU_GRID_SYNC_NS = 1430.0          # V100 cooperative-groups grid sync (IPDPS 2020), uarch_model GPU dict
# Measured link/collective constants transferable to the accelerator (B: claude/dsrom-c5hc-adopt-20261003 4ec2eef0e
# results/rtl/dsrom_c5hc_collective_gate_20261003/REPLAY.md, cycles at 0.834 ns): C1 board-link gather fixed 252 cyc,
# reduce fixed 265 cyc; in-package UCIe relay step +~100 cyc (82-86 hub-to-hub).
C1_GATHER_NS = 252 * 0.834
C1_REDUCE_NS = 265 * 0.834
INPKG_STEP_NS = 100 * 0.834
# Qwen measured collective improvements (B: claude/qwen-async-collective-20261003 839bab031, measured.json
# per_layer: cut-through only -148 cycles/layer over the layer's two all-reduces at the Qwen ROM clock 1.09864 GHz)
CUT_THROUGH_NS_PER_COLL = 148 / 2 / 1.09864
H5_EPILOGUE_US = dict(ar=6.1, mtp6=11.8, ar_high=11.6,
                      src="FA claude/fusion-audit a86b17cd (H5 on W19's program); W13b f984ba8d 11.6 us AR (high)")
SELECT_CYC = 419                    # W15b wide 96x512 select, measured (claude/w15-ss 082f11b2); P positions in series
INDEX_LAYERS = 8
# Index scan per die: 262,144 compressed keys / 96 dies at NK = 4 keys a cycle (W19 local rule) -> per-stack scorers
IDX_KEYS_DIE = 262144 / 96
SHARED_EXPERT_HIDE_US = 40 * 2 * (64 + 95) / F_FAST * 1e6   # shared expert w1/w3 ahead of routed slots: 2 ops a layer
                                                            # (group-slot 64 issue + 95 drain), ASSUMED from sm_op_cycles
SERIAL_SHARE_OF_LOCAL = 0.75        # ASSUMED from W19 dedicated.node_parts (serial nodes ~3/4 of a layer's local ns)
SERIAL_FAST_HZ = 1.091e9            # FP32 add pipe with ADDER_MAP off, SS (memory: orfs-asap7-adder-map; to re-measure)

# DS power (T: results/uarch/economics.json v41_hbm; consolidation.json hbm.v41_sweep TP-96 4-stack row)
DS_HBM_DYN_J = (10593.0 - 6498.5) / 2801.8      # dynamic J/token at the record's rate
DS_HBM_STATIC_GATED_W = (3.16764 - DS_HBM_DYN_J) * 3145.9   # from the sweep's gated mJ at its model rate
HBM_IDLE_W_STACK = 2.8              # technology.json power.memory_interface_idle_w_per_stack (assumed)
DRAM_MM2_PER_STACK = dict(central=1000.0, low=900.0, high=1450.0,
                          basis="ASSUMED: 8-Hi 24 GB HBM3E = 8 core dies of ~110 mm2 + ~110 mm2 base die (12-Hi ~1,450)")

# Qwen3-8B (T: results/uarch/hbm_gpu.json, economics.json; uarch_model GPU_FIT)
Q_W_B, Q_KV8K_B = 7.568e9, 0.604e9               # INT8/FP8 weights, FP8 KV at 8K (GPU_FIT)
Q_LMHEAD_B = 151936 * 4096                      # 8-bit lm_head, read by the draft and the verify of a DFlash step
Q_DRAFTER_B = 1.05e9                            # z-lab Qwen3-8B-DFlash-b16 at 8 bits (hbm_speculation_rows)
Q_TAU_B16 = 3.6559                              # results/speculative/dflash_block_acceptance.json (lab mix)
Q_TAU_PAPER = dict(humaneval=6.50, math500=8.01)
Q_STACK_TBPS_ASSUMED, Q_STACK_TBPS_MEASURED = 0.9, 0.958   # B: claude/qwen-hbm-sustained-bw-20261003 52ce3e9c1
Q_ABL_BOUNDARY_US = 0.3                         # 154 exposed cycles over the stream (hbm_gpu.json) at 1.0986 GHz
Q_DFLASH_BOUNDARY_US = 2 * 12 * 64 / 1.09864e9 * 1e6
GPU_FIXED_S_QWEN = 1.46395e-3                   # GPU_FIT fixed_seconds_qwen (launch+sync, 36 layers; H200 NIM fit)
B200_S_PER_B = (1 / 230.0 - GPU_FIXED_S_QWEN) / (2 * Q_W_B)   # fitted so BF16 reproduces 230 tok/s (DFlash paper)
E_HBM_J_B = 104.88e-12                          # technology.json energy.hbm_j_per_byte (measured, A100 SC'25)
E_SRAM_J_B = 2.6e-12
SRAM_MM2_PER_MB = 94.824 * 41.04 / 4096 * 1024 * 1.31 / 1e6 * 1024   # 128x256 macro, x1.31 pack -> mm2 per MiB
SRAM_W_PER_MM2 = 0.005 + 8.5e-11 * F_FAST * 0.15  # leakage + clock (uarch_model _static_w convention)
Q_DIE_RIGHT_MM2, Q_DIE_FULL_MM2 = 265.8, 815.0    # consolidation.json hbm.right_sized.qwen_4; W5 die
Q_HBM_STATIC_W_2DIE = 22.52 + 23.81             # economics.json qwen_hbm.energy.static_w (clock + leakage, 2 dies)
Q_ROM = dict(calibrated=2793.0, near_hbm=5237.0, dyn_J=0.076586, static_W=200.0, dies=4, die_mm2=815.0, stacks=16,
             src="docs/HEADLINE_BUNDLE_SCOPE.md (qwen_rom_calibrated_calendar_20261003 summary-r1.json, model only); "
                 "economics.json qwen_rom.energy")


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def T(parts):
    return sum(parts.values())


# --------------------------------------------------------------------------------------------------------------
# DeepSeek-V4.1 ladder
# --------------------------------------------------------------------------------------------------------------
def ds_rungs(P, include_conditional=True, topology="central"):
    """Ordered rungs as (id, us saved on a verify pass of width P (P = 1: AR), note).  Positive = saving."""
    base = VERIFY_PARTS[P]
    n_b = base["barrier"] / (W19_BOUNDARY_CYC / F_FAST * 1e6)       # boundaries on the path (~343)
    rungs = []
    # R0c: the ablation made honest (service term central): +fetch first access with refresh live, +boundary service
    corr = ROUTED_FETCHES * (FETCH_NS["central"] + FETCH_CDC_NS + FETCH_STALL_NS - FETCH_NS["postponed"]) * 1e-3
    svc = n_b * SERVICE_CYC_PER_BOUNDARY / F_FAST * 1e6
    rungs.append(("R0c", -(corr + svc), "service term central (refresh-live first access + ACK/fence/owner)"))
    # R1b dataflow completion: consumers wait on a local arrival (tx-count) counter; no release broadcast
    rungs.append(("R1b", n_b * W19_BARRIER_RELEASE_CYC / F_FAST * 1e6, "tx-count arrival, release broadcast removed"))
    # R2 direct die-to-die topology (2-level, measured C1 hop + in-package step) instead of the 668-ns switch hop
    if topology == "central":
        ag_new = INPKG_STEP_NS + 2 * C1_GATHER_NS
        ar_new = 2 * INPKG_STEP_NS + 2 * C1_REDUCE_NS
    else:   # optimistic: a light-FEC switch with in-switch reduction, 2 x 130 ns link + 100 ns core (ASSUMED)
        ag_new = ar_new = 2 * 130 + 100 + 40
    ag_old = W19_COLL_FIT["ag_fixed_cyc"] / W19_COLL_FIT["hz"] * 1e9
    ar_old = W19_COLL_FIT["ar_fixed_cyc"] / W19_COLL_FIT["hz"] * 1e9
    r2 = (W19_COLL_COUNT["gather_like"] * (ag_old - ag_new) + W19_COLL_COUNT["all_reduce"] * (ar_old - ar_new)) * 1e-3
    rungs.append(("R2", r2, f"AG fixed {ag_old:.0f}->{ag_new:.0f} ns, AR {ar_old:.0f}->{ar_new:.0f} ns"))
    # R3a cut-through injection/consumption (measured Qwen analogue per collective); R3b H5 epilogue (GPU-real)
    rungs.append(("R3a", W19_COLL_COUNT["total"] * CUT_THROUGH_NS_PER_COLL * 1e-3, "cut-through collective"))
    h5 = H5_EPILOGUE_US["ar"] + (P - 1) / 5 * (H5_EPILOGUE_US["mtp6"] - H5_EPILOGUE_US["ar"])
    rungs.append(("R3b", h5, "TMEM-style register epilogue (norm partials, quantise, residual)"))
    # R4b per-stack index scorers: 4 stacks x NK 4 keys/cycle instead of NK 4 per die (keys read once per pass)
    r4 = INDEX_LAYERS * (IDX_KEYS_DIE / 4 - IDX_KEYS_DIE / 16) / F_FAST * 1e6
    rungs.append(("R4b", r4, "per-stack index scorers + local top-k chase"))
    # R5a refresh-aware streaming controller (REFpb + notice): first access back to the postponed figure
    rungs.append(("R5a", corr - ROUTED_FETCHES * FETCH_CDC_NS * 1e-3, "refresh-aware routed fetch"))
    # R5b shared-expert-first issue: the routed fetch (and part of the union stream) hides under the shared expert
    fetch_left = base["fetch"] + ROUTED_FETCHES * FETCH_CDC_NS * 1e-3
    rungs.append(("R5b", min(fetch_left, SHARED_EXPERT_HIDE_US), "shared expert issued first; routed fetch overlaps"))
    # R6a one select unit per verify position (W15b select replicated P times)
    rungs.append(("R6a", (P - 1) * SELECT_CYC * INDEX_LAYERS / F_FAST * 1e6, "P parallel 96x512 select units"))
    # R7a serial-chain domain at 1.091 GHz (LAT 3) instead of 0.9 GHz -- CONDITIONAL on SS closure of the ratio FIFO
    if include_conditional:
        rungs.append(("R7a", base["local"] * SERIAL_SHARE_OF_LOCAL * (1 - F_SER / SERIAL_FAST_HZ),
                      "serial chain 0.9 -> 1.091 GHz (conditional)"))
    return rungs


def ds_pass_us(P, upto=None, **kw):
    t = T(VERIFY_PARTS[P])
    out = [("W19", t)]
    for rid, s, _ in ds_rungs(P, **kw):
        t -= s
        out.append((rid, t))
        if rid == upto:
            break
    return out


def ds_draft_us(**kw):
    d = dict(DRAFT_PARTS)
    coll_frac = (ds_rung(1, "R2", **kw) + ds_rung(1, "R3a", **kw)) / W19_AR["collective"]
    d["collective"] *= 1 - coll_frac
    d["barrier"] *= (W19_BOUNDARY_CYC - W19_BARRIER_RELEASE_CYC) / W19_BOUNDARY_CYC
    if kw.get("include_conditional", True):
        d["local"] *= 1 - SERIAL_SHARE_OF_LOCAL * (1 - F_SER / SERIAL_FAST_HZ)
    return T(d)


def ds_rung(P, rid, **kw):
    return {r: s for r, s, _ in ds_rungs(P, **kw)}[rid]


def ds_spec(pass_fn, draft_us, tau_set):
    best = None
    rows = []
    for g in range(1, 6):
        step = pass_fn(g + 1) + draft_us
        r = TAU[tau_set][g] * 1e6 / step
        rows.append(dict(gamma=g, step_us=round(step, 2), tau=TAU[tau_set][g], tokens_s=round(r, 1)))
        if best is None or r > best["tokens_s"]:
            best = rows[-1]
    return dict(rows=rows, best=best)


RUNG_META = {
    "R0": dict(name="GPU-faithful sync (grid barrier per dependent op, persistent kernel)", kind="GPU-standard",
               exactness="none (timing)", risk="-", deps="-", cost="-"),
    "R0c": dict(name="Ablation made honest: refresh-live routed fetch + ACK/fence/owner service (central)",
                kind="correction", exactness="n/a", risk="-", deps="-", cost="-"),
    "R1": dict(name="One statically scheduled persistent program + hardware barrier network (62 cyc measured)",
               kind="partly GPU-standard (persistent kernels / CUDA graphs); die-wide 62-cycle barrier is OURS",
               exactness="class A (no arithmetic change)", risk="low (measured tb_gpu_barrier)",
               deps="already in the comparator", cost="barrier tree, <0.1 mm2/die"),
    "R1b": dict(name="Dataflow completion: tx-count arrival counters (mbarrier-style), no release broadcast",
                kind="GPU-derived (Hopper mbarrier/TMA tx-count), extended die-wide", exactness="class A",
                risk="low", deps="W4 RF ACK identity, W6 visibility fence", cost="~32 counters/SM, negligible"),
    "R2": dict(name="Direct die-to-die links, 2-level topology (groups of 16 dies fully connected + global links)",
               kind="OURS (vs NVLink switch); link = ROM array's light-FEC board link", exactness="class A "
               "(fixed-order tree, same as NVLS record)", risk="medium: port count 20/die, endpoint fan-in 15",
               deps="link PHY sizing; C1 measured hop", cost="~40 SerDes lanes/die at <= the NVLS port's lane count"),
    "R3a": dict(name="Cut-through collectives: SM rows injected as drained, consumers start on arrival (levels 2/3/5)",
                kind="OURS (measured on the Qwen ROM path, d79a2089c)", exactness="class A",
                risk="low-medium (async gate passed on Qwen; SS not closed)", deps="R2 endpoint",
                cost="endpoint FIFO + credit, ~0.01 mm2/die"),
    "R3b": dict(name="Register/TMEM epilogue fusion (norm partials, block quantise, residual add)",
                kind="GPU-standard (Blackwell TMEM epilogue)", exactness="class A if golden order kept "
                "(two Qwen fused-epilogue gates FAILED: non-finite, wide overflow)", risk="medium",
                deps="-", cost="1.37 mm2/die (W13b)"),
    "R4b": dict(name="Near-memory index scan: one scorer per HBM stack + per-stack top-k chase", kind="OURS",
                exactness="class A (top-k of per-stack top-k)", risk="low", deps="streaming controller",
                cost="3 extra scorer slices/die (~0.3 mm2, ASSUMED)"),
    "R5a": dict(name="Refresh-aware streaming HBM controller (REFpb + notice) on the routed-expert fetch",
                kind="OURS (measured 0.958 TB/s/stack bench)", exactness="class A (no data change)",
                risk="medium: closes 976.6 MHz SS, -4.7 ps at 1.2 GHz", deps="r14 stream_pc/stack",
                cost="0.151 mm2/stack"),
    "R5b": dict(name="Shared expert issued before routed slots; routed fetch overlaps it", kind="OURS (compiler)",
                exactness="class A (sum order unchanged: routed in id order then shared)", risk="low",
                deps="W19 executor program order", cost="none"),
    "R6a": dict(name="Speculation: one 96x512 select unit per verify position", kind="OURS",
                exactness="class A", risk="low", deps="ot_coll_topk_merge", cost="5 extra select units/die (small)"),
    "R7a": dict(name="Serial chain at 1.091 GHz LAT-3 (adder map off) instead of 0.9 GHz", kind="OURS",
                exactness="class A", risk="HIGH: ratio FIFO fails SS -75.6 ps; serial units unmeasured at 1.091",
                deps="2-clock CDC fix (shared with ROM lane)", cost="none (re-timing)"),
}


def build_ds():
    out = {}
    for ctx, k in (("1M", 1.0), ("200K", CTX_200K_RATIO)):
        res = {}
        for cond in (False, True):
            tag = "with_R7a" if cond else "firm"
            lad = []
            t_gpuf = T(W19_AR) + (W19_AR["barrier"] / (W19_BOUNDARY_CYC / F_FAST * 1e6)) * (
                GPU_GRID_SYNC_NS * 1e-3 - W19_BOUNDARY_CYC / F_FAST * 1e6)
            lad.append(dict(rung="R0", ar_us=round(t_gpuf * k, 2), ar_tok_s=round(1e6 / (t_gpuf * k), 1)))
            lad.append(dict(rung="R1 (= W19 ablation as recorded)", ar_us=round(T(W19_AR) * k, 2),
                            ar_tok_s=round(1e6 / (T(W19_AR) * k), 1), saved_us=round((t_gpuf - T(W19_AR)) * k, 2)))
            rr1 = ds_rungs(1, include_conditional=cond)
            rr6 = ds_rungs(6, include_conditional=cond)
            t1, t6 = T(VERIFY_PARTS[1]), T(VERIFY_PARTS[6])
            for (rid, s1, note), (_, s6, _) in zip(rr1, rr6):
                t1 -= s1
                t6 -= s6
                lad.append(dict(rung=rid, saved_ar_us=round(s1 * k, 2), saved_verify6_us=round(s6 * k, 2),
                                ar_us=round(t1 * k, 2), ar_tok_s=round(1e6 / (t1 * k), 1),
                                verify6_us=round(t6 * k, 2), note=note,
                                pct_of_rate=round(100 * s1 / (t1 + s1), 2)))

            def pass_fn(P, cond=cond):
                return ds_pass_us(P, include_conditional=cond)[-1][1] * k

            dr = ds_draft_us(include_conditional=cond) * k
            spec = {s: ds_spec(pass_fn, dr, s) for s in TAU}
            abl_spec = {s: ds_spec(lambda P: T(VERIFY_PARTS[P]) * k, T(DRAFT_PARTS) * k, s) for s in TAU}
            res[tag] = dict(ladder=lad, best_ar_us=round(pass_fn(1), 2), best_ar_tok_s=round(1e6 / pass_fn(1), 1),
                            draft_us=round(dr, 2), spec=spec, ablation_spec=abl_spec,
                            tau4_gamma5_tok_s=round(4.0e6 / (pass_fn(6) + dr), 1),
                            ablation_tau4_gamma5_tok_s=round(4.0e6 / (T(VERIFY_PARTS[6]) * k + T(DRAFT_PARTS) * k), 1))
        out[ctx] = res
    # topology sensitivity (optimistic switch)
    t_opt = ds_pass_us(1, include_conditional=False, topology="optimistic")[-1][1]
    out["topology_optimistic_firm_ar_tok_s"] = round(1e6 / t_opt, 1)
    return out


# --------------------------------------------------------------------------------------------------------------
# Qwen3-8B ladder (bandwidth-bound: per-user = sustained stack bandwidth / bytes a token)
# --------------------------------------------------------------------------------------------------------------
def qwen_point(stacks, tbps_stack, sram_mb, weights=Q_W_B, kv=Q_KV8K_B, lmhead=Q_LMHEAD_B, drafter=Q_DRAFTER_B,
               tau=Q_TAU_B16, boundary_us=Q_ABL_BOUNDARY_US, dflash_boundary_us=Q_DFLASH_BOUNDARY_US):
    bw = stacks * tbps_stack * 1e12
    sram_b = sram_mb * 2 ** 20
    ar_bytes = weights + kv - min(sram_b, weights)
    t_ar = ar_bytes / bw * 1e6 + boundary_us
    # DFlash step: draft (drafter + lm_head over the draft slots) then verify (weights + KV + lm_head); SRAM holds the
    # lm_head first (read twice a step), then drafter/target bytes
    step_bytes = weights + kv + drafter + lmhead          # weights already include one lm_head read
    sram_saves = min(sram_b, lmhead) * 2 + max(0.0, sram_b - lmhead)
    t_df = (step_bytes - sram_saves) / bw * 1e6 + dflash_boundary_us
    return dict(ar_us=round(t_ar, 1), ar_tok_s=round(1e6 / t_ar, 1), ar_bytes=ar_bytes,
                dflash_step_us=round(t_df, 1), dflash_tok_s=round(tau * 1e6 / t_df, 1),
                dflash_step_bytes=step_bytes - sram_saves,
                dflash_tok_s_tau_humaneval=round(Q_TAU_PAPER["humaneval"] * 1e6 / t_df, 1),
                dflash_tok_s_tau_math500=round(Q_TAU_PAPER["math500"] * 1e6 / t_df, 1))


def qwen_power(pt, dies, die_mm2_logic_static, stacks, sram_mb, mode="ar"):
    sram_mm2 = sram_mb * SRAM_MM2_PER_MB
    static = Q_HBM_STATIC_W_2DIE * dies / 2 + stacks * HBM_IDLE_W_STACK + sram_mm2 * SRAM_W_PER_MM2
    if mode == "ar":
        e_dyn = pt["ar_bytes"] * E_HBM_J_B + min(sram_mb * 2 ** 20, Q_W_B) * E_SRAM_J_B
        rate = pt["ar_tok_s"]
        e_tok = e_dyn + static / rate
    else:
        e_step = pt["dflash_step_bytes"] * E_HBM_J_B + sram_mb * 2 ** 20 * E_SRAM_J_B
        rate = pt["dflash_tok_s"]
        e_tok = e_step / Q_TAU_B16 + static / rate
    return dict(static_w=round(static, 1), system_w=round(e_tok * rate, 1), J_per_token=round(e_tok, 4))


def build_qwen():
    abl = qwen_point(8, Q_STACK_TBPS_ASSUMED, 0)
    gpuf = dict(ar_us=round(abl["ar_us"] + GPU_FIXED_S_QWEN * 1e6, 1))
    gpuf["ar_tok_s"] = round(1e6 / gpuf["ar_us"], 1)
    q2 = qwen_point(8, Q_STACK_TBPS_MEASURED, 0)
    spare_same = 2 * (Q_DIE_FULL_MM2 - Q_DIE_RIGHT_MM2)               # B200-class package: 2 x 815 mm2 footprint
    sram_same = spare_same / SRAM_MM2_PER_MB
    q5 = qwen_point(8, Q_STACK_TBPS_MEASURED, sram_same)
    # iso total silicon with the ROM option C (4 x 815 mm2 logic + 16 stacks): 4 right-sized dies + 16 stacks + SRAM
    spare_iso = Q_ROM["dies"] * Q_ROM["die_mm2"] - 4 * Q_DIE_RIGHT_MM2
    sram_iso = spare_iso / SRAM_MM2_PER_MB
    iso = qwen_point(16, Q_STACK_TBPS_MEASURED, sram_iso)
    iso_nosram = qwen_point(16, Q_STACK_TBPS_MEASURED, 0)
    ladder = [
        dict(rung="Q0 GPU-faithful (kernel launch + sync, H200-NIM fixed 1.464 ms)", **gpuf),
        dict(rung="Q1 persistent program + hw barrier = GPU-organised ablation (2 dies, 8 stacks at 0.9 TB/s)",
             ar_us=abl["ar_us"], ar_tok_s=abl["ar_tok_s"], dflash_tok_s=abl["dflash_tok_s"]),
        dict(rung="Q2 refresh-aware streaming controller (0.958 TB/s/stack measured worst layer)",
             ar_us=q2["ar_us"], ar_tok_s=q2["ar_tok_s"], dflash_tok_s=q2["dflash_tok_s"]),
        dict(rung="Q3 one-stream / async collectives (TP-2 exchange)", ar_tok_s=q2["ar_tok_s"],
             note="0: hidden under the weight stream (154 cycles exposed); REJECTED below the 1% gate"),
        dict(rung="Q4 near-HBM attention", ar_tok_s=q2["ar_tok_s"],
             note="0: the KV bytes are still read from DRAM; REJECTED for a weight-streaming design"),
        dict(rung=f"Q5 SRAM residency on the same 2 x 815 mm2 footprint ({sram_same:.0f} MiB: lm_head first)",
             ar_us=q5["ar_us"], ar_tok_s=q5["ar_tok_s"], dflash_tok_s=q5["dflash_tok_s"],
             sram_mib=round(sram_same), sram_mm2=round(spare_same, 1)),
        dict(rung="Q6 DFlash b16 on the 16 MMA columns (tau 3.656 lab mix)", dflash_tok_s=q5["dflash_tok_s"],
             dflash_tok_s_tau_humaneval=q5["dflash_tok_s_tau_humaneval"],
             dflash_tok_s_tau_math500=q5["dflash_tok_s_tau_math500"]),
    ]
    p_abl = qwen_power(abl, 2, None, 8, 0)
    p_same = qwen_power(q5, 2, None, 8, sram_same)
    p_same_df = qwen_power(q5, 2, None, 8, sram_same, "dflash")
    p_iso = qwen_power(iso, 4, None, 16, sram_iso)
    p_iso_df = qwen_power(iso, 4, None, 16, sram_iso, "dflash")
    rom = {k: dict(tok_s=Q_ROM[k], J_per_token=round(Q_ROM["dyn_J"] + Q_ROM["static_W"] / Q_ROM[k], 4),
                   system_w=round(Q_ROM["dyn_J"] * Q_ROM[k] + Q_ROM["static_W"], 1)) for k in ("calibrated", "near_hbm")}
    # GPU rows
    b200_fp8 = GPU_FIXED_S_QWEN + B200_S_PER_B * (Q_W_B + Q_KV8K_B)
    h100_fp8 = GPU_FIXED_S_QWEN + B200_S_PER_B * 8.0 / 3.35 * (Q_W_B + Q_KV8K_B)
    gpus = [
        dict(gpu="1x B200, SGLang FA4, BF16, AR (DFlash paper Table 3, measured)", tok_s=230.0, tier=1),
        dict(gpu="1x B200, SGLang FA4, DFlash b16 Math500 tau 8.01 (measured)", tok_s=1175.0, tier=1),
        dict(gpu="1x B200, SGLang FA4, DFlash b16 HumanEval tau 6.50 (measured)", tok_s=955.0, tier=1),
        dict(gpu="1x H200, NIM FP8, AR (published)", tok_s=234.95, tier=1),
        dict(gpu="RTX PRO 6000 (this lab), vLLM FP8 AR / DFlash tau 3.72 (measured, shared GPU)", tok_s=151.4,
             dflash_tok_s=390.3, tier=1),
        dict(gpu="1x B200 FP8 8K (tier-2 calibrated)", tok_s=round(1 / b200_fp8, 1),
             dflash_tok_s_lab_mix=round(390.3 / 151.4 / b200_fp8, 1), tier=2, power_w=689.0,
             power_note="measured decode draw 689 W (567-994); TDP 1,000-1,200 W"),
        dict(gpu="1x H100 SXM FP8 8K (tier-2 MODELLED: B200 fit scaled to 3.35 TB/s; no measurement)",
             tok_s=round(1 / h100_fp8, 1), tier=2, power_w=700.0, power_note="H100 SXM TDP 700 W (published)"),
    ]
    return dict(ladder=ladder,
                same_silicon_as_ablation=dict(ar=q5, power_ar=p_same, power_dflash=p_same_df, sram_mib=round(sram_same)),
                ablation=dict(point=abl, power=p_abl),
                iso_total_silicon_with_rom=dict(point=iso, point_without_sram=iso_nosram, power_ar=p_iso,
                                                power_dflash=p_iso_df, sram_mib=round(sram_iso),
                                                logic_mm2=round(4 * Q_DIE_RIGHT_MM2 + spare_iso, 1)),
                rom=rom, gpus=gpus)


def build_qwen27():
    # ASSUMED Qwen3.8-27B: dense, 64 layers, hidden 5120, GQA 8 KV heads x 128 (Qwen3-32B-like); no config in repo
    w = 27.0e9
    kv = 2 * 64 * 8 * 128 * 8192
    lm = 151936 * 5120
    sram_iso = (Q_ROM["dies"] * Q_ROM["die_mm2"] - 4 * Q_DIE_RIGHT_MM2) / SRAM_MM2_PER_MB
    hbm16 = qwen_point(16, Q_STACK_TBPS_MEASURED, sram_iso, weights=w, kv=kv, lmhead=lm)
    hbm24 = qwen_point(24, Q_STACK_TBPS_MEASURED, sram_iso, weights=w, kv=kv, lmhead=lm)
    gpu = GPU_FIXED_S_QWEN * 64 / 36 + B200_S_PER_B * (w + kv)
    rom_us = 1e6 / Q_ROM["near_hbm"] * 64 / 36
    return dict(assumed_config="dense 27B, 64 layers, hidden 5120, 8 KV heads x 128, 8-bit weights, FP8 KV 8K",
                hbm_accel_16_stacks=hbm16, hbm_accel_24_stacks=hbm24,
                b200_fp8_tier2_tok_s=round(1 / gpu, 1),
                rom_near_hbm_scaled_tok_s=round(1e6 / rom_us, 1),
                rom_dies_scaled=math.ceil(Q_ROM["dies"] * w / Q_W_B),
                note="ROM row = Qwen3-8B near-HBM chain x 64/36 layers (ASSUMED scaling; ROM silicon ~x3.6)")


def silicon(logic_mm2, stacks, which="central"):
    return dict(logic_mm2=round(logic_mm2), stacks=stacks, dram_mm2=round(stacks * DRAM_MM2_PER_STACK[which]),
                total_mm2=round(logic_mm2 + stacks * DRAM_MM2_PER_STACK[which]))


def build_compare(ds, qw):
    firm, cond = ds["1M"]["firm"], ds["1M"]["with_R7a"]
    def ds_e(rate, stacks=384):
        st = DS_HBM_STATIC_GATED_W - (384 - stacks) * HBM_IDLE_W_STACK
        return dict(J_per_token=round(st / rate + DS_HBM_DYN_J, 3), system_w=round(st + DS_HBM_DYN_J * rate))
    mt_f = firm["spec"]["mixed_n36"]["best"]["tokens_s"]
    mt_c = cond["spec"]["mixed_n36"]["best"]["tokens_s"]
    ds_rows = [
        dict(design="DS HBM ablation (GPU-organised, W19 composed, 96 dies TP-96, 4 stacks/die)", ar=2261.7,
             mtp_tau3649=4847.7, mtp_tau4=firm["ablation_tau4_gamma5_tok_s"], **silicon(96 * 340.5, 384),
             **ds_e(2261.7)),
        dict(design="DS HBM accelerator, firm rungs (R1b-R6a), 4 stacks/die", ar=firm["best_ar_tok_s"], mtp_tau3649=mt_f,
             mtp_tau4=firm["tau4_gamma5_tok_s"], **silicon(96 * 340.5, 384), **ds_e(firm["best_ar_tok_s"])),
        dict(design="DS HBM accelerator, firm rungs, 2 stacks/die (R8b)", ar=firm["best_ar_tok_s"], mtp_tau3649=None,
             mtp_note="verify union stream doubles at half bandwidth; ~-4% MTP (ASSUMED, see md)",
             **silicon(96 * 340.5, 192), **ds_e(firm["best_ar_tok_s"], 192)),
        dict(design="DS HBM accelerator incl. conditional R7a (serial chain 1.091 GHz)", ar=cond["best_ar_tok_s"],
             mtp_tau3649=mt_c, mtp_tau4=cond["tau4_gamma5_tok_s"], **silicon(96 * 340.5, 384),
             **ds_e(cond["best_ar_tok_s"])),
        dict(design="DS ROM array (product basis, consolidation.json headline_table)", ar=2786.8, mtp_tau3649=4588.9,
             **silicon(169520.0, 464), J_per_token=0.6795, system_w=round(0.6795 * 2786.8),
             note="stacks from the 188-die economics record; J/token = consolidation mJ_b1 (gated product basis)"),
        dict(design="8x B200, V4.1-Flash 1M (tier-2 calibrated, 38->8 scan fix 32d865831)", ar=282.4, mtp_tau3649=547.8,
             **silicon(16 * 800.0, 64), system_w=8 * 689, J_per_token=round(8 * 689 / 282.4, 2)),
        dict(design="8x B200, DeepSeek-R1 TRT-LLM min-latency, MTP-3, ~3K ctx (published)", ar=None, mtp_tau3649=368.0,
             **silicon(16 * 800.0, 64), note="R1 is 37B active vs V4.1-Flash 13B: anchor, not like-for-like"),
    ]
    return dict(ds=ds_rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "ladder.json"))
    a = ap.parse_args(argv)
    ds = build_ds()
    qw = build_qwen()
    q27 = build_qwen27()
    cmp_ = build_compare(ds, qw)
    try:
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        head = None
    rec = dict(schema="opentallas.uarch.hbm_accelerator_study.v1", source_commit=head, status="MODEL ONLY",
               inputs_sha256={p: sha(ROOT / p) for p in ("results/uarch/hbm_gpu.json", "results/uarch/economics.json",
                                                           "results/uarch/consolidation.json",
                                                           "tools/uarch_model.py")},
               branch_inputs={"w19_ar_fused": "claude/w19-hbm-token 71b3ffc52 results/uarch/w19_hbm_token_ar_fused_wsel256"
                                              ".json sha256 785b2a30a534e7cacad52d242c8019db6a0a42b0574a34ef39e69227117904bc",
                              "dspark_hbm": "claude/v41-hbm-speculation-20261003 d2aff19ef",
                              "c5hc_links": "claude/dsrom-c5hc-adopt-20261003 4ec2eef0e",
                              "async_collective": "claude/qwen-async-collective-20261003 839bab031 (main d79a2089c)",
                              "one_stream_ar": "claude/qwen-allreduce-oneseg-20261003 7d736e8e6",
                              "streaming_hbm": "claude/qwen-hbm-sustained-bw-20261003 52ce3e9c1",
                              "near_hbm_index": "claude/dsrom-nearhbm-20261003 723243a4a",
                              "service_term": "/tmp/claude-review-20261003/dshbm_term (in-tree: results/uarch/"
                                              "v41_hbm_service_term_20261003)"},
               rung_meta=RUNG_META, ds=ds, qwen=qw, qwen27=q27, compare=cmp_,
               constants=dict(SRAM_MM2_PER_MiB=round(SRAM_MM2_PER_MB, 3), DRAM_MM2_PER_STACK=DRAM_MM2_PER_STACK,
                              DS_HBM_STATIC_GATED_W=round(DS_HBM_STATIC_GATED_W, 1),
                              DS_HBM_DYN_J=round(DS_HBM_DYN_J, 4), SHARED_EXPERT_HIDE_US=round(SHARED_EXPERT_HIDE_US, 2),
                              CUT_THROUGH_NS_PER_COLL=round(CUT_THROUGH_NS_PER_COLL, 1),
                              B200_EFFECTIVE_TBPS=round(1 / B200_S_PER_B / 1e12, 2)))
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    # console summary
    for ctx in ("1M", "200K"):
        for tag in ("firm", "with_R7a"):
            r = ds[ctx][tag]
            print(f"DS {ctx} {tag}: AR {r['best_ar_us']} us = {r['best_ar_tok_s']} tok/s; draft {r['draft_us']}; "
                  f"MTP mixed best {r['spec']['mixed_n36']['best']}; tau4 g5 {r['tau4_gamma5_tok_s']}; "
                  f"agentic_all5 best {r['spec']['agentic_all5_n30']['best']}")
    for row in ds["1M"]["firm"]["ladder"]:
        print("  ", row)
    print("topology optimistic firm AR", ds["topology_optimistic_firm_ar_tok_s"])
    for row in qw["ladder"]:
        print("Q", row)
    print("Q same-silicon", qw["same_silicon_as_ablation"]["power_ar"], qw["same_silicon_as_ablation"]["power_dflash"])
    print("Q iso", qw["iso_total_silicon_with_rom"])
    print("Q rom", qw["rom"])
    print("Q ablation power", qw["ablation"]["power"])
    for g in qw["gpus"]:
        print("GPU", g)
    print("Q27", q27)
    for r in cmp_["ds"]:
        print("CMP", r)


if __name__ == "__main__":
    main()
