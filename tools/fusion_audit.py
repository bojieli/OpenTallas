#!/usr/bin/env python3
"""FUSION AUDIT (stream FA, 2026-10-01): every operator-fusion opportunity of the four designs, counted on the real
programs and priced as critical-path counterfactuals.

AGENTS.md "Operator fusion" (user decision 2026-10-01) is the rule: dependent operations chain through lane-local
registers; a value goes back to the vector memory only at a chain boundary or a true cross-lane step.  W11's lane-local
fusion pass (claude/w11-fuse tools/w11_su_fuse.py) and W16b's conservative fusion pricing are the BASELINE here; this
audit prices what lies beyond them:

  * the DaVinci/Ascend FixPipe analogue -- a staging buffer at the hub edge where field (matvec), collective, scan and
    hop outputs land, with an epilogue (stream-tap reductions, per-element scale / RoPE / SiLU*up / quantise /
    residual) that delivers into the lanes and hands the scalar to the broadcast;
  * collective fusion (norm partials piggybacked on the all-gather; merged or overlapped collectives);
  * pipeline-hop cut-through; latency hiding by interleaving independent chains; a scalar broadcast H-tree;
  * the contract-changing (class C) options: the norm scalar applied after the matvec, online softmax, gamma folding,
    K-split collectives.

METHOD.
  V4.1 ROM: the product's per-token DAG (tools/uarch_model.py: cons_v41_rom's graph at S = 41, 1.2 GHz SS, BF16 columns,
  the 0.9 GHz serial domain, W11's measured serial build, W18b's shrunk die), re-timed with W11's C_rotate network on
  W18b's compact hub (broadcast 7, operand read 18, element write 17, result 7 slow cycles; +42 an op, +32 a reduction;
  claude/w11-crot v41_vm_crot_stages.json PROVISIONAL, as W16b prices it).  Every candidate is a COUNTERFACTUAL on that
  graph (network legs removed, dependencies rewired) followed by a full longest-path re-solve, so overlap is honoured
  and nothing is added by hand.  AR and the MTP verify pass (6 positions) are both re-solved.
  The real ISA program (tools/hdc_replay_v41.py ShapeBuilder, shipped shape: embed + 40 layers + head, one die; and
  the exact TP-4 layer-0 program with its 12 collectives) gives the op census: which unit produced every stream-unit
  operand, which matvec -> vector patterns dominate, local versus cross-die reductions, and the long tail.
  V4.1 HBM: W19's executed TP-96 program (results/rtl/w19_hbm_tp96_program_oreduce.json) priced with W19's own
  collective formula (W15b P=48 NVLS record) and node prices.
  Qwen3-8B ROM: the calibrated sequencer replay (uarch_model.qwen_tp_point, the product SS point) with the program's
  stream ops removed into producer epilogues (a range: the op removed outright, and the op's pipeline depth added back).
  Qwen3-8B HBM: the reference dependency chain (results/arch/qwen3_budget.json) against the HBM token's cycles.

EXACTNESS CLASSES.  A: the same operations in the same rounding order (free under the contract).  B: the same values by
a different schedule the golden can mirror exactly (e.g. the golden's chunk-8 / RMS_SPLIT tree rebuilt on a stream with
a log-depth stack of partials).  C: changes rounding (needs a contract change and a quality check): a USER DECISION.

Run:  python3 tools/fusion_audit.py [--out results/uarch/fusion_audit.json]
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import uarch_model as U  # noqa: E402

SCHEMA = "opentallas.uarch.fusion_audit.v1"
SLOW_HZ = 0.9e9
S_PRODUCT = 41
# W11 C_rotate on W18b's compact hub (claude/w11-crot results/floorplan/v41_vm_crot_stages.json, PROVISIONAL; W16b's
# VMC_COMPACT / FUSION_C_ROTATE_COMPACT): slow cycles a leg
NET = dict(bcast=7, read=18, write=17, result=7)
VMC_COMPACT = dict(x_gather=8, ret_scatter=7, coll_write=13, su_op_extra=0, su_red_extra=0, su_issue=1.0)
HUB = dict(diameter_um=10735, lane_array_side_um=4890.1, reach_um=748,
           src="W11 crot (bank -> lane worst run 10,735 um at 748 um a stage, W15 0.9 GHz SS reach); "
               "VMC_BLOCK lane_side_um 4,890.1 (uarch_model)")
SU_KINDS = ("vector", "reduce")
PRODUCERS = ("matvec", "collective", "kvscan", "hop")      # outputs that land at the hub edge (staging buffer)
FADD_SLOW = 3                                             # LAT-3 FP32 add, slow cycles
# functions a fixed-function epilogue covers (FixPipe-like): sums / sums of squares / max / absmax trees, multiply by a
# scalar or a constant vector, add, RoPE rotation, SiLU*up, block quantise; everything else is the long tail
FIXED_COVER = ("sumsq", "max", "den", "rsqrt", "scale", "quant", "qdq", "rope", "swiglu", "route_w", "bias",
               "hc_post", "hc_pre", "z_quant", "add")


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------------------------
# V4.1 ROM: the product graph and its counterfactuals
# ---------------------------------------------------------------------------------------------------------------
def product_graph(positions=1, vmh=None):
    """(graph, pass time s) of the product (S = 41) re-timed with the C_rotate compact network's NON-SU terms; the SU
    network legs are left at zero so that each scenario adds its own (uarch_model.cons_v41_rom's re-timing)."""
    plan = U.cons_stage_plan(S_PRODUCT)
    with U._cons_clock(U.PRODUCT_CLOCK_HZ), U._cons_stages(S_PRODUCT):
        d = copy.deepcopy(U.PRESETS["proposal"])
        d["macros"] = round(U.BASE["macros"] * plan["busiest_macros"] / U.cons_stage_plan(28)["busiest_macros"])
        r1, g = U._v41_graph(d, positions)
        T = U._cons_adjust(g, positions, r1["clock_hz"], "columns", U.FIELD_CONCURRENCY,
                           dict(U.SOFTPLUS_FIX, **U.W11_STREAM_SS), (SLOW_HZ, "w18"), None, 7,
                           True, d, U.PRODUCT_SERIAL, U.DIE_SHRUNK_INTERIM, vmh or VMC_COMPACT)
    return g, T


def sink_of(g):
    return [n for n in g.nodes if n.endswith("token.return")][0]


def solve(g, su_order=None):
    """decode_critical_path.Graph.solve's longest path (stream chaining, wire terms) with an optional in-order
    stream-unit constraint: su_order = "pipelined" (an SU op starts once the previous SU op in program order has
    issued) or "blocking" (once it has finished)."""
    fin, start, crit = {}, {}, {}
    prev = None
    for name, n in g.nodes.items():
        deps = n["deps"]
        if deps:
            c = max(deps, key=fin.__getitem__)
            pf, ps = fin[c], max(start[d] for d in deps)
        else:
            c, pf, ps = None, 0.0, 0.0
        su = n["kind"] in SU_KINDS
        floor = 0.0
        if su and su_order and prev is not None:
            floor = (start[prev] + g.nodes[prev]["issue"]) if su_order == "pipelined" else fin[prev]
        iss, dep, ctl = n["issue"], n["depth"], n["ctrl"]
        if n["stream"] and deps:
            s = max(ps + ctl, floor)
            a = s + iss
            f = max(a, pf) + dep
        else:
            s = max(pf + ctl, floor)
            f = s + iss + dep
        wi, wo = n.get("wire_in", 0.0), n.get("wire_out", 0.0)
        if wi or wo:
            s, f = s + wi, f + wi + wo
        fin[name], start[name], crit[name] = f, s, c
        if su:
            prev = name
    path, x = [], sink_of(g)
    while x is not None:
        path.append(x)
        x = crit[x]
    return fin[sink_of(g)], set(path), fin, start


def classes(g):
    """W16b's conservative lane-local classification (head / tail / reduction / RoPE / segmented quantise)."""
    succ = collections.defaultdict(list)
    for k, nd in g.nodes.items():
        for x in nd["deps"]:
            succ[x].append(k)
    out = {}
    for name, nd in g.nodes.items():
        if nd["kind"] not in SU_KINDS:
            continue
        leaf = name.rsplit(".", 1)[-1]
        out[name] = dict(
            head=not nd["deps"] or any(g.nodes[x]["kind"] not in SU_KINDS for x in nd["deps"]),
            tail=not succ[name] or any(g.nodes[x]["kind"] not in SU_KINDS for x in succ[name]),
            red=nd["kind"] == "reduce", rope="rope" in leaf, quant="quant" in leaf or leaf.endswith("qdq"),
            producer_fed=bool(nd["deps"]) and all(g.nodes[x]["kind"] in PRODUCERS for x in nd["deps"]),
            succ=succ[name])
    return out


def fused_extra(c, mode="conservative", drop=()):
    """Slow cycles of the SU network an op pays under lane-local fusion (W16b's rule); `drop` removes legs."""
    rd = NET["read"] if (c["head"] or c["rope"]) else 0
    if "read" in drop or ("rope_read" in drop and c["rope"] and not c["head"]):
        rd = 0
    bc = 0 if "bcast" in drop else NET["bcast"]
    wr = NET["result"] if c["red"] else (NET["write"] if c["tail"] else 0)
    seg = NET["result"] if (c["quant"] and "quant_seg" not in drop) else 0
    if mode == "unfused":
        return NET["bcast"] + NET["read"] + (NET["result"] if c["red"] else NET["write"])
    return bc + rd + wr + seg


def buffer_set(g, cl, fixed_only=False):
    """The staging-buffer epilogue's reach: SU ops all of whose inputs are producer outputs landing at the hub edge or
    other buffer ops (a reduction's scalar included), so the op runs on the stream / in the buffer, not in the lanes.
    fixed_only: only the FixPipe-like function set (FIXED_COVER)."""
    B = set()
    for name, nd in g.nodes.items():
        if name not in cl:
            continue
        leaf = name.rsplit(".", 1)[-1]
        if fixed_only and not any(k in leaf for k in FIXED_COVER):
            continue
        if nd["deps"] and all(g.nodes[x]["kind"] in PRODUCERS or x in B for x in nd["deps"]):
            # a buffer op must be reached from a producer (not only from other buffer scalars of an earlier layer)
            B.add(name)
    return B


def scenario(g0, cl, *, extra, issue_zero=(), rewire=None, stream_kinds=(), su_order=None):
    """Apply per-SU-node network extras (slow cycles), zero the listed nodes' issue, rewire dependencies, mark kinds as
    streaming (cut-through), and re-solve."""
    g = copy.deepcopy(g0)
    for name, c in cl.items():
        g.nodes[name]["depth"] += extra(name, c) / SLOW_HZ
    for name in issue_zero:
        g.nodes[name]["issue"] = 0.0
    if rewire:
        rewire(g)
    for name, nd in g.nodes.items():
        if nd["kind"] in stream_kinds:
            nd["stream"] = True
    T, path, fin, start = solve(g, su_order)
    return T, path, g


def v41_rom():
    rows, census = {}, {}
    for P in (1, U.V41_POSITIONS):
        g0, _ = product_graph(P)
        cl = classes(g0)
        cons = lambda n, c: fused_extra(c)                                   # noqa: E731
        T_unf, _, _ = scenario(g0, cl, extra=lambda n, c: fused_extra(c, "unfused"))
        T_b, path_b, gb = scenario(g0, cl, extra=cons)
        # W16b's own producer -> lane delivery (reference, NOT this audit's): chain heads' VM read leg removed
        T_dl, _, _ = scenario(g0, cl, extra=lambda n, c: fused_extra(c, drop=("read",) if c["head"] and not c["rope"]
                                                                     else ()))
        B = buffer_set(g0, cl)
        Bf = buffer_set(g0, cl, fixed_only=True)

        dl = lambda c: fused_extra(c, drop=("read",) if c["head"] and not c["rope"] else ())   # noqa: E731

        def sb_extra(Bs, deliver=False):
            def ex(n, c):
                if n not in Bs:
                    return dl(c) if deliver else fused_extra(c)
                # in the buffer: no VM read, no per-op control broadcast to the lanes; the result is DELIVERED into
                # the lanes (element write) or, for a scalar, broadcast (7) -- only when a consumer is outside the
                # buffer.  The hub crossing of the delivery stays (root point 3).
                out = [s for s in c["succ"] if s not in Bs]
                if not out:
                    return 0
                return NET["bcast"] if (c["red"] or g0.nodes[n]["issue"] * U.PRODUCT_CLOCK_HZ < 2) else NET["write"]
            return ex
        # buffer reductions run on the stream: their issue overlaps the producer (the tree tail stays in depth); buffer
        # element ops fed straight by a producer stream too; second-pass ops (after the scalar) keep their issue
        first_pass = lambda Bs: [n for n in Bs if all(g0.nodes[x]["kind"] in PRODUCERS or (x in Bs and x in first)  # noqa
                                                      for x in g0.nodes[n]["deps"])]
        first = set()
        for n in g0.nodes:
            if n in B and all(g0.nodes[x]["kind"] in PRODUCERS or x in first for x in g0.nodes[n]["deps"]) \
                    and not any(x in B and g0.nodes[x]["kind"] == "reduce" for x in g0.nodes[n]["deps"]):
                first.add(n)
        T_sb, path_sb, _ = scenario(g0, cl, extra=sb_extra(B), issue_zero=[n for n in B if n in first])
        # CUMULATIVE LEVELS (AGENTS.md a4f314fb): L2 = W16b's delivery + the buffer's element epilogue (first-pass,
        # non-reduction ops); L3 = + stream reductions and the scalar's second pass; L5 = + piggyback + hop cut-through
        Bel = {n for n in first if not cl[n]["red"]}
        T_L2, _, _ = scenario(g0, cl, extra=sb_extra(Bel, True), issue_zero=sorted(Bel))
        T_L3, _, _ = scenario(g0, cl, extra=sb_extra(B, True), issue_zero=[n for n in B if n in first])
        T_L3f, _, _ = scenario(g0, cl, extra=sb_extra(Bf, True), issue_zero=[n for n in Bf if n in first])
        T_sbf, _, _ = scenario(g0, cl, extra=sb_extra(Bf), issue_zero=[n for n in Bf if n in first])
        # reductions only (the producer-side reduction tap without the element epilogue)
        Br = {n for n in B if cl[n]["red"]}
        T_sbr, _, _ = scenario(g0, cl, extra=sb_extra(Br), issue_zero=[n for n in Br if n in first])
        # RoPE pair co-location and the block-absmax on the stream (lane layout; A)
        T_rope, _, _ = scenario(g0, cl, extra=lambda n, c: fused_extra(c, drop=("rope_read",)))
        T_qseg, _, _ = scenario(g0, cl, extra=lambda n, c: fused_extra(c, drop=("quant_seg",)))

        # collective piggyback: a sum of squares fed by an all-gather runs on each die's own slice BEFORE the gather
        # (the slice is a subtree of the golden's split tree: RMS_SPLIT = 8 segments, 2 a die at TP-4), its scalar
        # partial rides the gather, and the consumer combines 4 partials (2 adder levels) after it
        piggy = [n for n, c in cl.items() if c["red"] and len(g0.nodes[n]["deps"]) == 1
                 and g0.nodes[g0.nodes[n]["deps"][0]]["kind"] == "collective"
                 and g0.nodes[g0.nodes[n]["deps"][0]].get("op", "all_gather") != "all_reduce"]

        def rw_piggy(g):
            for n in piggy:
                coll = g.nodes[n]["deps"][0]
                src = list(g.nodes[coll]["deps"])
                g.nodes[n]["deps"] = src
                g.nodes[n]["issue"] /= 4
                for s in cl[n]["succ"]:
                    if coll not in g.nodes[s]["deps"]:
                        g.nodes[s]["deps"] = list(g.nodes[s]["deps"]) + [coll]
                    g.nodes[s]["depth"] += 2 * FADD_SLOW / SLOW_HZ
        T_pig, _, _ = scenario(g0, cl, extra=cons, rewire=rw_piggy)
        # pipeline-hop cut-through: the activation streams to the next stage as it is produced
        T_hop, _, _ = scenario(g0, cl, extra=cons, stream_kinds=("hop",))
        # interleaving: the model's DAG overlaps independent chains freely; the in-order stream unit does not
        T_pipe, _, _ = scenario(g0, cl, extra=cons, su_order="pipelined")
        T_blk, _, _ = scenario(g0, cl, extra=cons, su_order="blocking")

        def chain_root(g, x):
            # walk back from a quant / scale to the reduction's input (the un-normalised x)
            seen = x
            while seen in cl and not cl[seen]["red"]:
                ds = [d for d in g.nodes[seen]["deps"] if d in cl]
                if not ds:
                    break
                seen = ds[0]
            return seen if seen in cl and cl[seen]["red"] else None

        # CLASS C: the norm scalar after the matvec (the matvec starts on the un-normalised x; rstd scales its output)
        normed = {}
        for n, nd in g0.nodes.items():
            if nd["kind"] != "matvec":
                continue
            for dname in nd["deps"]:
                leaf = dname.rsplit(".", 1)[-1]
                if dname in cl and (leaf.endswith("quant") or dname.endswith("norm.scale")):
                    normed[n] = dname
        normed = {mv: q for mv, q in normed.items() if chain_root(g0, q)}
        def rw_late(g):
            for mv, q in normed.items():
                red = chain_root(g, q)
                if not red:
                    continue
                rs = [s for s in cl[red]["succ"] if s.endswith("rsqrt")]
                g.nodes[mv]["deps"] = [d for d in g.nodes[mv]["deps"] if d != q] + list(g.nodes[red]["deps"])
                if cl[q]["quant"]:      # the FP8 block quantise of the raw x stays in front of the matvec
                    g.nodes[mv]["depth"] += g0.nodes[q]["issue"] + g0.nodes[q]["depth"] + fused_extra(cl[q]) / SLOW_HZ
                succs = [s for s, nd in g.nodes.items() if mv in nd["deps"]]
                for s in succs:
                    g.nodes[s]["deps"] = list(g.nodes[s]["deps"]) + rs
                    g.nodes[s]["depth"] += FADD_SLOW / SLOW_HZ
        T_late, _, _ = scenario(g0, cl, extra=cons, rewire=rw_late)
        # CLASS C: online softmax (exp no longer waits for the max over the whole selected set)
        def rw_online(g):
            for n, nd in g.nodes.items():
                if n.endswith(".attn.exp"):
                    nd["deps"] = [d.replace(".attn.max", ".attn.scores") for d in nd["deps"]]
                    nd["depth"] += 2 * FADD_SLOW / SLOW_HZ      # the running-max rescale
        T_onl, _, _ = scenario(g0, cl, extra=cons, rewire=rw_online)
        # combined A/B: buffer + piggyback + RoPE pairs + hop cut-through (re-solved together)
        T_all, path_all, _ = scenario(g0, cl, extra=lambda n, c: (sb_extra(B, True)(n, c) if n in B else
                                                                  dl(c)),
                                      issue_zero=[n for n in B if n in first], rewire=rw_piggy,
                                      stream_kinds=("hop",))
        T_allc, _, _ = scenario(g0, cl, extra=lambda n, c: (sb_extra(B, True)(n, c) if n in B else dl(c)),
                                issue_zero=[n for n in B if n in first],
                                rewire=lambda g: (rw_piggy(g), rw_late(g), rw_online(g)), stream_kinds=("hop",))
        key = "ar" if P == 1 else "mtp_pass"
        T_L5p, _, _ = scenario(g0, cl, extra=lambda n, c: (sb_extra(B, True)(n, c) if n in B else dl(c)),
                               issue_zero=[n for n in B if n in first], rewire=rw_piggy)
        rows[key + "_levels"] = dict(L0_unfused_us=T_unf * 1e6, L1_lane_local_us=T_b * 1e6,
                                     L2_delivery_only_us=T_dl * 1e6, L2_delivery_plus_element_epilogue_us=T_L2 * 1e6,
                                     L3_stream_reductions_us=T_L3 * 1e6, L3_fixed_function_only_us=T_L3f * 1e6,
                                     L5_plus_piggyback_us=T_L5p * 1e6, L5_plus_piggyback_and_hops_us=T_all * 1e6,
                                     L4_in_order_pipelined_exposure_us=T_pipe * 1e6,
                                     L4_in_order_blocking_exposure_us=T_blk * 1e6,
                                     L6_C_plus_norm_after_matvec_and_online_softmax_us=T_allc * 1e6)
        rows[key] = dict(unfused_us=T_unf * 1e6, baseline_fused_us=T_b * 1e6, w16b_delivery_us=T_dl * 1e6,
                         staging_buffer_us=T_sb * 1e6, staging_buffer_fixed_function_us=T_sbf * 1e6,
                         staging_buffer_reductions_only_us=T_sbr * 1e6, rope_pairs_us=T_rope * 1e6,
                         quant_block_absmax_us=T_qseg * 1e6, norm_partial_piggyback_us=T_pig * 1e6,
                         hop_cut_through_us=T_hop * 1e6, in_order_su_pipelined_us=T_pipe * 1e6,
                         in_order_su_blocking_us=T_blk * 1e6, C_norm_after_matvec_us=T_late * 1e6,
                         C_online_softmax_us=T_onl * 1e6, combined_AB_us=T_all * 1e6,
                         combined_AB_plus_C_us=T_allc * 1e6)
        if P == 1:
            heads = [n for n, c in cl.items() if c["head"]]
            reds = [n for n, c in cl.items() if c["red"]]
            on = lambda xs, p=path_b: sum(1 for x in xs if x in p)               # noqa: E731
            fam = lambda xs: dict(collections.Counter(x.split(".", 1)[1] if x[0] in "LE" and "." in x else x  # noqa
                                                      for x in xs).most_common())
            census = dict(
                su_ops=len(cl), vector=sum(1 for c in cl.values() if not c["red"]), reductions=len(reds),
                chain_starts=len(heads), chain_ends=sum(1 for c in cl.values() if c["tail"] and not c["red"]),
                rope=sum(1 for c in cl.values() if c["rope"]), quant=sum(1 for c in cl.values() if c["quant"]),
                lane_local_chained=sum(1 for c in cl.values() if not (c["head"] or c["red"] or c["rope"] or c["quant"]
                                                                       or c["tail"])),
                on_baseline_critical_path=dict(su_ops=on(cl), chain_starts=on(heads), reductions=on(reds)),
                staging_buffer=dict(
                    ops=len(B), ops_on_path=on(B), fixed_function_ops=len(Bf), long_tail_ops=len(B - Bf),
                    long_tail_families=fam(B - Bf),
                    chain_starts_removed=sum(1 for n in heads if n in B),
                    chain_starts_removed_frac=round(sum(1 for n in heads if n in B) / len(heads), 3),
                    chain_starts_removed_fixed=sum(1 for n in heads if n in Bf),
                    reductions_removed=sum(1 for n in reds if n in B),
                    reductions_removed_frac=round(sum(1 for n in reds if n in B) / len(reds), 3),
                    reductions_removed_fixed=sum(1 for n in reds if n in Bf),
                    reduction_families=fam([n for n in reds if n in B]),
                    families=fam(B), producer_kinds=dict(collections.Counter(
                        g0.nodes[x]["kind"] for n in B for x in g0.nodes[n]["deps"] if x not in B)),
                    reductions_cross_die=sum(1 for n in reds if n in B and any(
                        g0.nodes[x]["kind"] == "collective" for x in g0.nodes[n]["deps"])),
                    reductions_local=sum(1 for n in reds if n in B and not any(
                        g0.nodes[x]["kind"] == "collective" for x in g0.nodes[n]["deps"])),
                    reductions_after_one_elementwise=sum(1 for n in reds if n in B and any(
                        x in B for x in g0.nodes[n]["deps"]))),
                cdc_fifo_as_buffer=dict(
                    producer_to_buffer_edges_on_path=sum(1 for n in first if n in path_b),
                    us_upper=round(sum(1 for n in first if n in path_b) * U.CDC_W18["fast_to_slow_slow_cycles"]
                                   / SLOW_HZ * 1e6, 2),
                    note="if the staging buffer IS the 1.2 -> 0.9 GHz ratio FIFO, each producer -> buffer edge stops "
                         "paying a separate crossing (W18: 3.0-3.75 slow cycles, charged 4); an upper bound, not "
                         "re-solved"),
                piggyback_reductions=len(piggy), piggyback_on_path=on(piggy), piggyback_families=fam(piggy),
                norm_after_matvec_instances=len(normed), norm_after_matvec_families=fam(list(normed)),
                hops=sum(1 for nd in g0.nodes.values() if nd["kind"] == "hop"),
                hops_on_path=on([n for n, nd in g0.nodes.items() if nd["kind"] == "hop"]),
                online_softmax_instances=sum(1 for n in g0.nodes if n.endswith(".attn.exp")),
                independent_work=independent_work(gb, path_b))
    return rows, census


def independent_work(g, path):
    """Stream-unit time per layer on and off the critical path (the independent chains a scheduler can interleave)."""
    per = collections.defaultdict(lambda: dict(on=0.0, off=0.0, ops_off=0))
    for n, nd in g.nodes.items():
        if nd["kind"] not in SU_KINDS or not n.startswith("L"):
            continue
        L = n.split(".", 1)[0]
        t = (nd["issue"] + nd["depth"]) * 1e6
        if n in path:
            per[L]["on"] += t
        else:
            per[L]["off"] += t
            per[L]["ops_off"] += 1
    on = sum(v["on"] for v in per.values())
    off = sum(v["off"] for v in per.values())
    L20 = per.get("L20", {})
    off20 = sorted(((n.split(".", 1)[1], round((nd["issue"] + nd["depth"]) * 1e9, 1)) for n, nd in g.nodes.items()
                    if n.startswith("L20.") and nd["kind"] in SU_KINDS and n not in path), key=lambda x: -x[1])
    return dict(su_us_on_path=round(on, 2), su_us_off_path=round(off, 2), off_to_on=round(off / on, 2),
                layer20=dict(on_us=round(L20.get("on", 0), 3), off_us=round(L20.get("off", 0), 3),
                             off_path_ops_ns=off20[:16]))


# ---------------------------------------------------------------------------------------------------------------
# V4.1 ROM: the real ISA program census (who produced each stream-unit operand)
# ---------------------------------------------------------------------------------------------------------------
UNIT_NAME = {0: "CTL", 1: "ME", 2: "SU", 3: "QE", 4: "XU", 5: "HE", 6: "COLL"}


def isa_programs():
    import hdc_isa_v41 as I
    import hdc_replay_v41 as R
    out = {}
    for tp in (False, True):
        lay = R.ShapeLayout(R.SHIPPED, tp_exact=tp)
        old = I.SU_LANES
        I.SU_LANES = 8
        try:
            b = R.ShapeBuilder(lay, True)
            out["tp4_layer0" if tp else "tp1_full"] = b.build(layers=[0], head=False) if tp else b.build()
        finally:
            I.SU_LANES = old
    return out


def su_kind(f):
    import hdc_isa_v41 as I
    red = f.get("red", 0)
    if red:
        return {I.RED_SUM: "sumsq" if f.get("red_sq") else "sum", I.RED_MAX: "max", I.RED_SEQ: "seqsum"}[red]
    sfu = f.get("sfu", 0)
    if sfu:
        return {I.SFU_EXP: "exp", I.SFU_RSQRT: "rsqrt", I.SFU_SQRT: "sqrt", I.SFU_SIGM: "sigmoid",
                I.SFU_SILU: "silu*up", I.SFU_SPSQRT: "softplus_sqrt", I.SFU_EGATE: "engram_gate"}[sfu]
    if f.get("qm", 0) in (I.QM_ALT_NP, I.QM_ALT_PN):
        return "rope"
    if f.get("dst", 0) in (I.DST_KV, I.DST_KVT):
        return "kv_write"
    if f.get("m1", 0) in (I.M1_DIVB, I.M1_DIVIMM):
        return "divide"
    if f.get("e1", 0) in (I.E1_MULC, I.E1_MULIMM) or f.get("m1", 0) == I.M1_AB:
        return "scale"
    if f.get("ad", 0) in (I.AD_C, I.AD_Q, I.AD_D, I.AD_NEGB) or f.get("qm", 0):
        return "add/mix"
    return "move/round"


def census_program(prog):
    """Per stream-unit op: the unit that last wrote each region it reads; matvec -> SU pattern counts."""
    last_w = {}
    pat = collections.Counter()
    first_after = collections.Counter()
    tags = collections.Counter()
    by_prod = collections.Counter()
    tail_tag = collections.Counter()
    n_su = 0
    for f in prog:
        u = UNIT_NAME[f["unit"]]
        if u == "SU":
            n_su += 1
            prods = sorted({last_w.get(r, ("init", None))[0] for r in f["_reads"]})
            src = ("matvec" if any(p in ("QE", "ME", "HE") for p in prods) else
                   "collective" if "COLL" in prods else "select/sinkhorn/gather" if "XU" in prods else
                   "stream unit" if "SU" in prods else "constant/initial")
            k = su_kind(f)
            pat[f"{src} -> {k}"] += 1
            by_prod[src] += 1
            tag = f["_tag"].split(".", 1)[-1]
            tags[tag] += 1
            if src in ("matvec", "collective"):
                first_after[k] += 1
                tail_tag[tag] += 1
        for r in f["_writes"]:
            last_w[r] = (u, f)
    return dict(su_ops=n_su, by_operand_producer=dict(by_prod.most_common()),
                patterns=dict(pat.most_common(40)), producer_fed_op_kinds=dict(first_after.most_common()),
                producer_fed_tags=dict(tail_tag.most_common()), tags=dict(tags.most_common()))


def tp4_reduction_placement(prog):
    """Every reduction of the exact TP-4 layer-0 program: local (its operand is this die's own matvec output) or
    cross-die (an all-gather / all-reduce lies between the matvec and the reduction)."""
    last_w = {}
    out = []
    for f in prog:
        u = UNIT_NAME[f["unit"]]
        if u == "SU" and f.get("red", 0):
            src = sorted({last_w.get(r, ("init",))[0] for r in f["_reads"]})
            out.append(dict(tag=f["_tag"], kind=su_kind(f), operand_writers=src,
                            placement=("cross-die (after the collective)" if "COLL" in src else
                                       "local (matvec output)" if any(s in ("QE", "ME", "HE") for s in src) else
                                       "local (stream-unit / replicated residual)")))
        for r in f["_writes"]:
            last_w[r] = (u,)
    return out


# ---------------------------------------------------------------------------------------------------------------
# V4.1 HBM (W19's executed TP-96 program)
# ---------------------------------------------------------------------------------------------------------------
W19_PROG = "results/rtl/w19_hbm_tp96_program_oreduce.json"
W19_AR = "results/uarch/w19_hbm_token_ar.json"
W19_MTP = "results/uarch/w19_hbm_token_mtp.json"
TP96 = 96
F_FAST, F_SER = 1.2e9, 0.9e9
SU_BASE_NS = 29 / 1.0339e9 * 1e9


def w19_coll_us(op, coll, P):
    """W19's prod_us (claude/w19-hbm-token tools/w19_hbm_token_compose.py), without the top-k select term."""
    hz, slot = coll["hz"], coll["slot"]
    if op["kind"] == "all_reduce":
        n = math.ceil(P * op["bytes"] / slot)
        return (coll["ar"]["fixed_cycles"] + coll["ar"]["cycles_per_word"] * n) / hz * 1e6
    per_rank = P * op["bytes"] / TP96
    return (coll["ag"]["fixed_cycles"] + coll["ag"]["cycles_per_word"] * math.ceil(per_rank / slot)) / hz * 1e6


def v41_hbm():
    prog = json.loads((ROOT / W19_PROG).read_text())
    ar = json.loads((ROOT / W19_AR).read_text())["result"]
    mtp = json.loads((ROOT / W19_MTP).read_text())["result"]
    coll = ar["collective_model"]
    nodes = ar["dedicated"]["node_ns"]
    tags = collections.Counter()
    per = {1: collections.Counter(), 6: collections.Counter()}
    for lay in prog["layers"]:
        for op in lay["ops"]:
            if op["kind"] in ("all_gather", "all_reduce", "topk_merge", "kv_gather"):
                t = op["tag"]
                if t.startswith(("engram.", "candidate merge")):
                    continue
                key = t.split(" (")[0]
                tags[key] += 1
                for P in (1, 6):
                    per[P][key] += w19_coll_us(op, coll, P)
    fixed_ag = coll["ag"]["fixed_cycles"] / coll["hz"] * 1e6
    ser = F_FAST / F_SER
    L = len(prog["layers"])
    # H1: all-gather + hc_post + hc_pre + norm sum-of-squares partial (TRT-LLM's fused all-reduce + residual + RMSNorm,
    # on a gather): each rank does hc_post / hc_pre / the sum of squares on its own slice before the gather and the
    # scalar partial rides the payload; after the gather only rsqrt / scale / quant remain on the path
    h1_inst = tags.get("attn_out_gather", 0) + tags.get("ffn_out_gather", 0)
    h1_ns = (73.5 + 42.6 + 74.5 - 74.5) * ser            # hc_post + hc_pre + sumsq leave the path; ~one pass stays
    # H2: merge expert_intermediate_gather + ffn_out_gather into one all-reduce (w2 K-split): -1 collective a layer
    h2_inst = min(tags.get("expert_intermediate_gather", 0), tags.get("ffn_out_gather", 0))
    h2_ar = sum(per[1][k] for k in ("expert_intermediate_gather", "ffn_out_gather")) / max(1, h2_inst)
    ar_one = (coll["ar"]["fixed_cycles"] + coll["ar"]["cycles_per_word"] * math.ceil(20480 / coll["slot"])) / coll["hz"] * 1e6
    ar_six = (coll["ar"]["fixed_cycles"] + coll["ar"]["cycles_per_word"] * math.ceil(6 * 20480 / coll["slot"])) / coll["hz"] * 1e6
    h2_mtp = sum(per[6][k] for k in ("expert_intermediate_gather", "ffn_out_gather")) / max(1, h2_inst)
    # H3: overlap the router gather with the shared expert (independent of the routing) -- bounded by the shared
    # expert's SM work; the per-layer SM total is W19's (sm / layers), the shared expert's share 2 of ~19 matvec issues
    sm_layer = ar["parts_us"]["sm"] / L
    h3 = min(per[1]["router_gather"] / max(1, tags["router_gather"]), sm_layer * 2 / 19) * tags["router_gather"]
    # H5: SM epilogue (Blackwell TMEM + register epilogue): the head ops that read an MMA result through shared
    # memory lose the pass's base latency (SU_BASE) -- swiglu x route, z_quant, q RoPE, softplus_sqrt (W19 classes)
    heads_layer = 4
    h5 = L * heads_layer * SU_BASE_NS * ser / 1e3
    out = dict(
        source=dict(program=W19_PROG, ar=W19_AR, mtp=W19_MTP, collective_model=coll["source"]),
        ar_us=ar["total_us"], mtp_pass_us=mtp["total_us"], parts_us_ar=ar["parts_us"], parts_us_mtp=mtp["parts_us"],
        collectives_on_path=ar["collectives_on_path"], collectives_by_tag=dict(tags.most_common()),
        collective_us_by_tag_ar={k: round(v, 2) for k, v in per[1].most_common()},
        collective_us_by_tag_mtp={k: round(v, 2) for k, v in per[6].most_common()},
        fixed_latency_us_per_gather=round(fixed_ag, 3),
        candidates=[
            dict(id="H1", name="all-gather + hc_post + hc_pre + norm sum-of-squares partial piggybacked (TRT-LLM fused "
                               "all-reduce + residual + RMSNorm, on the gather)",
                 instances=h1_inst, ar_us_saved=round(h1_inst * h1_ns / 1e3, 1),
                 mtp_us_saved=round(h1_inst * h1_ns / 1e3 * U_REPEAT(6), 1), cls="B*",
                 exactness="hc_post / hc_pre are element-wise (A); the sum of squares is B only if each rank's slice "
                           "is a subtree of the golden's split tree -- 5,120 / 96 is not an integer, so the rank slices "
                           "must be re-cut to tree-aligned runs or each rank sends several subtree partials; otherwise C",
                 gpu_precedent="TensorRT-LLM AllReduce+residual+RMSNorm fusion; NVLS"),
            dict(id="H2", name="merge expert_intermediate_gather + ffn_out_gather into one all-reduce (w2 K-split over "
                               "ranks)", instances=h2_inst,
                 ar_us_saved=round(h2_inst * (h2_ar - ar_one), 1), mtp_us_saved=round(h2_inst * (h2_mtp - ar_six), 1),
                 cls="C", exactness="the FP4 w2's blocks accumulate sequentially from +0 in the golden; a K-split "
                                    "across ranks re-associates them -- a contract change", gpu_precedent="Megatron "
                                    "row-parallel down projection"),
            dict(id="H3", name="overlap the router gather with the shared expert's matvecs (stream overlap)",
                 instances=tags["router_gather"], ar_us_saved=round(h3, 1), mtp_us_saved=round(h3, 1), cls="A",
                 exactness="schedule only", gpu_precedent="CUDA streams / persistent-kernel overlap"),
            dict(id="H4", name="different parallel split (EP + smaller TP, TP-48) at equal cost", instances=0,
                 ar_us_saved=0.0, mtp_us_saved=0.0, cls="A",
                 exactness="no change in count: the 6 collectives a layer are re-sharding points (a projection gather, "
                           "the o-group reduce, two output gathers, the router gather, the expert intermediates); EP "
                           "replaces the two expert gathers by a dispatch and a combine (same count) and TP-48 keeps the "
                           "NVLS fixed latency (~0.78 us of a ~1.07 us average)"),
            dict(id="H5", name="TMEM-style accumulator + register epilogue in the SM (SwiGLU x route weight, z_quant, "
                               "q RoPE, softplus_sqrt on the MMA output)", instances=L * heads_layer,
                 ar_us_saved=round(h5, 1), mtp_us_saved=round(h5 * U_REPEAT(6), 1), cls="A",
                 exactness="same element operations, same rounding points", gpu_precedent="Blackwell TMEM + CUTLASS "
                                                                                        "epilogue fusion"),
        ])
    return out


def U_REPEAT(P):
    """W19's LOCAL_REPEAT: each extra verify position repeats a local step's issue fraction."""
    return 1.0 + (P - 1) * (95.955 / 103.253 / 5)


# ---------------------------------------------------------------------------------------------------------------
# Qwen3-8B ROM (the calibrated replay with stream ops folded into producer epilogues) and HBM
# ---------------------------------------------------------------------------------------------------------------
def qwen_rom():
    import hdc_program as P
    import hdc_isa as I
    import hdc_timing as T
    orig = P.build_program
    cap = {}

    def classify(prog):
        """Per layer, the stream ops between matrix-engine ops (the as-built program order)."""
        segs, cur, after = [], [], None
        for i, f in enumerate(prog):
            if f["unit"] == I.UNIT_ME:
                segs.append((after, cur))
                cur, after = [], i
            elif f["unit"] == I.UNIT_SU:
                cur.append(i)
        segs.append((after, cur))
        return segs

    def kinds(f):
        if f.get("red") and f.get("red_sq"):
            return "residual+sumsq" if f.get("ad") else "sumsq"
        if f.get("red"):
            return "softmax(exp+sum)"
        if f.get("sfu") == I.SFU_RSQRT:
            return "rsqrt"
        if f.get("sfu") == I.SFU_RECIP:
            return "recip"
        if f.get("sfu") == I.SFU_SIGM:
            return "silu*up"
        if f.get("mb"):
            return "rope"
        if f.get("dst") == 2:
            return "scale->kv"
        return "scale"

    def run(drop=frozenset(), add_back=0):
        def wrapped(*a, **k):
            prog = orig(*a, **k)
            cap["prog"] = prog
            # a folded op keeps its place, waits and barriers (the dependency it carries) but costs one trivial
            # element: the producer's epilogue did its work on the stream
            return [dict(f, su_nout=1, su_nin=1, su_d_nout=0, su_d_nin=0, red=0, red_sq=0, sfu=0) if i in drop else f
                    for i, f in enumerate(prog)]
        P.build_program = wrapped
        try:
            p = U.qwen_tp_point(4, 6144, "board", clock_hz=U.PRODUCT_CLOCK_HZ, me_lat_extra=U.QWEN_SS["me_lat_extra"])
        finally:
            P.build_program = orig
        return p["cycles"] + add_back
    base = run()
    prog = cap["prog"]
    me_after = {}
    for after, ops in classify(prog):
        for i in ops:
            me_after[i] = after
    kind = {i: kinds(prog[i]) for i in me_after}
    me_rows = lambda i: prog[me_after[i]].get("me_nout", 0) if me_after[i] is not None else -1   # noqa: E731
    k = T.K
    sets = {
        "Q1 gate/up epilogue: rstd scale + SiLU*up on the ME output": (
            {i for i in kind if kind[i] in ("scale", "silu*up") and me_rows(i) == 6144},
            k["su_depth"][I.SFU_SIGM] + 3),
        "Q2 qkv epilogue: per-head q/k-norm sum-of-squares tap + rsqrt + scale + RoPE (+ v scale to KV)": (
            {i for i in kind if kind[i] in ("sumsq", "rsqrt", "scale", "rope", "scale->kv") and me_rows(i) == 1536},
            k["red_tail_vec"] + k["su_depth"][I.SFU_RSQRT] + 6),
        "Q3 p.v epilogue: reciprocal + normalise": (
            {i for i in kind if kind[i] in ("recip", "scale") and prog[me_after[i]].get("me_wsrc")
             and not prog[me_after[i]].get("me_d_tiles")}, k["su_depth"][I.SFU_RECIP] + 3),
        "Q4 o / down output: residual add + sum of squares in the all-reduce delivery": (
            {i for i in kind if kind[i] == "residual+sumsq"}, k["red_tail"]),
        "Q5 scores epilogue: exp + running sum (two-pass max kept)": (
            {i for i in kind if kind[i] == "softmax(exp+sum)"}, k["su_depth"][I.SFU_EXP] + k["red_tail"]),
    }
    clock = U.PRODUCT_CLOCK_HZ
    rate = lambda c: round(clock / c * U.QWEN_SS["droop_rate"], 1)          # noqa: E731
    cands = []
    alln = set()
    for name, (drop, depth) in sets.items():
        layers = 36
        per_layer = len(drop) // layers if layers else 0
        hi = run(frozenset(drop))
        lo = run(frozenset(drop), add_back=depth * layers)
        alln |= drop
        cands.append(dict(name=name, ops_removed=len(drop), per_layer=per_layer,
                          saved_cycles_range=[base - lo, base - hi],
                          tokens_s_range=[rate(lo), rate(hi)]))
    allc = run(frozenset(alln))
    allc_lo = run(frozenset(alln), add_back=sum(depth * 36 for _, depth in sets.values()))
    return dict(source="uarch_model.qwen_tp_point(4, 6144, 'board', SS, me_lat_extra) replay; program hdc_program."
                       "build_program at this commit", baseline_cycles=base, baseline_tokens_s=rate(base),
                su_ops=sum(1 for f in prog if f["unit"] == I.UNIT_SU), me_ops=sum(1 for f in prog if f["unit"] == I.UNIT_ME),
                kinds=dict(collections.Counter(kind.values()).most_common()),
                note="the Qwen layer program already applies the norm scalar AFTER the matvec (norm_fold: the qkv and "
                     "gate/up matvecs start on the un-normalised x; INT8 rows norm-folded) -- candidate 8's class-C "
                     "change is already in the Qwen contract",
                candidates=cands, all_folded=dict(cycles_range=[allc_lo, allc], saved_range=[base - allc_lo, base - allc],
                                                  tokens_s_range=[rate(allc_lo), rate(allc)]),
                method="a folded stream op is replaced in place by a one-element op (keeping its waits / barriers); "
                       "the range's low end adds the epilogue's pipeline depth back once per layer instance")


def qwen_hbm():
    rec = json.loads((ROOT / "results/arch/qwen3_budget.json").read_text())
    st = rec["dependency_chain"]["8192/spec_widths_reference_graph"]["stages"]
    hb = json.loads((ROOT / "results/uarch/hbm_gpu.json").read_text())["designs"]["qwen"]
    tot = hb["sm_count_sweep"][-1]["cycles"]
    fusable = ("attn_norm.scale", "qk_norm.sumsq", "qk_norm.rsqrt", "qk_norm.scale", "rope", "softmax.recip",
               "softmax.scale", "residual+sumsq", "ffn_norm.scale", "silu_mul")
    per_layer = sum(s["exposed_latency"] for s in st if s["stage"] in fusable)
    return dict(source="results/arch/qwen3_budget.json dependency_chain 8192/spec_widths_reference_graph; "
                       "results/uarch/hbm_gpu.json designs.qwen sm_count_sweep (token cycles at the SM count plateau)",
                token_cycles=tot, epilogue_fusable_stage_cycles_per_layer=per_layer,
                upper_bound_saved_frac=round(36 * per_layer / tot, 4),
                note="the Qwen HBM token is HBM-bandwidth bound (~1.25 M cycles a token); every epilogue / AR+norm "
                     "fusion together removes at most this fraction of the dependent latency, all class A or B "
                     "(TRT-LLM / CUTLASS precedents)")


# ---------------------------------------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/uarch/fusion_audit.json")
    a = ap.parse_args(argv)
    rows, census = v41_rom()
    progs = isa_programs()
    isa = dict(tp1_full=census_program(progs["tp1_full"]), tp4_layer0=census_program(progs["tp4_layer0"]),
               tp4_layer0_reductions=tp4_reduction_placement(progs["tp4_layer0"]))
    rec = dict(schema=SCHEMA, v41_rom=dict(rows=rows, graph_census=census, isa_census=isa),
               v41_hbm=v41_hbm(), qwen_rom=qwen_rom(), qwen_hbm=qwen_hbm(), net_legs_slow_cycles=NET, hub=HUB)
    rec["v41_rom"]["ranked"] = rank_v41(rows, census)
    rec["source_sha256"] = {p: sha(p) for p in ("tools/fusion_audit.py", "tools/uarch_model.py",
                                                "tools/hdc_replay_v41.py", "tools/hdc_program_v41.py",
                                                W19_PROG, W19_AR, W19_MTP, "results/arch/qwen3_budget.json")}
    txt = json.dumps(_round(rec), indent=1) + "\n"
    (ROOT / a.out).write_text(txt)
    print(json.dumps(_round(dict(rows=rows, ranked=rec["v41_rom"]["ranked"])), indent=1))


def rank_v41(rows, census):
    ar, mp = rows["ar"], rows["mtp_pass"]
    lv = []
    for k in rows["ar_levels"]:
        T1, Tp = rows["ar_levels"][k], rows["mtp_pass_levels"][k]
        lv.append(dict(step=k, ar_us=T1, ar_tokens_s=1e6 / T1, mtp_pass_us=Tp,
                       mtp_tokens_s=U.V41_TAU / ((Tp + U.V41_DRAFT_FRACTION * T1) * 1e-6)))
    b, bm = ar["baseline_fused_us"], mp["baseline_fused_us"]
    td = lambda: U.V41_DRAFT_FRACTION * b                                 # noqa: E731
    mtp_rate = lambda Tp, T1: U.V41_TAU / ((Tp + U.V41_DRAFT_FRACTION * T1) * 1e-6)   # noqa: E731
    base_mtp = mtp_rate(bm, b)
    out = []
    for key, name, cls in (
            ("staging_buffer_us", "staging buffer + epilogue (FixPipe analogue), programmable", "A/B"),
            ("staging_buffer_fixed_function_us", "staging buffer, fixed-function epilogue only", "A/B"),
            ("staging_buffer_reductions_only_us", "producer-side reduction tap only", "B"),
            ("norm_partial_piggyback_us", "norm sum-of-squares partials piggybacked on the all-gather", "B"),
            ("hop_cut_through_us", "pipeline-hop cut-through", "A"),
            ("rope_pairs_us", "RoPE pairs co-located in a lane", "A"),
            ("quant_block_absmax_us", "block absmax on the stream (no segmented tree)", "A"),
            ("w16b_delivery_us", "REFERENCE (W16b): producer -> lane delivery", "A"),
            ("combined_AB_us", "COMBINED levels 2-5 (delivery + buffer + piggyback + hop cut-through)", "A/B"),
            ("C_norm_after_matvec_us", "C: norm scalar after the matvec", "C"),
            ("C_online_softmax_us", "C: online softmax", "C"),
            ("combined_AB_plus_C_us", "COMBINED A/B + C", "C")):
        T1, Tp = ar[key], mp[key]
        out.append(dict(candidate=name, cls=cls, ar_us_saved=b - T1, ar_tokens_s=1e6 / T1,
                        ar_gain_pct=100 * (b / T1 - 1), mtp_pass_us_saved=bm - Tp,
                        mtp_tokens_s=mtp_rate(Tp, T1), mtp_gain_pct=100 * (mtp_rate(Tp, T1) / base_mtp - 1)))
    out.sort(key=lambda r: -r["ar_us_saved"])
    return dict(levels=lv, baseline=dict(ar_us=b, ar_tokens_s=1e6 / b, mtp_pass_us=bm, mtp_tokens_s=base_mtp,
                              unfused_ar_tokens_s=1e6 / ar["unfused_us"]),
                interleaving=dict(dag_us=b, in_order_pipelined_us=ar["in_order_su_pipelined_us"],
                                  in_order_blocking_us=ar["in_order_su_blocking_us"],
                                  exposure_pipelined_pct=100 * (ar["in_order_su_pipelined_us"] / b - 1),
                                  exposure_blocking_pct=100 * (ar["in_order_su_blocking_us"] / b - 1)),
                candidates=out)


def _round(x):
    if isinstance(x, float):
        return round(x, 3)
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v) for v in x]
    return x


if __name__ == "__main__":
    main()
