#!/usr/bin/env python3
"""Utilisation of the DeepSeek-V4.1-Flash ROM array (and its HBM comparator), the bottleneck link, and a priced
optimisation plan.  Model work only: every figure is the budget model's (tools/arch_budget_v41.py), not silicon.

    python3 tools/arch_utilization_v41.py [--out results/arch/v41_utilization.json]

The budget model (owned by the spec agent) is imported, never edited.  This tool:

1. UTILISATION.  At batch 1, at the pipeline-fill batch (28 users: one per layer-group stage) and at saturation
   (1,024 users), with and without MTP (DSpark gamma 5, m = 2, tau 5.0), at 200K (primary) and 1M:
   * MFU per engine class (quantised weight block-dot, BF16, attention, indexer, hyper-connection): model MACs
     of the EMITTED tokens per second / the class's peak MACs per second, for the whole array (188 uniform dies,
     the spec as written) and for the layer dies only (28 groups x 4 = 112);
   * busy fraction per unit (its issue time / wall time, averaged over the layer dies);
   * MBU: ROM bytes read / the provisioned read port and / the macros' sweep capacity; HBM KV + index-key bytes
     / (stacks x 90%); link bytes / link capacity;
   * critical-path efficiency at batch 1: exposed issue time of the units on the critical path / token time.
2. PER-BLOCK GATE (user gate 2026-09-27): every V4.1 block's peak, demand, utilisation, busy fraction, area and
   energy share, on the ROM layer die, the ROM non-layer die and the HBM comparator die; over-provisioned blocks
   flagged with a right-sizing (or the batch-1 latency they buy).
3. BOTTLENECK.  The collective / hop census on the critical path and the levers against it, each re-priced by
   surgery on the budget model's own solved DAG (price(keep=True), then the lever's node changes, then solve).
4. UTILISATION LEVERS and the Pareto (per-user tok/s, aggregate tok/s, area, energy/token incl. static power).
5. RECOMMENDATION.  User rule (2026-09-27): adopt every change that improves MFU/MBU, area or energy WITHOUT
   slowing the batch-1 rate; changes that trade batch-1 speed for utilisation stay documented alternatives.

Dependencies: weight precisions are the spec's current ones (docs/ARCH_SPEC_V41.md 2.1, the checkpoint audit);
another agent is auditing them, and every figure here moves with the budget model if they change.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from contextlib import contextmanager
from dataclasses import asdict, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import arch_budget_v41 as A  # noqa: E402
import decode_critical_path as D  # noqa: E402

# USER DECISION 2026-09-27: 4 HBM3E stacks per die (8 per 2-die package, today's interposers), not the budget
# model's 5.  Applied to the ROM array's dies and, on the same package class, to the HBM comparator's.  The budget
# model reads these module globals at call time, so they are set here without editing it.
STACKS_PER_DIE = 4
A.ROM_DIE_HBM_STACKS = STACKS_PER_DIE
A.ROM_DIE_HBM_BPS = STACKS_PER_DIE * 1.0e12 * 0.90

SCHEMA = "opentallas.v41-utilization.v1"
OUT = ROOT / "results/arch/v41_utilization.json"
BUDGET = ROOT / "results/arch/arch_budget_v41.json"
CONTEXTS = (200000, 1048576)
PRIMARY = 200000
FILL = 28                     # layer-group stages: b <= 28 users ride one per stage at the batch-1 rate
SAT = 1024                    # the nominal saturated batch; a point runs min(SAT, users held): A.point_batch
POINTS = (("b1", 1), ("fill28", FILL), ("sat1024", SAT))
CURVE = (1, 8, 28, 64, 128, 256, 1024)
# MTP (user decision 2026-09-27): DSpark gamma 5 (6 verified positions), lane multiplier m = 2, tau = 5.0 --
# LMSYS/SGLang accept length ~5 on DeepSeek-V4-Pro-DSpark at batch 1 (B300, TP8;
# https://www.lmsys.org/blog/2026-07-06-dspark-sglang/), graded published, third-party, V4-Pro not V4.1-Flash,
# workload unstated; the vLLM survival-derived band 3.27-3.80 is the sensitivity.
TAU = 5.0
TAU_BAND = (3.27, 3.80)
GAMMA = 5
MTP_M = 2
LAYER_GROUPS = 28
G = 4
LAYER_DIES = LAYER_GROUPS * G          # 112 dies hold the 40 layers
DIES = 188
HEAD_DIES = 4                          # the vocabulary-split lm_head group
NONLAYER_DIES = DIES - LAYER_DIES      # 76: Engram tables, embedding, lm_head
CHAIN_L3 = ("osm", "chain_all", "short_stages")    # the spec's adopted chain ladder (docs/ARCH_SPEC_V41.md 12)
MAC_CLASSES = ("weight", "bf16", "att", "idx", "hc")
WORK_KEYS = dict(weight=("weight:fp8", "weight:fp4"), bf16=("weight:bf16", "weight:bf16xfp8w"),
                 att=("attention:bf16xfp8", "attention:bf16"), idx=("indexer:fp4",), hc=("hc_proj:fp32",))
OP_ENERGY = dict(weight=None, bf16="bf16", att="bf16", idx="fp4", hc="fp32")
# block areas the budget does not carry (ASAP7, results/physical_abi3/asap7/...)
EXTRA_AREA_UM2 = dict(
    oneshot16=("rom/ot_rom_oneshot_die_d32", "one-shot all-reduce engine, 16 FP32 lanes, 32-word FIFOs, not closed"),
    pkg_ctrl=("rom/ot_rom_pkg_ctrl", "package controller, closed"),
    fabric_router=("rom/ot_rom_fabric_router", "fabric router, closed"),
    sinkhorn=("hdc/v41/ot_hdc_sinkhorn", "Sinkhorn unit, one normalisation per unit clock, not closed"),
    softplus=("hdc/v41/ot_hdc_softplus", "sqrt(softplus) side pipe, closed"),
    egather_slice=("hdc/v41x/ot_hdc_v41x_egather_slice", "Engram per-bank gather slice, closed 1,656 MHz"),
    egather_asm=("hdc/v41x/ot_hdc_v41x_egather_asm", "Engram gather assembler, closed 1,179 MHz"),
    idx_tail=("hdc/v41x/ot_hdc_v41x_idx_tail", "indexer output tree, closed 1,153 MHz"),
    kv_stream=("hdc/kv/ot_hdc_kv_stream", "HBM KV streamer, not closed"),
    select_k6=("hdc/v41/ot_hdc_select_k6", "router top-6, closed"),
    actquant=("hdc/v41/ot_hdc_actquant", "FP8 activation quantiser, closed"),
)
ONESHOT_RTL = dict(
    cycles_per_token_step_per_die=331.0, lanes=16, word_bytes=64, add_lat=5, fifo_words=32,
    source="results/rtl/hdc_package_tp_campaign.json packages[0].collective_cycles_per_step_per_die (Qwen3 reduced "
           "vehicle, 4-die tensor group, 8 all-reduces of 128 FP32 + 1 argmax gather per token step: ~37 cycles per "
           "collective incl. the 12-cycle UCIe flight) and one_shot_unit reduce_320w_depth32 (1,308 cycles for 320 "
           "16-lane words from 4 dies, 0.98 words/cycle/die): rtl/rom/ot_rom_oneshot_allreduce.sv")


def _area(rel):
    p = ROOT / "results/physical_abi3/asap7" / rel / "physical.json"
    return json.loads(p.read_text())["design"]["area_um2"] if p.exists() else None


@contextmanager
def params(**kw):
    """Price with decode_critical_path Params changed (e.g. moe='expert_parallel'); restored afterwards."""
    E = A._env()
    old = E["p"]
    E["p"] = replace(old, **kw)
    try:
        yield
    finally:
        E["p"] = old


# spec input (agent ad495baa, 2026-09-27; its branch's results/arch/arch_budget_v41.json hc_mtp_sizing): the
# hyper-connection projection is 5,120 FP32 MAC lanes per weight lane (10,240 in the m = 2 MTP core) -- with its
# measured 126-cycle depth, 8,192 lanes left the HC op on the chain-attacked MTP verify path
HC_LANES_SPEC = 5120


def hbm_comparator(c):
    """A.hbm_comparator at STACKS_PER_DIE stacks: the freed PHY area goes to logic, and the die count is re-derived
    at iso total logic area."""
    hb = dict(A.hbm_comparator(c))
    E = A._env()
    h = E["tech"]["hbm"]["hbm3e"]
    d = E["designs"][D.ARRAY_DESIGN]["area_split_per_device"]
    phy = h["phy_area_mm2_per_stack"]["value"]
    logic = d["total_mm2"] - d["interconnect_mm2"] - d["overhead_mm2"] - STACKS_PER_DIE * phy
    dies = math.ceil(hb["rom_array_logic_mm2"] / logic)
    bw = STACKS_PER_DIE * hb["stack_bw_Bps"] * hb["sustained_efficiency_required"]
    hb.update(hbm_stacks_per_die=STACKS_PER_DIE, logic_mm2_per_die=logic, dies=dies, tensor_groups=dies // 4,
              capacity_B=dies * STACKS_PER_DIE * hb["stack_capacity_B"], die_bw_Bps=bw, bw_Bps=bw,
              stacks_note="4 stacks per die (user decision 2026-09-27), re-derived from A.hbm_comparator's 5")
    return hb


NVSWITCH_TRAY_W = 1500.0        # ASSUMED (unverified; adae6788): one NVL72 NVSwitch tray
NVL72_TRAYS, NVL72_GPUS = 9, 72
NVL72_GPU_TBPS = 14.4           # 1.8 TB/s bidirectional per GPU (B200 NVLink) in Tb/s


def static_terms(hb=None):
    """Static power per die on the validated inputs (technology.json 2026-09-27; the budget's power.static_w_per_die):
    logic leakage 0.10 W/mm2 of LOGIC area (the ROM macro array keeps its own 0.0067 W/mm2), HBM idle 2.8 W per stack,
    always-on 112G SerDes at 6.5 pJ/b (0.728 W a lane; 84 per 2-die package), UCIe idle 15% of peak, and the wall
    chain 1 / (VR x PSU) x (1 + CDU + fans).  hb: the HBM comparator die (its logic area and stacks), SerDes excluded
    (it depends on the comparator's fabric)."""
    E = A._env()
    t = E["tech"]
    pw = json.loads(BUDGET.read_text())["power"]
    sw = pw["static_w_per_die"]
    sl = t["power"]["static_leakage_w_per_mm2"]
    stat = E["designs"][D.ARRAY_DESIGN]["static_power"]["detail"]
    lane_w = 112e9 * t["energy"]["link_j_per_bit"]["board_serdes_112g"]["value"]
    stack = t["power"]["memory_interface_idle_w_per_stack"]["value"]
    out = dict(logic_density=sl["logic"]["value"], rom_array_density=sl["rom_array"]["value"],
               rom_array_leak=sl["rom_array"]["value"] * stat["rom_array_mm2_per_device"],
               leakage=sw["leakage"], hbm_idle=sw["hbm_interface_idle"], serdes=sw["serdes_always_on"],
               ucie_idle=sw["ucie_idle"], layer_die=sw["total"], lane_w=lane_w, stack_w=stack,
               table_serdes=lane_w, wall=pw["wall_factor"],
               switch_w_per_tbps=NVSWITCH_TRAY_W * NVL72_TRAYS / (NVL72_GPUS * NVL72_GPU_TBPS),
               source="results/arch/arch_budget_v41.json power.static_w_per_die (validated inputs, cce817f3)")
    if hb:
        out["hbm_die_no_serdes"] = (sl["logic"]["value"] * hb["logic_mm2_per_die"] + hb["hbm_stacks_per_die"] * stack
                                    + sw["ucie_idle"])
    return out


def req_spec():
    sp = A.Spec(**json.loads(BUDGET.read_text())["required_spec"])
    return replace(sp, hc_macs=max(sp.hc_macs, HC_LANES_SPEC))


# -- 1. operating points -------------------------------------------------------------------------------------------
def solve(spec, ctx, batch=1, positions=1, levers=(), muts=(), hbm=None):
    """price() on the budget model, then optional graph surgery (lever mutations) and a re-solve.  The occupancy
    bound is the BUSIEST pipeline stage's (A.stage_bound: the placement is packed by ROM bytes, not by time, and the
    index-scan layers' stages carry several times the mean), not the stage mean price() sizes the specification on."""
    r = A.price(spec, ctx, batch=batch, positions=positions, keep=True, levers=levers, fill=True, hbm=hbm)
    b = r["_built"]
    if not muts:
        ob, busiest, imb = A.stage_bound(b.g, min(b.mach.slots, batch))
        period = max(r["T_s"], ob)
        r.update(occupancy_bound_stage_mean_s=r["occupancy_bound_s"], occupancy_bound_s=ob, busiest_stage=busiest,
                 stage_imbalance=imb, period_s=period, tokens_s_per_user=1 / period, aggregate_tokens_s=batch / period,
                 binding="critical_path" if r["T_s"] >= ob else "occupancy")
    if muts:
        b.g.mb = b.mach.microbatch                         # lever mutations may need the pass size
        b.g.positions = positions                          # the MTP verify pass's hop tail (collective_exposure)
        for f in muts:
            f(b.g, spec)
        fin = b.g.solve(spec.chaining)
        T = fin[b.sink]
        ob, busiest, imb = A.stage_bound(b.g, min(b.mach.slots, batch))     # the busiest stage, after the muts
        period = max(T, ob)
        path = b.g.path(b.sink)
        cats = dict.fromkeys(D.CATS, 0.0)
        for n in path:
            for k_, v in b.g.contrib[n].items():
                cats[k_] = cats.get(k_, 0.0) + v
        r.update(T_s=T, occupancy_bound_s=ob, busiest_stage=busiest, stage_imbalance=imb, period_s=period,
                 tokens_s_per_user=1 / period,
                 aggregate_tokens_s=batch / period, binding="critical_path" if T >= ob else "occupancy",
                 breakdown_us={k: v * 1e6 for k, v in cats.items()})
    return r


def rom_bytes_pass(b, spec, mb, hbm=False):
    """Weight bytes one die reads in one pass (mirrors price(): dense once per ceil(mb / m), routed at the union)."""
    c = A._env()["c"]
    NE, KE, FF, D_ = c["num_routed_experts"], c["experts_per_token"], c["moe_intermediate_size"], c["hidden_size"]
    lm = max(1, spec.lane_mult)
    tokens = max(1, round(mb))
    U = A.distinct_experts(tokens, NE, KE)
    share = tokens * KE / U
    tot = 0.0
    for name, nd in b.g.nodes.items():
        if nd["kind"] != "matvec" or name.endswith("hc.fn"):
            continue
        f = A.die_fraction(name, c, G)
        full = nd["sweep"]["bytes"] * f * A._precision_fix(name, c, nd)
        routed = full if name.endswith("ffn.experts_gu") else (KE * D_ * FF * A.FP4 * f if name.endswith("ffn.down") else 0.0)
        if hbm:                                          # the HBM die buffers a tile and reuses it
            tot += (full - routed) + routed * (U / KE)
        else:
            tot += (full - routed) * math.ceil(mb / lm) + routed * (U / KE) * max(1.0, share / lm)
    return tot


SEPARATE_UNITS = dict(weight="weight", bf16="bf16", att="att", idx="idx", su="su", sfu="sfu", hc="hc", sel="sel")
POOLED_UNITS = dict(SEPARATE_UNITS, idx="weight", att="bf16")


def draft_contention(d, busy_head, verify_s, batch, microbatch, units=None, tol=1e-12):
    """Drafts of different users sharing the head group's engines (MTP at batch > 1).

    Each user's draft runs on the head dies after its verify; with `batch` users cycling, drafts start at
    lambda = batch / (verify + draft) per second, so N = lambda x draft are in flight, and the other users' verify
    passes cross the head (lm_head rows, argmax) meanwhile.  On every pooled head unit u the OTHER users' load is
    rho_u = (batch - 1) / cycle x (draft work on u) + (passes - 1) / cycle x (verify head work on u); the unit is
    time-shared, so this draft's work w_u on it takes w_u / (1 - rho_u) (processor sharing): the contended draft is
    d0 + sum_u w_u rho_u / (1 - rho_u), solved to a fixed point with the cycle.  Conservative against the per-unit
    scoreboard: the slowdown is charged on every busy second, although the isolated draft's span already has idle
    gaps (dependencies, collectives) that other users' work could fill.  Throughput: if any unit's total load
    (every user's drafts + every verify pass) exceeds 1, the aggregate is capped by 1 / that load."""
    u_ = units or SEPARATE_UNITS
    d0 = d["total_s"] + d.get("extra_s", 0.0)
    w = {}
    for k, v in d["busy_s"].items():
        w[u_.get(k, k)] = w.get(u_.get(k, k), 0.0) + v
    vh = {}
    for k, v in busy_head.items():
        vh[u_.get(k, k)] = vh.get(u_.get(k, k), 0.0) + v
    passes = batch / microbatch                              # head passes per verify cycle (one per microbatch)
    unit_names = sorted(set(w) | set(vh))

    def loads(cyc, others):
        n_d, n_v = (batch - 1, passes - 1) if others else (batch, passes)
        return {u: max(0.0, n_d) / cyc * w.get(u, 0.0) + max(0.0, n_v) / cyc * vh.get(u, 0.0) for u in unit_names}

    D = d0
    for _ in range(500):
        rho = loads(verify_s + D, True)
        D_new = d0 + sum(w.get(u, 0.0) * min(r, 0.99) / (1 - min(r, 0.99)) for u, r in rho.items())
        if abs(D_new - D) < tol:
            D = D_new
            break
        D = D_new
    cyc = verify_s + D
    rho = loads(cyc, True)
    total = loads(cyc, False)
    busiest = max(total, key=total.get)
    return dict(isolated_draft_s=d0, contended_draft_s=D, contention_s=D - d0, drafts_per_s=batch / cyc,
                drafts_in_flight=batch / cyc * D, engine_work_per_draft_s=sum(w.values()), engine_work_by_unit_s=w,
                head_verify_work_per_pass_s=sum(vh.values()), head_verify_work_by_unit_s=vh,
                others_load_by_unit=rho, head_unit_load=total, busiest_head_unit=busiest,
                throughput_cap=min(1.0, 1.0 / total[busiest]) if total[busiest] > 0 else 1.0,
                basis="per-unit processor sharing of the head group's pooled units among the users' drafts and "
                      "verify passes (tools/arch_utilization_v41.draft_contention)")


def op_point(spec, ctx, batch, mtp=False, levers=(), muts=(), tau=TAU, hbm=None, dies=None, units=None,
             draft_extra_s=0.0, contention=False):
    """One operating point: rates, per-class busy fraction and MFU, MBU of ROM / HBM / links.
    draft_extra_s: seconds added to every draft (the draft-conditioning transfer, tools/arch_lanes_v41.py).
    contention: MTP drafts of different users overlap on the head group (draft_contention); the period carries the
    contended draft and the aggregate its throughput cap."""
    E = A._env()
    c, clock = E["c"], E["clock"]
    tot, _ = A.token_workload(c, ctx)
    sp = replace(spec, lane_mult=MTP_M) if mtp else spec
    pos = GAMMA + 1 if mtp else 1
    r = solve(sp, ctx, batch=batch, positions=pos, levers=levers, muts=muts, hbm=hbm)
    b = r["_built"]
    m = A.fill_machine(batch)
    mb = m.microbatch * pos
    NL = c["num_layers"]
    # busy (issue) seconds per die per pass, by unit class, layer dies vs the head group
    busy_layer, busy_head = {}, {}
    for name, nd in b.g.nodes.items():
        w = nd.get("_work")
        if not w:
            continue
        L = nd["layer"]
        tgt = busy_head if (L is not None and L >= NL) else busy_layer
        tgt[w[0]] = tgt.get(w[0], 0.0) + nd["issue"]
    dc, cap = None, 1.0
    if mtp:
        dd = dict(A.draft_cost_s(sp, ctx, GAMMA, c, hbm=hbm), extra_s=draft_extra_s)
        draft = dd["total_s"] + draft_extra_s
        if contention and batch > 1:
            dc = draft_contention(dd, busy_head, r["period_s"], batch, m.microbatch, units=units)
            draft, cap = dc["contended_draft_s"], dc["throughput_cap"]
    else:
        draft = 0.0
    period = (r["period_s"] + draft) / cap
    per_user = (tau if mtp else 1.0) / period
    agg = per_user * batch
    slots = min(batch, m.stages)
    frac = {k: slots * v / (m.stages * period) for k, v in busy_layer.items()}
    # the budget model's occupancy bound serialises EVERY unit of a die (sum of issue); with two or more
    # microbatches in flight per stage and a per-unit scoreboard, units overlap and the bound is the busiest unit
    unit_occ = {}
    for k, v in busy_layer.items():
        u_ = (units or SEPARATE_UNITS).get(k, k)
        unit_occ[u_] = unit_occ.get(u_, 0.0) + v
    busiest = max(unit_occ, key=unit_occ.get)
    # the busiest unit of the busiest STAGE (the placement's stages are not balanced in time: A.stage_bound)
    ob_conc, _st, _imb = A.stage_bound(b.g, slots, units=(units or SEPARATE_UNITS), per_unit=True)
    period_conc = max(r["T_s"], ob_conc) + draft
    agg_conc = (tau if mtp else 1.0) / period_conc * batch
    head_frac = {k: slots * v / period / 1.0 for k, v in busy_head.items()}
    # MFU on emitted tokens (goodput) and on executed positions
    lm = sp.lane_mult
    width = dict(weight=sp.weight_macs, bf16=sp.bf16_macs, att=sp.att_macs, idx=sp.idx_macs, hc=sp.hc_macs)
    macs = {k: sum(tot["macs"].get(x, 0) for x in WORK_KEYS[k]) for k in MAC_CLASSES}
    head_macs = c["vocab_size"] * c["hidden_size"]
    n_dies = dies or DIES
    mfu_array, mfu_layer = {}, {}
    for k in MAC_CLASSES:
        peak = width[k] * lm * clock
        mfu_array[k] = agg * macs[k] / (peak * n_dies)
        mfu_layer[k] = agg * (macs[k] - (head_macs if k == "bf16" else 0)) / (peak * (n_dies if hbm else LAYER_DIES))
    peak_all = sum(width[k] for k in MAC_CLASSES) * lm * clock
    mfu_array["all"] = agg * tot["macs_total"] / (peak_all * n_dies)
    mfu_layer["all"] = agg * (tot["macs_total"] - head_macs) / (peak_all * (n_dies if hbm else LAYER_DIES))
    mfu_exec = agg * pos / (tau if mtp else 1.0) * tot["macs_total"] / (peak_all * n_dies)
    # ROM (or HBM-weight) bytes per emitted token
    rb_die = rom_bytes_pass(b, sp, mb, hbm=bool(hbm))                          # one die, one pass of mb user-positions
    tokens_per_pass = m.microbatch * (tau if mtp else 1.0)
    w_bytes_token = G * rb_die / tokens_per_pass
    rom_cap = json.loads(BUDGET.read_text())["rom_read_capacity_bytes_per_cycle"]
    kv_token = (tot["bytes"]["kv_sram"] + tot["bytes"]["idx"]) / (tau if mtp else 1.0)
    link_bytes = sum(nd.get("payload", 0) for nd in b.g.nodes.values() if nd["kind"] in ("collective", "hop"))
    link_token = link_bytes * (pos / (tau if mtp else 1.0))
    out = dict(batch=batch, mtp=mtp, tau=tau if mtp else None, period_us=period * 1e6, verify_us=r["period_s"] * 1e6,
               draft_us=draft * 1e6, tokens_s_per_user=per_user, aggregate_tokens_s=agg, binding=r["binding"],
               microbatch=m.microbatch, breakdown_us=r["breakdown_us"], draft_extra_us=draft_extra_s * 1e6,
               pass_T_us=r["T_s"] * 1e6,
               stage_busy_us={str(s): sum(v.values()) * 1e6 for s, v in A.stage_occupancy(b.g).items()},
               draft_contention=dc,
               busy_fraction_layer_dies=frac, busy_fraction_head_dies=head_frac,
               mfu_array=mfu_array, mfu_layer_dies=mfu_layer, mfu_executed_array=mfu_exec,
               concurrent_units=dict(busiest_unit=busiest, aggregate_tokens_s=agg_conc,
                                     tokens_s_per_user=agg_conc / batch,
                                     gain_over_serial=agg_conc / agg - 1,
                                     mfu_layer_dies=mfu_layer["all"] * agg_conc / agg))
    if hbm:
        cap = hbm["bw_Bps"] * n_dies
        out.update(hbm_weight_bytes_per_token=w_bytes_token,
                   mbu_hbm=(w_bytes_token + kv_token) * agg / cap,
                   mbu_hbm_active_stage=(w_bytes_token + kv_token) * agg / cap * n_dies / (G * slots))
    else:
        out.update(rom_bytes_per_token=w_bytes_token,
                   mbu_rom_port_array=w_bytes_token * agg / (spec.rom_bytes * clock * LAYER_DIES),
                   mbu_rom_macro_array=w_bytes_token * agg / (rom_cap * clock * DIES),
                   mbu_hbm_kv=kv_token * agg / (A.ROM_DIE_HBM_BPS * LAYER_DIES),
                   mbu_hbm_kv_all_stacks=kv_token * agg / (A.ROM_DIE_HBM_BPS * DIES))
    per_die_link = E["links"]["rom_package_ucie"]["bw"] + 1.19e12 / 2      # UCIe partner + half the package SerDes
    out["link_bytes_per_token"] = link_token
    out["mbu_links"] = link_token * agg / (per_die_link * LAYER_DIES)
    if batch == 1 and not mtp:
        ci = sum(r["critical_issue_us_by_resource"].values()) if "critical_issue_us_by_resource" in r else None
        out["critical_path_efficiency"] = ci / (r["T_s"] * 1e6) if ci is not None else None
        out["critical_issue_us_by_resource"] = r.get("critical_issue_us_by_resource")
    return out


# -- 3. the bottleneck and its levers -----------------------------------------------------------------------------
def _zero(g, suffix):
    for n, nd in g.nodes.items():
        if n.endswith(suffix):
            nd["issue"] = nd["depth"] = nd["ctrl"] = 0.0


def _scale_issue(g, suffix, f):
    for n, nd in g.nodes.items():
        if n.endswith(suffix):
            nd["issue"] *= f


def lever_mutations():
    """Each lever as graph surgery on the solved budget DAG.  Returns name -> (mutations, cost, feasibility)."""
    E = A._env()
    clock = E["clock"]
    lk = A.links_for(A.BASELINE)
    ucie, board = lk["rom_package_ucie"]["hop"], lk["rom_board_serdes"]["hop"]
    cyc = 1 / clock
    c = E["c"]
    D_, NE = c["hidden_size"], c["num_routed_experts"]

    def rep_router(g, sp):
        _zero(g, "ffn.router_allgather")
        _scale_issue(g, "ffn.router", G)                  # the full [384, 5120] on every die
        _scale_issue(g, "ffn.softplus_sqrt", G)

    def rep_aproj(g, sp):
        _zero(g, "attn.a_allgather")
        _scale_issue(g, "attn.a_proj", G)

    def rows_local(g, sp):                               # every die gathers all selected rows itself
        _zero(g, "attn.rows_allgather")

    def direct_stage(g, sp):
        """At each group boundary the producing group's partial sums go straight over the hop and the next
        group folds them (one-shot over the hop): the all-reduce before the hop keeps only its in-package
        pre-reduce (UCIe + fold); the residual rides ahead (it is known at the sublayer's start)."""
        for n, nd in list(g.nodes.items()):
            if nd["kind"] != "hop" or nd["hop_kind"] not in ("substage", "head", "stage"):
                continue
            L = nd["layer"]
            src = f"L{L}.attn.out_allreduce" if nd["hop_kind"] == "substage" else f"L{min(L, 39)}.ffn.combine_allreduce"
            if src in g.nodes:
                g.nodes[src]["depth"] = ucie + (2 + 3 * A.ADD_LAT["fastfp"]) * cyc

    def cut_through(g, sp):                              # hops stream behind their producer (flit cut-through)
        for nd in g.nodes.values():
            if nd["kind"] == "hop":
                nd["stream"] = True

    rack = lk["rom_rack_cable_serdes"]["hop"] if "rom_rack_cable_serdes" in lk else board

    def ring_return(g, sp):                              # snake/ring placement: last stage beside the first
        g.nodes["token.return"]["depth"] = rack           # one rack-cable hop (209 ns, full KP4)

    def flat_oneshot(g, sp):
        """Every die owns a board port to both dies of the partner package: an all-reduce is ONE board flight
        plus the one-shot fold (2 + 3 x 3 cycles on the fast add), no in-package pre-reduce / broadcast."""
        for nd in g.nodes.values():
            if nd["kind"] != "collective":
                continue
            if nd["op"] == "all_reduce":
                nd["depth"] = min(nd["depth"], board + (2 + 3 * A.ADD_LAT["fastfp"]) * cyc)
            elif nd["op"] == "all_gather":
                nd["depth"] = min(nd["depth"], board)

    def oneshot_as_built(g, sp):
        """NEGATIVE: the committed one-shot engine moves one 16-lane word per cycle, so a 5,120-FP32 all-reduce
        occupies it 320 cycles -- far longer than its producer's issue; exposed unless the engine is widened."""
        for nd in g.nodes.values():
            if nd["kind"] == "collective" and nd["op"] == "all_reduce":
                nd["issue"] = max(nd["issue"], nd["payload"] / ONESHOT_RTL["word_bytes"] * cyc)

    def oneshot_128(g, sp):
        for nd in g.nodes.values():
            if nd["kind"] == "collective" and nd["op"] == "all_reduce":
                nd["issue"] = max(nd["issue"], nd["payload"] / (8 * ONESHOT_RTL["word_bytes"]) * cyc)

    rom_router = 3 * NE * D_ * 2 * 40
    a_bytes = sum((c["q_lora_rank"] + c["head_dim"]) * D_ * A.FP8 + c["index_heads"] * D_ * 2 for _ in range(40))
    return {
        "replicate_router": ([rep_router], dict(rom_bytes_added=rom_router, collectives_removed_on_path=40),
                             "replicate the BF16 router gate [384, 5120] on all 4 dies (3.9 MB/layer, +0.09% of the "
                             "checkpoint's ROM): each die computes all 384 scores (53 cycles on the BF16 engine) and "
                             "the router all-gather disappears; bit-identical (same FP32 dot per score)"),
        "replicate_a_proj": ([rep_aproj], dict(rom_bytes_added=3 * a_bytes, collectives_removed_on_path=40),
                             "replicate wq_a | wkv | index weights_proj on all 4 dies (+3 x 8.2 MB/layer, +0.2% ROM): "
                             "q_a, kv and the index weights are local; the a all-gather disappears; bit-identical"),
        "rows_local_gather": ([rows_local], dict(hbm_capacity_factor_compressed_kv=4),
                              "every die gathers all 512 selected compressed rows from its own HBM copy: the rows "
                              "all-gather leaves the 8 index-source layers' path; costs 4x the compressed-KV "
                              "capacity (1M users per die ~1,203 -> ~300)"),
        "direct_to_next_stage": ([direct_stage], dict(),
                                 "at the 29 group boundaries the partial sums cross the hop and the next group folds "
                                 "them (the one-shot engine's fold, fixed rank order: bit-identical); the residual "
                                 "copies ride ahead"),
        "cut_through_hops": ([cut_through], dict(),
                             "stage hops stream the residual behind hc_post (flit cut-through, credit per vector) "
                             "instead of store-and-forward of 41 KB at 0.3 TB/s per neighbour"),
        "ring_placement_return": ([ring_return], dict(),
                                  "fold the 29 stage modules into adjacent rack trays; the head dies also hold "
                                  "their embedding quarters, so the selected embedding row returns to S0 in one "
                                  "board hop instead of the generic mesh's 8"),
        "flat_one_shot": ([flat_oneshot], dict(board_ports_per_die=2),
                          "each die gets board lanes to both dies of the partner package (the package's 90 lanes "
                          "split per die; bytes stay overlapped): one board flight + fold per collective"),
        "oneshot_as_built_16_lanes": ([oneshot_as_built], dict(),
                                      "NEGATIVE sensitivity: the committed ot_rom_oneshot_die at LANES = 16"),
        "oneshot_128_lanes": ([oneshot_128], dict(area_um2=8 * _area("rom/ot_rom_oneshot_die_d32")),
                              "requirement: the one-shot engine at LANES >= 128 (512 B/cycle) so a 20-KB all-reduce "
                              "ingests within its producer's issue"),
    }


LEVER_ORDER = ("replicate_router", "replicate_a_proj", "direct_to_next_stage", "cut_through_hops",
               "ring_placement_return", "flat_one_shot")


def census(spec, ctx, levers=()):
    r = solve(spec, ctx, levers=levers)
    b = r["_built"]
    g = b.g
    path = set(g.path(b.sink))
    rows = {}
    for n, nd in g.nodes.items():
        if nd["kind"] not in ("collective", "hop"):
            continue
        k = n.split(".", 1)[1] if nd["kind"] == "collective" else nd["hop_kind"] + "_hop"
        row = rows.setdefault(k, dict(count=0, on_path=0, latency_on_path_us=0.0, bytes_exposed_on_path_us=0.0,
                                      latency_ns_each=round(nd["depth"] * 1e9, 1)))
        row["count"] += 1
        if n in path:
            row["on_path"] += 1
            row["latency_on_path_us"] += g.contrib[n].get(nd["depth_cat"], 0.0) * 1e6
            if nd["issue_cat"] != nd["depth_cat"]:
                row["bytes_exposed_on_path_us"] += g.contrib[n].get(nd["issue_cat"], 0.0) * 1e6
            else:
                row["bytes_exposed_on_path_us"] += max(0.0, g.contrib[n].get(nd["issue_cat"], 0.0) - nd["depth"]) * 1e6
    return dict(T_us=r["T_s"] * 1e6, breakdown_us=r["breakdown_us"], rows=rows,
                collective_latency_us=r["breakdown_us"]["collective_latency"],
                collective_bytes_us=r["breakdown_us"]["collective_bytes"],
                hops_us=r["breakdown_us"]["pipeline_hops"],
                collectives_on_path=sum(v["on_path"] for k, v in rows.items() if not k.endswith("_hop")),
                hops_on_path=sum(v["on_path"] for k, v in rows.items() if k.endswith("_hop")))


def price_levers(spec, base_levers):
    """Each lever alone and cumulatively (LEVER_ORDER), at 200K and 1M, batch 1, on `base_levers`; plus MTP."""
    L = lever_mutations()
    out = dict(base_levers=list(base_levers), single={}, cumulative=[], sensitivities={})
    base = {ctx: solve(spec, ctx, levers=base_levers) for ctx in CONTEXTS}
    for name in L:
        muts, cost, basis = L[name]
        row = dict(cost=cost, feasibility=basis)
        for ctx in CONTEXTS:
            r = solve(spec, ctx, levers=base_levers, muts=muts)
            row[str(ctx)] = dict(us=r["T_s"] * 1e6, tokens_s_per_user=r["tokens_s_per_user"],
                                 delta_us=(r["T_s"] - base[ctx]["T_s"]) * 1e6,
                                 gain=r["tokens_s_per_user"] / base[ctx]["tokens_s_per_user"] - 1)
        out["single"][name] = row
    acc = []
    for name in LEVER_ORDER:
        acc = acc + L[name][0]
        row = dict(step=name)
        for ctx in CONTEXTS:
            r = solve(spec, ctx, levers=base_levers, muts=acc)
            row[str(ctx)] = dict(us=r["T_s"] * 1e6, tokens_s_per_user=r["tokens_s_per_user"],
                                 collective_latency_us=r["breakdown_us"]["collective_latency"],
                                 hops_us=r["breakdown_us"]["pipeline_hops"])
        out["cumulative"].append(row)
    out["cumulative_mutations"] = list(LEVER_ORDER)
    # expert placement: expert-parallel instead of striped (balance / collisions)
    with params(moe="expert_parallel"):
        for ctx in CONTEXTS:
            r1 = solve(spec, ctx, levers=base_levers)
            r64 = solve(spec, ctx, batch=A.point_batch("sat", SAT, ctx), levers=base_levers)
            out["sensitivities"][f"expert_parallel_{ctx}"] = dict(
                b1_tokens_s_per_user=r1["tokens_s_per_user"], sat_aggregate_tokens_s=r64["aggregate_tokens_s"])
    for ctx in CONTEXTS:
        r64 = solve(spec, ctx, batch=A.point_batch("sat", SAT, ctx), levers=base_levers)
        out["sensitivities"][f"striped_{ctx}"] = dict(b1_tokens_s_per_user=base[ctx]["tokens_s_per_user"],
                                                      sat_aggregate_tokens_s=r64["aggregate_tokens_s"])
    # stage count vs per-stage width: the report DAG's packaging options (group 2 / 4 / 4-in-package)
    rec = json.loads((ROOT / "results/roofline/critical_path/decode_critical_path.json").read_text())
    out["stage_count_vs_width"] = {k: dict(label=o["label"][:90], group=o["placement"].get("group"),
                                           b1_tokens_s_per_user=o["batch1"]["tokens_s_per_user"],
                                           breakdown_us=o["batch1"]["breakdown_us"])
                                   for k, o in rec["packaging_options"]["options"].items()}
    out["stage_count_vs_width_note"] = (
        "report DAG (plain option-(b) links), results/roofline/critical_path/decode_critical_path.json "
        "packaging_options: group 2 inside a 2-die package removes the board from every collective (2.2 us) but "
        "doubles each die's weight sweep (86 us) and the stage count (hops 22 us) -- a net loss; group 4 in one "
        "4-die package is the real fix (future packaging); att_local (attention on one package) is priced in "
        "arch_budget_v41 chain_ladder 4a/4b and was not adopted")
    return out


# -- 4. utilisation levers --------------------------------------------------------------------------------------------
POOL_IDX_EXTRA_CYC = 21   # pooled indexer path: ~69 cycles key request -> BF16 score vs 48 standalone (spec agent,
                          # from design, routes pending); added once per index layer


def m_pool_idx(g, sp):
    """The pooled block-dot pool's indexer path is ~21 cycles deeper than the standalone indexer's."""
    for n, nd in g.nodes.items():
        if n.endswith("attn.idx.score"):
            nd["depth"] += POOL_IDX_EXTRA_CYC / A._env()["clock"]


def unified(spec):
    """One block-dot pool for quantised weights AND the indexer (FP4 x FP4 is a mode of the FP8/FP4 block-dot:
    R-ARITH makes both a 32-block exact dot), one BF16 pool for BF16 weights, wo_a (FP8 codes dequantised at the
    lane input) AND attention (BF16 q/p x FP8 KV rows, the same dequantise-at-input mode).  Pool width = the
    larger of the two it replaces; the operand muxes (ROM read network | HBM key stream; ROM | KV staging) are
    charged 10% of the pooled engines' area (ASSUMED, no routed block)."""
    return replace(spec, idx_macs=max(spec.idx_macs, spec.weight_macs), att_macs=max(spec.att_macs, spec.bf16_macs))


def area_of(spec, areas, pooled=False, lm=1):
    a = A.spec_area_mm2(spec, areas)
    if pooled:
        a = dict(a)
        a["idx"], a["att"] = 0.0, 0.0
        a["pool_muxes"] = 0.10 * (a["weight"] + a["bf16"])
        a["total"] = sum(v for k, v in a.items() if k != "total")
    return {k: v * (lm if k not in ("sel", "total") else 1) for k, v in a.items()} | \
        dict(total=(a["total"] - a["sel"]) * lm + a["sel"])


def pool_conflicts(spec, ctx, levers, batch=1):
    """Busy-interval overlap between the classes a pool would merge, within one token's schedule (upper bound of
    the serialisation a shared pool adds).  Returns seconds of overlap and whether any is on the critical path."""
    r = solve(spec, ctx, batch=batch, levers=levers)
    b = r["_built"]
    g = b.g
    path = set(g.path(b.sink))
    iv = {}
    for n, nd in g.nodes.items():
        w = nd.get("_work")
        if not w or nd["issue"] <= 0:
            continue
        f = g.fin[n] - nd["depth"]
        iv.setdefault(w[0], []).append((f - nd["issue"], f, n in path))

    def overlap(a, b_):
        tot, onp = 0.0, 0.0
        for s1, e1, p1 in a:
            for s2, e2, p2 in b_:
                o = min(e1, e2) - max(s1, s2)
                if o > 0:
                    tot += o
                    if p1 or p2:
                        onp += o
        return tot, onp

    q = overlap(iv.get("weight", []), iv.get("idx", []))
    bb = overlap(iv.get("bf16", []), iv.get("att", []))
    return dict(quantised_pool_overlap_us=q[0] * 1e6, quantised_pool_overlap_on_path_us=q[1] * 1e6,
                bf16_pool_overlap_us=bb[0] * 1e6, bf16_pool_overlap_on_path_us=bb[1] * 1e6)


def marginal_widths(spec, levers):
    """Halve (and double) each engine alone: batch-1 tok/s at 200K / 1M and the area it moves -- which widths only
    buy latency, and how much."""
    areas = A.unit_areas()[0]
    out = {}
    base = {ctx: solve(spec, ctx, levers=levers)["tokens_s_per_user"] for ctx in CONTEXTS}
    b64 = solve(spec, PRIMARY, batch=64, levers=levers)["tokens_s_per_user"]
    for k in A.RESOURCES:
        w = getattr(spec, A.WIDTH_FIELD[k])
        row = dict(width=w, area_mm2=w * areas[A.AREA_KEY[k]] / 1e6)
        for tag, f in (("half", 0.5), ("double", 2.0)):
            sp = A._with_widths(spec, {k: A.round_width(k, w * f)})
            row[tag] = {str(ctx): solve(sp, ctx, levers=levers)["tokens_s_per_user"] / base[ctx] - 1 for ctx in CONTEXTS}
            row[tag]["b64_200000"] = solve(sp, PRIMARY, batch=64, levers=levers)["tokens_s_per_user"] / b64 - 1
        out[k] = row
    return out


# -- energy ----------------------------------------------------------------------------------------------------------------
def energy(spec, ctx, point, area_layer_mm2, area_nonlayer_mm2, static_w_layer, static_w_nonlayer, hbm=None):
    """J per emitted token at an operating point: dynamic non-clock parts (budget model's energy_per_token at the
    point's microbatch), the clock of the clocked die-time (gated: a die clocks only while its stage holds work;
    the non-layer dies clock only for the head/Engram share) and the STATIC power of every die over the token."""
    E = A._env()
    et = A.energy_terms(E["tech"])
    clock = E["clock"]
    mb, pos = point["microbatch"], (GAMMA + 1 if point["mtp"] else 1)
    sp = replace(spec, lane_mult=MTP_M) if point["mtp"] else spec
    e = A.energy_per_token(sp, ctx, mb, pos, hbm=hbm, rate_tokens_s=point["aggregate_tokens_s"])
    nonclock = e["total_j"] - e["parts_j"]["clock"]
    if point["mtp"]:
        nonclock = nonclock * pos / point["tau"] * (1 + 3 / 40)
    agg = point["aggregate_tokens_s"]
    b = point["batch"]
    period = point["period_us"] * 1e-6
    n_layer = LAYER_DIES if not hbm else hbm["dies"]
    clocked_die_s = n_layer * period * min(b, FILL) / FILL / b / max(1.0, (point["tau"] if point["mtp"] else 1.0))
    clk_gated = et["clock"] * area_layer_mm2 * clock * clocked_die_s
    clk_ungated = et["clock"] * (area_layer_mm2 * n_layer + (area_nonlayer_mm2 * NONLAYER_DIES if not hbm else 0)) \
        * clock / agg
    static = (static_w_layer * n_layer + (static_w_nonlayer * NONLAYER_DIES if not hbm else 0)) / agg
    return dict(dynamic_nonclock_j=nonclock, clock_gated_j=clk_gated, clock_ungated_j=clk_ungated, static_j=static,
                total_gated_j=nonclock + clk_gated + static, total_gated_dynamic_only_j=nonclock + clk_gated,
                parts_nonclock_j={k: v for k, v in e["parts_j"].items() if k != "clock"})


# -- 2. per-block gate -------------------------------------------------------------------------------------------------------
def block_gate(spec, pts, c, areas, extra, clock, static):
    """Per block of the ROM layer die: peak, demand per operating point, utilisation, busy fraction, area share."""
    tot, _ = A.token_workload(c, PRIMARY)
    lm_of = lambda p: MTP_M if p["mtp"] else 1  # noqa: E731
    blk_area = A.spec_area_mm2(spec, areas)
    NL = c["num_layers"]
    rows = []

    def row(block, unit, peak, demand_fn, busy_key=None, area_mm2=0.0, note="", right_size=None):
        r = dict(block=block, unit=unit, peak=peak, area_mm2=area_mm2, note=note, right_size=right_size, points={})
        for tag, p in pts.items():
            d = demand_fn(p)
            pk = peak * (lm_of(p) if unit.endswith("/cycle") and "MAC" in unit else 1)
            r["points"][tag] = dict(demand=d, utilisation=(d / pk) if (pk and d is not None) else None,
                                    busy_fraction=p["busy_fraction_layer_dies"].get(busy_key) if busy_key else None)
        rows.append(r)

    def macs_per_cycle(keys, head=False):
        def f(p):
            m = sum(tot["macs"].get(k, 0) for k in keys) - (c["vocab_size"] * c["hidden_size"] if head else 0)
            return p["aggregate_tokens_s"] * m / (LAYER_DIES * clock)
        return f
    row("FP8/FP4 weight engine (block-dot)", "MACs/cycle", spec.weight_macs, macs_per_cycle(WORK_KEYS["weight"]),
        "weight", blk_area["weight"])
    row("BF16/FP32 weight engine", "MACs/cycle", spec.bf16_macs, macs_per_cycle(WORK_KEYS["bf16"], head=True), "bf16",
        blk_area["bf16"], note="lm_head runs on the 4 head dies, not here")
    row("attention engine", "MACs/cycle", spec.att_macs, macs_per_cycle(WORK_KEYS["att"]), "att", blk_area["att"])
    row("KV row staging", "bytes/cycle", spec.kv_bytes,
        lambda p: p["aggregate_tokens_s"] * tot["bytes"]["kv_sram"] * G / tau_of(p) / (LAYER_DIES * clock), None, 0.0,
        note="every die stages all rows of its layers (rows all-gathered)")
    row("lightning indexer engine", "MACs/cycle", spec.idx_macs, macs_per_cycle(WORK_KEYS["idx"]), "idx", blk_area["idx"])
    row("HBM index-key stream", "bytes/cycle", spec.idx_bytes,
        lambda p: p["aggregate_tokens_s"] * tot["bytes"]["idx"] / (tau_of(p)) / (LAYER_DIES * clock), None,
        extra["kv_stream"] / 1e6, note="averaged over layer dies; only 8 of 28 groups scan")
    sel_scores = sum(o["elems"] for L in range(NL) for o in A.ops_of_layer(c, L, PRIMARY)[0]
                     if o["cls"] == "select" and (".idx." in o["name"] or ".cand." in o["name"]))
    row("top-512 + candidate select", "scores/cycle", spec.sel_lanes,
        lambda p: p["aggregate_tokens_s"] * sel_scores / tau_of(p) * (GAMMA + 1 if p["mtp"] else 1)
        / (LAYER_DIES * clock), "sel", blk_area["sel"], note="scores per die; only the 8 scan groups work")
    row("hyper-connection projection", "FP32 MACs/cycle", spec.hc_macs, macs_per_cycle(WORK_KEYS["hc"]), "hc",
        blk_area["hc"], note="replicated: every die projects its layers' mixes (4x the model MACs)")
    sk_cyc = 297
    row("Sinkhorn unit", "normalisations/token", 1.0,
        lambda p: p["aggregate_tokens_s"] * 2 * NL * sk_cyc * G / (LAYER_DIES * clock)
        * ((GAMMA + 1) / p["tau"] if p["mtp"] else 1), None,
        extra["sinkhorn"] / 1e6, note="busy fraction = 297 core cycles x 2 per layer per die")
    row("vector unit, light lanes", "elements/cycle", spec.su_lanes,
        lambda p: p["aggregate_tokens_s"] * tot["elems"].get("linear", 0) / (LAYER_DIES * clock) * 1.0, "su",
        blk_area["su"], note="stream work is replicated per die: demand here is the model's, busy includes replication")
    row("vector unit, SFU lanes", "elements/cycle", spec.sfu_lanes,
        lambda p: p["aggregate_tokens_s"] * (tot["elems"].get("transcendental", 0) + tot["elems"].get("divide", 0))
        / (LAYER_DIES * clock), "sfu", blk_area["sfu"])
    row("weight ROM read port", "bytes/cycle", spec.rom_bytes,
        lambda p: p["aggregate_tokens_s"] * p["rom_bytes_per_token"] / (LAYER_DIES * clock), None, 0.0)
    rom_cap = json.loads(BUDGET.read_text())["rom_read_capacity_bytes_per_cycle"]
    row("ROM macros (sweep capacity)", "bytes/cycle", rom_cap,
        lambda p: p["aggregate_tokens_s"] * p["rom_bytes_per_token"] / (LAYER_DIES * clock), None, 289.4)
    row(f"HBM controllers + PHYs ({STACKS_PER_DIE} stacks)", "bytes/s", A.ROM_DIE_HBM_BPS,
        lambda p: p["aggregate_tokens_s"] * (tot["bytes"]["kv_sram"] + tot["bytes"]["idx"]) / tau_of(p) / LAYER_DIES,
        None, 10.0 * STACKS_PER_DIE, note="PHY area 10 mm2/stack (technology.json, assumed)")
    per_die_link = A._env()["links"]["rom_package_ucie"]["bw"] + 1.19e12 / 2
    row("UCIe + package SerDes", "bytes/s", per_die_link,
        lambda p: p["aggregate_tokens_s"] * p["link_bytes_per_token"] / LAYER_DIES, None, 65.2,
        note="interconnect area of the analytical die; latency-bound, not bandwidth-bound")
    row("one-shot all-reduce engine (16 lanes as built)", "words/cycle", 1.0,
        lambda p: p["aggregate_tokens_s"] * (2 * NL * c["hidden_size"] * 4 / 64) * G / (LAYER_DIES * clock) / tau_of(p)
        * (GAMMA + 1 if p["mtp"] else 1), None, extra["oneshot16"] / 1e6,
        note="80 all-reduces of 320 words per token per die; widen to 128 lanes (lever)")
    row("sequencer / control", "instructions/cycle", 1 / 5,
        lambda p: p["aggregate_tokens_s"] * 3837 / LAYER_GROUPS / p["microbatch"] / tau_of(p) / clock, None,
        extra["pkg_ctrl"] / 1e6,
        note="3,837 instructions per token over 40 layers (results/arch/v41x_replay.json), ~137 per die visit, one "
             "instruction per microbatch pass, 5-cycle issue")
    return rows


def tau_of(p):
    return p["tau"] if p["mtp"] else 1.0


# -- build ------------------------------------------------------------------------------------------------------------------------
def build():
    E = A._env()
    c, clock = E["c"], E["clock"]
    areas = A.unit_areas()[0]
    extra = {k: _area(v[0]) for k, v in EXTRA_AREA_UM2.items()}
    spec = req_spec()
    budget = json.loads(BUDGET.read_text())
    hb = hbm_comparator(c)
    hbm_kw = dict(bw_Bps=hb["bw_Bps"], lat_s=hb["lat_s"], dies=hb["dies"])
    stat = E["designs"][D.ARRAY_DESIGN]["static_power"]["detail"]
    ST = static_terms(hb)
    leak = ST["leakage"]
    hbm_if = ST["hbm_idle"]
    rom_leak = ST["rom_array_leak"]
    logic_leak_per_mm2 = ST["logic_density"]
    rec = dict(schema=SCHEMA, tool="tools/arch_utilization_v41.py", clock_hz=clock,
               budget_model="tools/arch_budget_v41.py (imported, not edited); results/arch/arch_budget_v41.json",
               precision_dependency=("weights at the spec's current checkpoint dtypes (docs/ARCH_SPEC_V41.md 2.1); a "
                                     "separate agent is auditing them -- every figure re-derives from the budget model"),
               mtp=dict(tau=TAU, tau_band=TAU_BAND, gamma=GAMMA, positions=GAMMA + 1, lane_mult=MTP_M,
                        tau_source="LMSYS/SGLang DeepSeek-V4-Pro-DSpark batch 1 (B300, TP8), ~5 accepted; "
                                   "https://www.lmsys.org/blog/2026-07-06-dspark-sglang/; published, third-party, "
                                   "V4-Pro not V4.1-Flash, workload unstated; band 3.27-3.80 vLLM survival-derived"),
               die_classes=dict(dies=DIES, layer_dies=LAYER_DIES, layer_groups=LAYER_GROUPS, nonlayer_dies=NONLAYER_DIES,
                                head_dies=HEAD_DIES,
                                note="188 dies: 28 groups x 4 hold the 40 layers; 76 hold the Engram tables (202.8 GB), "
                                     "the embedding and the BF16 lm_head (4 dies run it)"),
               definitions=dict(
                   mfu="model MACs of the EMITTED tokens per second / the class's peak MACs per second (lanes x m x "
                       "clock x dies); 'array' = all 188 dies carrying the spec's blocks (as the spec is written), "
                       "'layer_dies' = the 112 dies that run layers",
                   busy_fraction="a unit's issue time per wall time, mean over the layer dies (the model's issue: "
                                 "includes ROM-port or lane-quantisation stalls, replication and MTP positions)",
                   mbu_rom_port="ROM weight bytes read per second / (provisioned read port x clock x 112 layer dies)",
                   mbu_rom_macro="ROM weight bytes read per second / (macro sweep capacity 2.96 TB/s/mm2 x 289 mm2 x "
                                 "188 dies)",
                   mbu_hbm_kv="KV rows + index keys per second / (4.5 TB/s x 112 layer dies)",
                   mbu_links="collective + hop payload bytes per second / (UCIe 4.2 TB/s + half the 2-die package's "
                             "1.19 TB/s SerDes) per layer die",
                   critical_path_efficiency="exposed issue time of the units on the batch-1 critical path / the token "
                                            "time: how much of the token is spent doing work rather than waiting on "
                                            "depth, links and control"))
    configs = dict(spec=((), spec, False), spec_l3=(CHAIN_L3, spec, False))
    # 1. utilisation at each operating point
    util = {}
    for ctx in CONTEXTS:
        util[str(ctx)] = {}
        for cname, (lv, sp, _) in configs.items():
            rows = {}
            for tag, bt in POINTS:
                bt = A.point_batch(tag, bt, ctx)
                rows[tag] = op_point(sp, ctx, bt, levers=lv)
                rows[tag + "_mtp"] = op_point(sp, ctx, bt, mtp=True, levers=lv)
            util[str(ctx)][cname] = rows
    rec["utilisation"] = util
    u = util[str(PRIMARY)]["spec"]
    rom_cap = budget["rom_read_capacity_bytes_per_cycle"]
    rec["coordinator_check"] = dict(
        batch1_mfu=dict(estimate=0.001, model=u["b1"]["mfu_array"]["all"], verdict="confirmed (~0.1%)"),
        saturated_mfu=dict(estimate=0.08, model=u["sat1024"]["mfu_array"]["all"],
                           verdict="confirmed (~8% at 1,024 users; the array is occupancy-bound there)"),
        rom_read_39pct=dict(estimate=0.39, provisioned_port_over_macro=spec.rom_bytes / rom_cap,
                            actual_b1=u["b1"]["mbu_rom_macro_array"], actual_sat=u["sat1024"]["mbu_rom_macro_array"],
                            verdict="corrected: 39% is the PROVISIONED read port over the macros' sweep rate (a "
                                    "peak-to-peak ratio); the ROM actually read is ~0.04% of macro capacity at batch 1 "
                                    "and a few % at saturation"))
    # HBM comparator utilisation
    hbm_util = {}
    for ctx in CONTEXTS:
        rows = {}
        for tag, bt in POINTS:
            bt = A.point_batch(tag, bt, ctx, "hbm")
            rows[tag] = op_point(spec, ctx, bt, hbm=hbm_kw, dies=hb["dies"])
            rows[tag + "_mtp"] = op_point(spec, ctx, bt, mtp=True, hbm=hbm_kw, dies=hb["dies"])
        hbm_util[str(ctx)] = rows
    hr = {}
    for f in (1.0, 0.5, 0.25):
        sp = A._with_widths(spec, {k: A.round_width(k, getattr(spec, A.WIDTH_FIELD[k]) * f)
                                   for k in ("weight", "bf16", "att", "idx")})
        hr[str(f)] = {str(ctx): dict(b1=solve(sp, ctx, hbm=hbm_kw)["tokens_s_per_user"],
                                     b1_mtp=op_point(sp, ctx, 1, mtp=True, hbm=hbm_kw, dies=hb["dies"])["tokens_s_per_user"],
                                     area_mm2=A.spec_area_mm2(sp, areas)["total"]) for ctx in CONTEXTS}
    rec["hbm_engine_right_size"] = dict(rows=hr, note="the comparator die's weight/BF16/attention/indexer engines at "
                                                      "1x, 1/2 and 1/4 of the ROM die's spec widths")
    rec["hbm_comparator_utilisation"] = dict(dies=hb["dies"], stacks_per_die=hb["hbm_stacks_per_die"],
                                             bw_Bps_per_die=hb["bw_Bps"], rows=hbm_util,
                                             note="the comparator dies carry the ROM die's block spec (MTP at m = 2 as "
                                                  "in the batch model); weight bytes stream from HBM")
    # 2. per-block gate
    pts = {k: u[k] for k in ("b1", "b1_mtp", "fill28", "fill28_mtp", "sat1024", "sat1024_mtp")}
    gate = block_gate(spec, pts, c, areas, extra, clock, None)
    rec["block_gate"] = dict(ctx=PRIMARY, die="ROM layer die (one of 112)", rows=gate)
    # 3. bottleneck
    rec["bottleneck"] = dict(census_spec=census(spec, PRIMARY), census_l3=census(spec, PRIMARY, CHAIN_L3),
                             oneshot_rtl=ONESHOT_RTL)
    rec["levers"] = dict(on_spec=price_levers(spec, ()), on_l3=price_levers(spec, CHAIN_L3))
    # MTP on top of the adopted levers
    L = lever_mutations()
    full = list(LEVER_ORDER) + ["oneshot_128_lanes"]
    loo = {}
    for ctx in CONTEXTS:
        t_all = solve(spec, ctx, levers=CHAIN_L3, muts=[f for n in full for f in L[n][0]])["T_s"]
        t_all_mtp = solve(replace(spec, lane_mult=MTP_M), ctx, positions=GAMMA + 1, levers=CHAIN_L3,
                          muts=[f for n in full for f in L[n][0]])["T_s"]
        for n in full:
            rest = [f for k in full if k != n for f in L[k][0]]
            t = solve(spec, ctx, levers=CHAIN_L3, muts=rest)["T_s"]
            tm = solve(replace(spec, lane_mult=MTP_M), ctx, positions=GAMMA + 1, levers=CHAIN_L3, muts=rest)["T_s"]
            loo.setdefault(n, {})[str(ctx)] = dict(us_saved_b1=(t - t_all) * 1e6, us_saved_verify=(tm - t_all_mtp) * 1e6)
    rec["leave_one_out_l3"] = loo
    # adopt a lever only if it buys batch-1 time in the full set (> 0.05 us at 200K or 1M, with or without MTP)
    adopted = [n for n in full if n == "oneshot_128_lanes" or
               max(max(v["us_saved_b1"], v["us_saved_verify"]) for v in loo[n].values()) > 0.05]
    rec["adopted_levers"] = adopted
    adopted_muts = [f for n in adopted for f in L[n][0]]
    # 4. utilisation levers
    uni = unified(spec)
    rec["unification"] = dict(
        spec_area_mm2=A.spec_area_mm2(spec, areas)["total"],
        pooled_area=area_of(spec, areas, pooled=True),
        widths=dict(quantised_pool=uni.weight_macs, bf16_pool=uni.bf16_macs),
        conflicts={str(ctx): pool_conflicts(spec, ctx, CHAIN_L3) for ctx in CONTEXTS},
        batch1={str(ctx): dict(spec=solve(spec, ctx, levers=CHAIN_L3)["tokens_s_per_user"],
                               pooled=solve(uni, ctx, levers=CHAIN_L3, muts=[m_pool_idx])["tokens_s_per_user"])
                for ctx in CONTEXTS},
        batch1_mtp={str(ctx): dict(
            spec=op_point(spec, ctx, 1, mtp=True, levers=CHAIN_L3)["tokens_s_per_user"],
            pooled=op_point(uni, ctx, 1, mtp=True, levers=CHAIN_L3, muts=[m_pool_idx], units=POOLED_UNITS)[
                "tokens_s_per_user"]) for ctx in CONTEXTS},
        d_split_note=("the pooled width 252,160 = 61.6 index keys/cycle x 4,096 MACs; the scan fits the pool only "
                      "with the idx split-chain mode (d_split); without it 64 keys/cycle would need 262,144"),
        saturated={str(ctx): dict(spec=solve(spec, ctx, batch=A.point_batch("sat", SAT, ctx), levers=CHAIN_L3)[
                                      "aggregate_tokens_s"],
                                  pooled=solve(uni, ctx, batch=A.point_batch("sat", SAT, ctx), levers=CHAIN_L3,
                                               muts=[m_pool_idx])["aggregate_tokens_s"],
                                  batch=A.point_batch("sat", SAT, ctx))
                   for ctx in CONTEXTS},
        feasibility=unified.__doc__.strip())
    rec["marginal_widths_l3"] = marginal_widths(spec, CHAIN_L3)
    # non-layer dies and HBM stacks
    blk = A.spec_area_mm2(spec, areas)["total"]
    head_keep = A.spec_area_mm2(spec, areas)["bf16"] + A.spec_area_mm2(spec, areas)["su"] + \
        A.spec_area_mm2(spec, areas)["sfu"] + 8 * extra["oneshot16"] / 1e6
    eng_keep = 24 * extra["egather_slice"] / 1e6 + extra["egather_asm"] / 1e6
    rec["nonlayer_right_size"] = dict(
        engine_area_per_die_spec_mm2=blk,
        head_die_keeps_mm2=head_keep, engram_die_keeps_mm2=eng_keep,
        engine_area_removed_mm2=(NONLAYER_DIES - HEAD_DIES) * (blk - eng_keep) + HEAD_DIES * (blk - head_keep),
        engine_area_array_spec_mm2=DIES * blk,
        hbm_stacks_removed=(NONLAYER_DIES - HEAD_DIES) * A.ROM_DIE_HBM_STACKS,
        hbm_stacks_spec=DIES * A.ROM_DIE_HBM_STACKS,
        head_dies_keep_stacks="4 per head die for the drafter's per-user state at saturation (rack C10)",
        static_w_saved=(NONLAYER_DIES - HEAD_DIES) * (hbm_if + logic_leak_per_mm2 * (blk - eng_keep)
                                                     + ST["serdes"] - ST["table_serdes"])
        + HEAD_DIES * logic_leak_per_mm2 * (blk - head_keep),
        batch1_effect="none: the non-layer dies' engines never run layer work; KV lives only on layer dies",
        basis=("busy fraction of a non-layer die's weight/attention/indexer/HC engines is 0 at every batch (they run "
               "no layer); the 4 lm_head dies need the BF16 engine, the vector unit and the one-shot engine; the "
               "Engram dies need only their per-bank gather slices and the assembler; the HBM stacks hold KV and "
               "index keys, which live on the layer dies (kv-lives-in-hbm), except the head dies' 4 stacks for the "
               "drafter (rack C10). Static saving on the table dies: HBM idle + logic leakage (0.10 W/mm2 of logic) "
               "x the removed ASAP7 engine area (ASSUMED scaling) + the SerDes they do not need (84 -> 2 lanes a "
               "package)"))
    nl_saved_per_die = rec["nonlayer_right_size"]["static_w_saved"] / NONLAYER_DIES
    # 5. Pareto: configurations x batch, with and without MTP
    static_layer = ST["layer_die"]
    configs_p = [
        ("spec", spec, (), [], False),
        ("spec+chain(L1-3)", spec, CHAIN_L3, [], False),
        ("L3+comm levers", spec, CHAIN_L3, adopted_muts, False),
        ("L3+comm+pooled engines", uni, CHAIN_L3, adopted_muts + [m_pool_idx], True),
    ]
    pareto = []
    for cname, sp, lv, muts, pooled in configs_p:
        un = POOLED_UNITS if pooled else SEPARATE_UNITS
        for mtp in (False, True):
            ar = area_of(sp, areas, pooled=pooled, lm=MTP_M if mtp else 1)["total"]
            # the spec as written: 188 uniform dies; from 'L3+comm levers' on, the non-layer dies are right-sized
            uniform = cname in ("spec", "spec+chain(L1-3)")
            nl_area = ar if uniform else eng_keep
            s_nl = static_layer if uniform else static_layer - nl_saved_per_die
            for bt in CURVE:
                p = op_point(sp, PRIMARY, bt, mtp=mtp, levers=lv, muts=muts, units=un)
                en = energy(sp, PRIMARY, p, ar, nl_area, static_layer, s_nl)
                pareto.append(dict(config=cname, mtp=mtp, batch=bt, tokens_s_per_user=p["tokens_s_per_user"],
                                   aggregate_tokens_s=p["aggregate_tokens_s"], layer_die_block_mm2=ar,
                                   mfu_array=p["mfu_array"]["all"], mfu_layer_dies=p["mfu_layer_dies"]["all"],
                                   energy_j_per_token=en["total_gated_j"],
                                   energy_dynamic_j_per_token=en["total_gated_dynamic_only_j"],
                                   energy_static_j_per_token=en["static_j"],
                                   concurrent_aggregate_tokens_s=p["concurrent_units"]["aggregate_tokens_s"],
                                   concurrent_tokens_s_per_user=p["concurrent_units"]["tokens_s_per_user"]))
    for r in pareto:
        r["frontier"] = not any(o["tokens_s_per_user"] >= r["tokens_s_per_user"] and
                                o["aggregate_tokens_s"] >= r["aggregate_tokens_s"] and
                                o["layer_die_block_mm2"] <= r["layer_die_block_mm2"] and
                                o["energy_j_per_token"] <= r["energy_j_per_token"] and o is not r and
                                (o["tokens_s_per_user"], o["aggregate_tokens_s"], -o["energy_j_per_token"],
                                 -o["layer_die_block_mm2"]) != (r["tokens_s_per_user"], r["aggregate_tokens_s"],
                                                                -r["energy_j_per_token"], -r["layer_die_block_mm2"])
                                for o in pareto)
    rec["pareto"] = dict(ctx=PRIMARY, rows=pareto,
                         energy_basis=("dynamic = the budget model's per-format MAC, ROM/HBM byte and link energies at "
                                       "the point's microbatch; clock gated per stage; static = the budget's per-die static "
                                       f"{static_layer:.1f} W (leakage, HBM idle, SerDes, UCIe idle), less the right-sizing "
                                       "saving on the 76 non-layer dies from 'L3+comm levers' on (ASSUMED scaling)"))
    # recommended design point
    rec["design_point"] = design_point(rec, uni, adopted_muts + [m_pool_idx], areas)
    rec["energy_with_static"] = energy_with_static(spec, uni, adopted_muts + [m_pool_idx], areas, hb, hbm_kw, stat,
                                                   rec["nonlayer_right_size"], eng_keep)
    rec["tau_band"] = {str(t): op_point(uni, PRIMARY, 1, mtp=True, levers=CHAIN_L3, muts=adopted_muts + [m_pool_idx],
                                        tau=t)[
        "tokens_s_per_user"] for t in TAU_BAND + (TAU,)}
    return rec


def energy_with_static(spec, uni, muts, areas, hb, hbm_kw, stat, rs, eng_keep):
    """J per emitted token WITH static power, ROM array vs HBM comparator, on one basis (spec agent request,
    2026-09-27): static = logic leakage + HBM stacks' traffic-independent power, charged on every die over the
    token; dynamic = the budget model's MAC / byte / link energies + the gated clock of the block area.

    * ROM die: the validated static terms (static_terms: logic leakage, SerDes, UCIe idle) + its
      A.ROM_DIE_HBM_STACKS (4) stacks x the idle W per stack.
    * HBM die: logic leakage at the same per-mm2 logic density x the comparator die's logic area + its
      hbm_stacks_per_die (4, the shipping-interposer cap) x the idle W per stack.
    * 2.8 W/stack: technology.json power.memory_interface_idle_w_per_stack (DRAM standby + refresh + PHY and
      controller, band 1.2-6.4 W); the same term the ROM die's 14 W already is.
    * Sensitivity: technology.json's clocked-idle floor (50 W per device, applied as max(enumerated, floor))."""
    E = A._env()
    t = E["tech"]["power"]
    stack_w = t["memory_interface_idle_w_per_stack"]["value"]
    floor_w = t["clocked_idle_floor_w_per_device"]["value"]
    band = (1.2, 6.4)
    ST = static_terms(hb)
    dens = ST["logic_density"]
    leak_hbm = dens * hb["logic_mm2_per_die"]
    S = A.ROM_DIE_HBM_STACKS
    nl_saved = rs["static_w_saved"] / NONLAYER_DIES
    leak_rom = ST["layer_die"] - S * stack_w           # everything but the stacks (leakage, SerDes, UCIe idle)

    def st(kind, stack=stack_w, floor=False):
        """array static W on the validated terms (static_terms)."""
        if kind == "hbm":
            w = ST["hbm_die_no_serdes"] + ST["serdes"] + hb["hbm_stacks_per_die"] * (stack - stack_w)
            return max(w, floor_w) * hb["dies"] if floor else w * hb["dies"]
        w = leak_rom + S * stack
        wn = w if kind == "rom_spec" else max(0.0, w - nl_saved - S * (stack - stack_w))
        if floor:
            w, wn = max(w, floor_w), max(wn, floor_w if kind == "rom_spec" else wn)
        return w * LAYER_DIES + wn * NONLAYER_DIES

    rows = {}
    for ctx in CONTEXTS:
        for tag, bt in POINTS:
            for mtp in (False, True):
                key = f"{ctx}/{tag}{'_mtp' if mtp else ''}"
                out = {}
                for kind, sp, lv, mu, un, hbm in (
                        ("rom_spec", spec, (), (), SEPARATE_UNITS, None),
                        ("rom_design", uni, CHAIN_L3, muts, POOLED_UNITS, None),
                        ("hbm", spec, (), (), SEPARATE_UNITS, hbm_kw)):
                    p = op_point(sp, ctx, A.point_batch(tag, bt, ctx, "hbm" if hbm else "rom"), mtp=mtp, levers=lv,
                                 muts=mu, units=un, hbm=hbm, dies=hb["dies"] if hbm else None)
                    pooled = kind == "rom_design"
                    ar = area_of(sp, areas, pooled=pooled, lm=MTP_M if mtp else 1)["total"]
                    e = energy(sp, ctx, p, ar, ar if kind == "rom_spec" else eng_keep, 0.0, 0.0, hbm=hbm)
                    dyn = e["dynamic_nonclock_j"] + e["clock_gated_j"]
                    agg = p["aggregate_tokens_s"]
                    s = st(kind) / agg
                    out[kind] = dict(tokens_s_per_user=p["tokens_s_per_user"], aggregate_tokens_s=agg,
                                     dynamic_j=dyn, static_j=s, total_j=dyn + s,
                                     static_array_w=st(kind),
                                     total_j_stack_band=[dyn + st(kind, stack=b) / agg for b in band],
                                     total_j_with_idle_floor=dyn + st(kind, floor=True) / agg)
                for rk in ("rom_spec", "rom_design"):
                    h, r = out["hbm"], out[rk]
                    out[f"hbm_over_{rk}"] = dict(
                        with_static=h["total_j"] / r["total_j"], dynamic_only=h["dynamic_j"] / r["dynamic_j"],
                        with_idle_floor=h["total_j_with_idle_floor"] / r["total_j_with_idle_floor"],
                        stack_band=[hb_ / rb_ for hb_, rb_ in zip(h["total_j_stack_band"], r["total_j_stack_band"])])
                rows[key] = out
    return dict(basis=energy_with_static.__doc__.strip(), stack_w=stack_w, stack_w_band=band,
                idle_floor_w_per_device=floor_w, rom_die_static_w=leak_rom + S * stack_w,
                hbm_die_static_w=ST["hbm_die_no_serdes"] + ST["serdes"], hbm_die_logic_leak_w=leak_hbm,
                logic_leak_w_per_mm2=dens, rom_dies=DIES, hbm_dies=hb["dies"],
                rom_design_nonlayer_die_static_w=leak_rom + S * stack_w - nl_saved, rows=rows,
                note="rom_spec = the spec as written (188 uniform dies, spec engines); rom_design = the recommended "
                     "point (pooled engines, adopted levers, right-sized non-layer dies); both machines at their "
                     "own rates at each point; MTP on HBM at m = 2 as in the batch model")


def design_point(rec, uni, muts, areas):
    out = {}
    for ctx in CONTEXTS:
        row = {}
        for tag, bt in POINTS:
            for mtp in (False, True):
                p = op_point(uni, ctx, A.point_batch(tag, bt, ctx), mtp=mtp, levers=CHAIN_L3, muts=muts,
                             units=POOLED_UNITS)
                row[tag + ("_mtp" if mtp else "")] = dict(
                    batch=A.point_batch(tag, bt, ctx),
                    tokens_s_per_user=p["tokens_s_per_user"], aggregate_tokens_s=p["aggregate_tokens_s"],
                    mfu_array=p["mfu_array"]["all"], mfu_layer_dies=p["mfu_layer_dies"]["all"],
                    busy_fraction_layer_dies=p["busy_fraction_layer_dies"], mbu_rom_port_array=p["mbu_rom_port_array"],
                    mbu_hbm_kv=p["mbu_hbm_kv"], breakdown_us=p["breakdown_us"], binding=p["binding"],
                    concurrent_units=p["concurrent_units"])
        out[str(ctx)] = row
    return dict(label="spec + chain ladder L1-3 + the adopted communication levers (" + ", ".join(rec["adopted_levers"])
                + ") + pooled engines + per-unit concurrency across microbatches; non-layer dies right-sized; MTP m = "
                  "2 at tau 5.0; operate at the 28-user pipeline fill",
                block_area_layer_die_mm2=area_of(uni, areas, pooled=True)["total"],
                block_area_layer_die_mtp_mm2=area_of(uni, areas, pooled=True, lm=MTP_M)["total"], rows=out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    rec = build()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=lambda o: None) + "\n")
    u = rec["utilisation"][str(PRIMARY)]["spec"]
    print("MFU b1 / fill / sat:", [round(u[k]["mfu_array"]["all"], 5) for k in ("b1", "fill28", "sat1024")])
    dp = rec["design_point"]["rows"][str(PRIMARY)]
    print("design point 200K b1 / b1 MTP:", round(dp["b1"]["tokens_s_per_user"]), round(dp["b1_mtp"]["tokens_s_per_user"]))


if __name__ == "__main__":
    main()
