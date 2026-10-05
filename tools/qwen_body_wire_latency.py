#!/usr/bin/env python3
"""Qwen3-8B ROM TP4: where the non-collective layer body spends its cycles, and what wire-stage and
collective-fusion levers could recover (model only; no RTL, no P&R).

Inputs (all sha256-pinned in the record, copied under results/uarch/qwen_body_wire_latency_20261003/inputs/):
  * the TP4 SW64 L1 die-0 programs: the pinned split-128 image (50934438) and the one-stream image
    (23e52eb4) that measured 3,930 cycles a layer (claude/qwen-allreduce-oneseg-20261003 @ 7d736e8e6);
  * the RT_ITRACE die-0 L0 instruction trace a17a3c79 (split images, same body, 4,669 cycles);
  * the one-stream measured.json / Verilator gate (624 cycles an all-reduce, 987 split);
  * the W12 floorplan estimate c6e6b845 (BD 41, NWS 5, TWS 38, ORD 7 at the 504 um SS reach) and the
    B2-EW near-HBM floorplan r2 ced04cd96 (64 x 24 tiles of 313.6 x 1,291.7 um, hub at the die centre).

Method:
  1. A re-implementation of tools/hdc_timing.simulate (no KV/HBM streaming) that also records, for every
     instruction, which earlier event bound its issue; it is asserted equal to hdc_timing.simulate on both
     programs.  me_lat = 16 + 112 (the runtime's wire stages), tree 4 x 13 levels, G 6,144, SW 64, position 0.
  2. The model is checked against the trace issue times (fetch f at cycle c => instruction f - 5 issued at
     c - 1: NFQ 4 + NEXT), segment by segment.
  3. Critical-path walk from each segment's END back to its start, attributing every cycle to ME compute,
     ME fixed fill, ME tree adders, ME wire stages (BD / NWS / TWS / ORD / MEM_EXTRA), SU stream, SU pipe,
     SU reducer tail, handoffs and issue gaps.
  4. Candidates priced as cycle deltas on the calibrated composition (3,930 a layer measured).

Run:  (cd tools && python3 qwen_body_wire_latency.py)            # writes the record
      (cd tools && python3 qwen_body_wire_latency.py --verify)   # regenerates in a temp dir, byte-compares
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import hdc_isa as I                                   # noqa: E402
import hdc_timing as T                                # noqa: E402
import hdc_qwen_fullshape_isa_w12 as QI               # noqa: E402

REC = ROOT / "results/uarch/qwen_body_wire_latency_20261003"
INP = REC / "inputs"
FILES = dict(
    prog_split=INP / "tp4_sw64_L1_d0_program_split128.hex",
    prog_one=INP / "tp4_sw64_L1_d0_program_onestream256.hex",
    seg_split=INP / "tp4_sw64_L1_d0_segments_split128.hex",
    seg_one=INP / "tp4_sw64_L1_d0_segments_onestream256.hex",
    itrace=INP / "layer0_tp4_g6144_sw64_itrace_a17a3c79.txt",
    ar_measured=INP / "allreduce_oneseg_measured_7d736e8e6.json",
    ar_gate=INP / "allreduce_oneseg_verilator_gate_7d736e8e6.json",
    fp_w12=INP / "floorplan_w12_tp4_g6144_ss504_c6e6b845.json",
    fp_b2ew=INP / "floorplan_b2ew_model_r2_ced04cd96.json",
    calendar=ROOT / "results/uarch/qwen_rom_calibrated_calendar_20261003/near-hbm-selected-r1.json",
)
SOURCES = [HERE / "hdc_timing.py", HERE / "hdc_isa.py", HERE / "hdc_qwen_fullshape_isa_w12.py", Path(__file__)]

G = 6144
SW = 64
POS = 0
DYN_SHAPE = dict(H=4096, half=64, HD=128)
LAYERS = 36
REACH_UM = 504.0
CLOCK_HZ = 1.2e9
# the runtime's wire stages (tools/qwen_rom_rt_token_w12.py engine_latency_added = BD + (TCUT-2) NWS + TWS + MEM_EXTRA + ORD)
WIRE = dict(BD=41, NWS=5 * 5, TWS=38, ORD=7, MEM_EXTRA=1)
WIRE_TOTAL = sum(WIRE.values())                       # 112
ME_FILL = T.K["me_lat"]                               # 16
TREE = T.K["me_tree"] * T.split_tree_levels(G)        # 52

# instruction names, one-stream program (29 words; segments at 0, 18, 26)
NAMES_ONE = ["in_norm_sumsq", "QKV_ME", "in_norm_rsqrt", "v_norm_scale_kvwrite", "qk_norm_sumsq", "qk_rsqrt",
             "qk_norm_scale", "rope_q_a", "rope_k_a_kvwrite", "rope_q_b", "rope_k_b_kvwrite", "scores_ME",
             "softmax_exp_sum", "PV_ME", "recip_Z", "attn_out_scale", "O_ME", "AR1_barrier",
             "post_tp_scale_1", "residual_1_sumsq", "GU_ME", "ffn_norm_rsqrt", "gu_norm_scale", "silu_mul_up",
             "down_ME", "AR2_barrier", "post_tp_scale_2", "residual_2_sumsq", "END"]
ATTN = {"scores_ME", "softmax_exp_sum", "PV_ME", "recip_Z", "attn_out_scale"}
SEGS_ONE = [(0, 18), (18, 26), (26, 29)]
SEGS_SPLIT = [(0, 18), (18, 19), (19, 27), (27, 28), (28, 31)]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_prog(p: Path):
    return [QI.decode_instruction(int(x, 16)) for x in p.read_text().split()]


def seg_bases(p: Path):
    return [(int(x, 16) >> 32) & 0xFFFF for x in p.read_text().split()]


# --------------------------------------------------------------------------------------------- simulator
class Op:
    def __init__(self, i, f):
        self.i, self.f = i, f
        self.unit = f["unit"]


def _pick(a, b, me_op, su_op):
    """the binding unit-idle event of a barrier/wait: the later release, among units that have an op"""
    if me_op is None:
        return ("idle_su", su_op)
    if su_op is None:
        return ("idle_me", me_op)
    return ("idle_me", me_op) if a >= b else ("idle_su", su_op)


def simulate(prog, k=None, wire=None, chase_n=None, start=None):
    """hdc_timing.simulate (kv=None, w=None) with per-op wire overrides and binding-event tracking.
    wire: {pc: me wire cycles} (default WIRE_TOTAL); chase_n: {pc: chase_n override}."""
    k = dict(T.K) if k is None else k
    wire = wire or {}
    chase_n = chase_n or {}
    dyn = T.dyn_values(POS, groups=G, **DYN_SHAPE)
    t = k.get("start", 0) if start is None else start
    me_free = su_free = 0
    me_idle = su_idle = 0
    me_idle_op = su_idle_op = None
    su_cls, su_cls_idle, su_cls_op = None, 0, None
    last_me = last_su = None
    me_free_op = su_free_op = None
    ops = []
    prev = None
    end = None
    for idx, f0 in enumerate(prog):
        f = {name: f0.get(name, 0) for name, _ in I.FIELDS}
        o = Op(idx, f)
        u = f["unit"]
        if u == I.UNIT_END:
            a = me_idle + k.get("idle_me", k["idle_reg"])
            b = su_idle + k.get("idle_su", k["idle_reg"])
            t2 = max(t, a, b)
            if t2 == t:
                bind = ("seq", prev)
            else:
                bind = _pick(a, b, me_idle_op, su_idle_op)
            o.go, o.bind = t2, bind
            ops.append(o)
            end = o
            break
        ready, bind = t, ("seq", prev)
        if f["barrier"]:
            a = me_idle + k.get("idle_me", k["idle_reg"])
            b2 = su_idle + k.get("idle_su", k["idle_reg"])
            bb = max(a, b2)
            if bb > ready:
                ready = bb
                bind = _pick(a, b2, me_idle_op, su_idle_op)
        elif f["wait_me"] or f["wait_su"]:
            a = me_idle + k.get("idle_me", k["idle_reg"]) if f["wait_me"] else 0
            b2 = su_idle + k.get("idle_su", k["idle_reg"]) if f["wait_su"] else 0
            bb = max(a, b2)
            if bb > ready:
                ready = bb
                bind = _pick(a, b2, me_idle_op if f["wait_me"] else None, su_idle_op if f["wait_su"] else None)
        elif f["chase"]:
            n = chase_n.get(idx, f["chase_n"])
            if u == I.UNIT_ME and f["chase_rows"]:
                first, cnt, per_row = last_su.el
                c = first + min(n * per_row, cnt) - 1 + 1 + k.get("chase_me", 0)
                cb = ("chase_su", last_su, min(n * per_row, cnt))
            elif u == I.UNIT_ME:
                first, cnt, _ = last_su.el
                c = first + min(n, cnt) - 1 + 1 + k.get("chase_me", 0)
                cb = ("chase_su", last_su, min(n, cnt))
            else:
                m = min(n, len(last_me.slots))
                c = last_me.slots[m - 1] + 1 + k.get("chase_su", 0)
                cb = ("chase_me", last_me, m)
            if c > ready:
                ready, bind = c, cb
        if u == I.UNIT_ME:
            go = max(ready, me_free)
            if go > ready:
                bind = ("busy", me_free_op)
            rounds, kc = T.me_loop(f, dyn, POS, G)
            n_el = rounds * kc * I.INTERLEAVE
            e0 = go + k["me_start"]
            w = wire.get(idx, WIRE_TOTAL)
            lat = ME_FILL + TREE + w
            o.n_el, o.e0, o.lat, o.wire, o.kc, o.rounds = n_el, e0, lat, w, kc, rounds
            o.slots = [e0 + r * kc * I.INTERLEAVE + (kc - 1) * I.INTERLEAVE + j + lat
                       for r in range(rounds) for j in range(I.INTERLEAVE)]
            o.rmax = (k.get("rmax_tail", 0) + (G * I.W_LANES - 1).bit_length()) if f["me_rmax"] else 0
            o.free = e0 + n_el
            o.idle = o.slots[-1] + o.rmax
            me_free, me_free_op = o.free, o
            if o.idle >= me_idle:
                me_idle, me_idle_op = o.idle, o
            last_me = o
        else:
            cls = f["sfu"]
            go = max(ready, su_free)
            if go > ready:
                bind = ("busy", su_free_op)
            if su_cls is not None and cls != su_cls and su_cls_idle > go:
                go, bind = su_cls_idle, ("class_drain", su_cls_op)
            n_el = T.su_vectors(f, dyn, SW)
            e0 = go + k["su_start"]
            d = k["su_depth"][cls]
            o.n_el, o.e0, o.depth = n_el, e0, d
            o.el = (e0 + d, n_el, n_el // max(1, f["su_nout"]))
            o.last = e0 + n_el - 1 + d
            o.tail = T.red_tail(k, SW) if f["red"] else 0
            o.idle = o.last + o.tail
            o.free = e0 + n_el
            su_free, su_free_op = o.free, o
            if o.idle >= su_idle:
                su_idle, su_idle_op = o.idle, o
            su_cls, su_cls_idle, su_cls_op = cls, o.last, o
            last_su = o
        o.go, o.bind = go, bind
        ops.append(o)
        prev = o
        t = go + k["seq_gap"]
    return ops, end


def check_equal(prog, k):
    iss, t = T.simulate(prog, POS, groups=G, k=k, dyn_shape=DYN_SHAPE, su_width=SW)
    ops, end = simulate(prog, k)
    mine = [o.go for o in ops if o.unit != I.UNIT_END]
    assert mine == iss, (mine, iss)
    assert end.go == t, (end.go, t)
    return t


def kmodel():
    k = dict(T.K)
    k["me_lat"] = ME_FILL + TREE - k["me_tree"] * T.split_tree_levels(G) + WIRE_TOTAL   # = 16 + 112 (tree added by simulate)
    return k


# --------------------------------------------------------------------------------------------- critical path
CATS = ["me_compute", "me_fill", "me_tree", "me_wire", "me_rowmax", "su_stream", "su_pipe", "su_reduce_tail",
        "handoff", "issue", "start"]


def _span_op(o, upto, acc, label):
    """attribute o.go -> `upto` (an event inside o) to categories"""
    def add(c, v):
        acc[c] = acc.get(c, 0) + v
        label[o.i] = label.get(o.i, 0) + v
        label[(o.i, c)] = label.get((o.i, c), 0) + v
    if o.unit == I.UNIT_ME:
        # go -> e0 (me_start) -> element loop -> lat (fill + tree + wire) -> slots / rowmax
        total = upto - o.go
        rest = total
        st = o.e0 - o.go
        add("me_fill", st)
        rest -= st
        lat = o.lat
        comp = rest - lat - (o.rmax if upto == o.idle else 0)
        add("me_compute", comp)
        add("me_fill", ME_FILL)
        add("me_tree", TREE)
        add("me_wire", o.wire)
        if upto == o.idle and o.rmax:
            add("me_rowmax", o.rmax)
    else:
        total = upto - o.go
        st = o.e0 - o.go
        add("su_pipe", st)
        rest = total - st
        if upto == o.idle:
            add("su_reduce_tail", o.tail)
            rest -= o.tail
        if upto >= o.e0 + o.depth:
            add("su_pipe", o.depth)
            rest -= o.depth
        add("su_stream", rest)


def critical_path(ops, end, k):
    acc, label, chain = {}, {}, []
    cur = end
    t_cur = end.go
    while cur is not None:
        kind = cur.bind[0]
        src = cur.bind[1]
        if src is None:                      # nothing issued yet in this segment: the start latency / empty drain
            acc["start"] = acc.get("start", 0) + cur.go
            chain.append((cur.i, "start", cur.go))
            break
        if kind == "seq":
            if src is None:
                acc["start"] = acc.get("start", 0) + cur.go
                chain.append((cur.i, "start", cur.go))
                break
            gap = cur.go - src.go
            acc["issue"] = acc.get("issue", 0) + gap
            chain.append((cur.i, "issue", gap))
            cur = src
            continue
        if kind in ("idle_me", "idle_su"):
            h = k.get(kind, k["idle_reg"])
            acc["handoff"] = acc.get("handoff", 0) + (cur.go - src.idle)
            chain.append((cur.i, kind, cur.go - src.idle))
            _span_op(src, src.idle, acc, label)
            chain.append((src.i, "op_to_idle", src.idle - src.go))
            cur = src
            continue
        if kind == "busy":
            acc["handoff"] = acc.get("handoff", 0) + (cur.go - src.free)
            _span_op(src, src.free, acc, label)
            chain.append((src.i, "op_to_free", src.free - src.go))
            cur = src
            continue
        if kind == "class_drain":
            _span_op(src, src.last, acc, label)
            chain.append((src.i, "op_to_last", src.last - src.go))
            cur = src
            continue
        if kind == "chase_su":
            n = cur.bind[2]
            ev = src.el[0] + n - 1
            acc["handoff"] = acc.get("handoff", 0) + (cur.go - ev)
            _span_op(src, ev, acc, label)
            chain.append((src.i, f"chase_su_{n}", ev - src.go))
            cur = src
            continue
        if kind == "chase_me":
            m = cur.bind[2]
            ev = src.slots[m - 1]
            acc["handoff"] = acc.get("handoff", 0) + (cur.go - ev)
            _span_op(src, ev, acc, label)
            chain.append((src.i, f"chase_me_{m}", ev - src.go))
            cur = src
            continue
        raise RuntimeError(kind)
    assert sum(acc.values()) == end.go, (acc, end.go)
    return acc, label, chain


# --------------------------------------------------------------------------------------------- trace
def parse_trace(p: Path):
    ev = []
    for line in p.read_text().splitlines():
        if not line.startswith("ITR "):
            continue
        parts = dict(x.split("=") for x in line.split()[1:])
        c = int(parts.pop("cyc"))
        (key, val), = parts.items()
        ev.append((c, key, int(val)))
    return ev


def trace_windows(ev, bases, stage_end):
    """[(base, first fetch, end)] of each program segment: segment 0 starts at the first fetch; every later
    segment at the first fetch after a collective's traffic ends (the core prefetches past END, so a word index
    alone does not place a fetch in a segment); each segment ends where the next collective's traffic starts,
    the last at the stage end."""
    coll_on = [c for c, key, v in ev if key == "coll" and v == 1]
    coll_off = [c for c, key, v in ev if key == "coll" and v == 0]
    fetches = [(c, v) for c, key, v in ev if key == "fetch"]
    starts = [fetches[0][0]] + [min(c for c, _ in fetches if c > off) for off in coll_off]
    ends = coll_on + [stage_end]
    assert len(starts) == len(bases) == len(ends)
    return list(zip(bases, starts, ends))


def trace_issue_times(ev, windows, nwords):
    """issue cycle of each program word from fetch edges, inside its segment's window: in steady state the core
    holds NEXT + NFQ = 4 words, so the fetch of word f follows the issue of word f - 5 by one cycle."""
    issue = {}
    for base, c0, c1 in windows:
        for c, key, v in ev:
            if key == "fetch" and c0 <= c <= c1:
                pc = v - 5
                if base <= pc < nwords:
                    issue.setdefault(pc, c - 1)
    return issue


# --------------------------------------------------------------------------------------------- geometry
def geometry():
    w12 = json.loads(FILES["fp_w12"].read_text())
    con = {c["rtl_param"].split()[0]: c for c in w12["connections"]}
    levels = w12["wire_stages"]["per_level"]
    bd_um = [c for c in w12["connections"] if c["rtl_param"].startswith("BD")][0]["distance_um"]
    tws_um = [c for c in w12["connections"] if c["rtl_param"] == "TWS"][0]["distance_um"]
    ord_um = [c for c in w12["connections"] if c["rtl_param"] == "ORD"][0]["distance_um"]
    lvl_stages = [v["stages"] for v in levels.values()]
    lvl_um = [v["worst_um"] for v in levels.values()]
    out_stages = WIRE["BD"]
    ret_now = WIRE["NWS"] + WIRE["TWS"]
    # monotone (spine-directed) tree: each in-block node sits on the farthest leaf's path toward the tree top,
    # so the return wire is the leaf -> tree-top distance (~ the broadcast distance) plus at most one rounding
    # stage per in-block level
    ret_mono_best = math.ceil(bd_um / REACH_UM)
    ret_mono_worst = ret_mono_best + len(lvl_stages)
    w12_geo = dict(
        die_um=w12["die_um"], tile_um=w12["tile_um"], spine_x_um=w12["spine"]["x"],
        broadcast_um=bd_um, broadcast_stages=out_stages,
        in_block_levels=dict(zip(levels.keys(), [dict(um=u, stages=s) for u, s in zip(lvl_um, lvl_stages)])),
        in_block_uniform_nws=WIRE["NWS"], in_block_per_level_sum=sum(lvl_stages),
        in_block_path_um=round(sum(lvl_um), 1),
        tree_top_um=tws_um, tree_top_stages=WIRE["TWS"], result_write_um=ord_um, result_write_stages=WIRE["ORD"],
        return_path_um=round(sum(lvl_um) + tws_um + ord_um, 1), return_stages_now=ret_now + WIRE["ORD"],
        return_detour_um=round(sum(lvl_um) + tws_um - bd_um, 1),
        monotone_return_stages=[ret_mono_best, ret_mono_worst],
        note="W12 frame (as built in the runtime parameters): the return path (in-block levels 3-7 + level-7 "
             "words to the spine top + result write) is 29.8 mm against the 20.5 mm broadcast; the uniform NWS "
             "pads levels 3-7 (2+3+4+5+3 = 17 stages) to 5 x 5 = 25")
    b2 = json.loads(FILES["fp_b2ew"].read_text())
    fl = b2["floorplan"]
    hub_x, hub_y = b2["stages"]["hub_xy_um"]
    tw, th = fl["tile_slot_um"]
    x0, y0 = fl["core_origin_um"]
    aw, ah = fl["array_um"]
    sw = fl["spine"]["w_um"]
    # tile field: 32 columns each side of the spine, 24 rows (two link channels inside the array height)
    west_far_x = x0 + tw / 2
    east_far_x = x0 + aw + sw - tw / 2
    far_dx = max(hub_x - west_far_x, east_far_x - hub_x)
    far_dy = max(hub_y - (y0 + th / 2), (y0 + ah - th / 2) - hub_y)
    d_far = far_dx + far_dy
    one_way = math.ceil(d_far / REACH_UM)
    floor_rt = one_way + 2 + one_way + 1 + WIRE["MEM_EXTRA"]   # + tile input reg + XVM, + one result-write stage
    d_edge = d_far - tw / 2 - th / 2                            # pins at the tile's near corner (optimistic)
    one_way_edge = math.ceil(d_edge / REACH_UM)
    floor_edge = one_way_edge + 2 + one_way_edge + 1 + WIRE["MEM_EXTRA"]
    b2_geo = dict(
        die_um=fl["die_um"], tile_slot_um=fl["tile_slot_um"], array_um=fl["array_um"], hub_xy_um=[hub_x, hub_y],
        farthest_tile_centre_dx_um=round(far_dx, 1), farthest_tile_centre_dy_um=round(far_dy, 1),
        farthest_manhattan_um=round(d_far, 1), one_way_stages=one_way,
        round_trip_floor_cycles=floor_rt,
        farthest_near_corner_um=round(d_edge, 1), one_way_stages_near_corner=one_way_edge,
        round_trip_floor_near_corner=floor_edge,
        measured_runtime_cycles=WIRE_TOTAL,
        headroom_vs_measured=WIRE_TOTAL - floor_rt,
        headroom_vs_measured_optimistic=WIRE_TOTAL - floor_edge,
        w12_style_broadcast_stages=one_way + 2,
        note="B2-EW (selected frame): hub at the die centre is the minimax point for Manhattan distance; any "
             "broadcast to and reduction from every tile is >= 2 x the farthest-tile distance. Floor = one-way "
             "stages x 2 + tile input register + XVM + 1 result-write stage + MEM_EXTRA. The runtime's 112 was "
             "derived on the W12 frame (0.20 mm2 tiles, half the field), so on B2-EW it is already AT this floor "
             "only if the tree is monotone; a W12-style tree on B2-EW would exceed 112")
    return w12_geo, b2_geo


# --------------------------------------------------------------------------------------------- study
def segment_runs(prog, segs, k, **kw):
    out = []
    for a, b in segs:
        p = prog[a:b] + ([] if prog[b - 1]["unit"] == I.UNIT_END else [dict(unit=I.UNIT_END)])
        # per-op overrides are given in absolute PCs; shift them into the segment
        kk = {key: {pc - a: v for pc, v in val.items() if a <= pc < b} for key, val in kw.items()}
        ops, end = simulate(p, k, **kk)
        out.append((a, ops, end))
    return out


def body_cycles(runs):
    return sum(end.go for _, _, end in runs)


def study():
    k = kmodel()
    prog_one = load_prog(FILES["prog_one"])
    prog_split = load_prog(FILES["prog_split"])
    assert seg_bases(FILES["seg_one"]) == [a for a, _ in SEGS_ONE]
    assert seg_bases(FILES["seg_split"]) == [a for a, _ in SEGS_SPLIT]
    assert len(prog_one) == 29 and len(prog_split) == 31
    # equivalence with hdc_timing.simulate, segment by segment, both programs
    for prog, segs in ((prog_one, SEGS_ONE), (prog_split, SEGS_SPLIT)):
        for a, b in segs:
            p = prog[a:b] + ([] if prog[b - 1]["unit"] == I.UNIT_END else [dict(unit=I.UNIT_END)])
            check_equal(p, k)
    ar_meas = json.loads(FILES["ar_measured"].read_text())
    gate = json.loads(FILES["ar_gate"].read_text())
    ar_one = sorted({c["cycles"] for n, c in gate["cases"].items() if n.endswith("one256") and c["depth"] >= 256})
    ar_split = sorted({c["cycles"] for n, c in gate["cases"].items() if n.endswith("split128") and c["depth"] >= 256})
    assert len(ar_one) == 1 and len(ar_split) == 1
    AR1 = ar_one[0]                                                    # 624
    layer_meas = ar_meas["runs"]["B"]["cycles"]["L1"]                 # 3,930
    layer_split = ar_meas["runs"]["A"]["cycles"]["L1"]                # 4,668

    # ---- 1. model vs trace (split program, the traced one)
    ev = parse_trace(FILES["itrace"])
    stage_end = int([ln.split("end_cyc=")[1].split()[0] for ln in FILES["itrace"].read_text().splitlines()
                     if ln.startswith("STAGE L0 done")][0])
    windows = trace_windows(ev, [a for a, _ in SEGS_SPLIT], stage_end)
    tri = trace_issue_times(ev, windows, len(prog_split))
    runs_split = segment_runs(prog_split, SEGS_SPLIT, k)
    first_fetch = {b: c0 for b, c0, _ in windows}
    seg_end_trace = {b: c1 for b, _, c1 in windows}
    cal_rows, seg_rows = [], []
    for a, ops, end in runs_split:
        base = first_fetch[a]
        seg_rows.append(dict(segment_base=a, trace_first_fetch=base, trace_end=seg_end_trace[a],
                             trace_span=seg_end_trace[a] - base, model_span=end.go,
                             delta=end.go - (seg_end_trace[a] - base)))
        for o in ops:
            pc = a + o.i
            if o.unit == I.UNIT_END or pc not in tri:
                continue
            cal_rows.append(dict(pc=pc, unit="ME" if o.unit == I.UNIT_ME else "SU", model=o.go,
                                 trace=tri[pc] - base, delta=o.go - (tri[pc] - base)))
    me_windows, on = [], None
    for c, key, v in ev:
        if key == "me":
            if v == 1:
                on = c
            else:
                me_windows.append([on, c])
    body_seg_trace = sum(r["trace_span"] for r in seg_rows if r["segment_base"] in (0, 19, 28))
    body_seg_model = sum(r["model_span"] for r in seg_rows if r["segment_base"] in (0, 19, 28))

    # ---- 2. one-stream composition, calibrated to the measured 3,930
    runs = segment_runs(prog_one, SEGS_ONE, k)
    seg_model = [end.go for _, _, end in runs]
    boundary = layer_meas - sum(seg_model) - 2 * AR1
    comp = dict(segments_model=seg_model, allreduce_gate=AR1, allreduces=2, boundary_calibrated=boundary,
                layer_measured=layer_meas,
                note="layer = seg0 + AR + seg1 + AR + seg2 + boundary; AR = the Verilator gate's one-stream "
                     "all-reduce (issue -> resume, 624); boundary absorbs TP-sequencer transitions, the stage "
                     "restart and model error (calibrated, not a measured term)")

    # ---- 3. critical path decomposition (one-stream program)
    cp = []
    tot = {c: 0 for c in CATS}
    per_op = {}
    per_grp = {}
    for a, ops, end in runs:
        acc, label, chain = critical_path(ops, end, k)
        for c, v in acc.items():
            tot[c] += v
        for key, v in label.items():
            if isinstance(key, tuple):
                i, c = key
                grp = "attention" if NAMES_ONE[a + i] in ATTN else "body"
                per_grp.setdefault(grp, {}).setdefault(c, 0)
                per_grp[grp][c] += v
            else:
                per_op[NAMES_ONE[a + key]] = per_op.get(NAMES_ONE[a + key], 0) + v
        cp.append(dict(segment_base=a, cycles=end.go, categories={c: acc.get(c, 0) for c in CATS if acc.get(c)},
                       chain=[dict(pc=a + i, op=NAMES_ONE[a + i], link=lk, cycles=v) for i, lk, v in chain]))
    me_ops = [(a + o.i, NAMES_ONE[a + o.i], o) for a, ops, _ in runs for o in ops if o.unit == I.UNIT_ME]
    me_table = [dict(pc=pc, op=n, rounds=o.rounds, k_steps=o.kc, compute=o.n_el, start=1, fill=ME_FILL,
                     tree=TREE, wire=o.wire, rowmax=o.rmax, issue_to_idle=o.idle - o.go) for pc, n, o in me_ops]
    # wire on the critical path, by sensitivity (all ME ops 112 -> 0) and per op
    base_body = body_cycles(runs)
    no_wire = body_cycles(segment_runs(prog_one, SEGS_ONE, k, wire={pc: 0 for pc, _, _ in me_ops}))
    wire_sens = {}
    for pc, n, _ in me_ops:
        wire_sens[n] = base_body - body_cycles(segment_runs(prog_one, SEGS_ONE, k, wire={pc: 0}))
    attn_pcs = [i for i, n in enumerate(NAMES_ONE) if n in ATTN]
    # on-core attention span on the critical path (scores issue -> O issue): replaced by near-HBM attention
    ops0 = runs[0][1]
    attn_span = ops0[NAMES_ONE.index("O_ME")].go - ops0[NAMES_ONE.index("scores_ME")].go
    body_me_ops = [n for _, n, _ in me_ops if n not in ATTN]
    body_wire_cp = sum(wire_sens[n] for n in body_me_ops)
    attn_wire_cp = sum(wire_sens[n] for n in wire_sens if n in ATTN)
    by_wire_component = {c: v * len(body_me_ops) for c, v in WIRE.items()}

    nonattn_body_model = base_body - attn_span
    nonattn_body_meas = layer_meas - 2 * AR1 - attn_span          # 2,682 - attention span
    decomposition = dict(
        layer_measured_one_stream=layer_meas,
        non_collective_measured=layer_meas - 2 * AR1,
        non_collective_model=base_body,
        on_core_attention_span_pos0=attn_span,
        non_attention_body_measured_basis=nonattn_body_meas,
        calendar_body_2599_check=dict(
            calendar_body=2599,
            calendar_attention_share=87,
            this_study_attention_span=attn_span,
            difference=attn_span - 87,
            finding=f"the calendar subtracts 87 cycles of position-0 attention; the critical path's on-core "
                    f"attention (scores ME issue -> O ME issue: scores ME, softmax, P.V ME, 1/Z, scale) is "
                    f"{attn_span} cycles, two of them ME ops carrying 112 wire stages each. The non-attention "
                    f"body the near-HBM design keeps is ~{nonattn_body_meas}, not 2,599"),
        critical_path_categories_total=tot,
        critical_path_by_op=per_op,
        critical_path_by_group=dict(per_grp, unattributed_handoff_issue_start={c: tot[c] for c in ("handoff", "issue", "start")},
                                    note="op-attributed cycles of the walk; 'attention' = scores, softmax, P.V, 1/Z, "
                                         "scale (replaced by the near-HBM unit); handoffs/issue/start are listed apart"),
        me_ops=me_table,
        wire_on_critical_path=dict(
            per_me_op=WIRE_TOTAL, per_component=WIRE,
            all_six_me_ops_sensitivity=base_body - no_wire,
            per_op_sensitivity=wire_sens,
            body_me_ops=body_me_ops, body_wire_cycles=body_wire_cp,
            attention_me_ops_wire_cycles=attn_wire_cp,
            body_wire_by_component_walk=by_wire_component,
            share_of_non_attention_body=round(body_wire_cp / nonattn_body_meas, 4),
            share_of_layer=round(body_wire_cp / layer_meas, 4)),
    )

    # ---- 4. geometry
    w12_geo, b2_geo = geometry()

    # ---- 5. bases for per-user gain
    cal = json.loads(FILES["calendar"].read_text())
    nonlayer = cal["composition"]["nonlayer_cycles"]                   # 3,042
    att_hbm = cal["composition"]["attention_cycles"]["primary"]        # 1,700
    bases = dict(
        A_measured_pos0_onstream=dict(per_layer=layer_meas, token=ar_meas["token_projection"]["projected"],
                                      note="measured one-stream TP4 runtime, position 0, on-core attention "
                                           "(6 ME ops a layer)"),
        B_selected_near_hbm_calendar=dict(per_layer=2599 + 2 * AR1 + att_hbm,
                                          token=LAYERS * (2599 + 2 * AR1 + att_hbm) + nonlayer,
                                          note="selected near-HBM build entry with the one-stream AR: calendar "
                                               "body 2,599 + 2 x 624 + 1,700, + 3,042 non-layer (4 tile ME "
                                               "ops a layer)"),
        C_near_hbm_corrected_body=dict(per_layer=nonattn_body_meas + 2 * AR1 + att_hbm,
                                       token=LAYERS * (nonattn_body_meas + 2 * AR1 + att_hbm) + nonlayer,
                                       note="as B with the body corrected to this study's attention span"),
    )

    def gain(per_layer_saving, basis, me_ops_per_layer=None):
        b = bases[basis]
        tok = b["token"]
        new = tok - LAYERS * per_layer_saving
        return dict(per_layer_saved=per_layer_saving, token_cycles=new,
                    token_us=round(new / CLOCK_HZ * 1e6, 3),
                    per_user_rate_gain=round(tok / new - 1, 4))

    # ---- 6. candidates
    cands = []

    def wire_cand(cid, name, per_op_saving, frame, exact, cost, note):
        """per-op wire saving applied to the body ME ops (and, for basis A, the attention ME ops too)"""
        w_body = {pc: WIRE_TOTAL - per_op_saving for pc, n, _ in me_ops if n not in ATTN}
        w_all = {pc: WIRE_TOTAL - per_op_saving for pc, _, _ in me_ops}
        s_body = base_body - body_cycles(segment_runs(prog_one, SEGS_ONE, k, wire=w_body))
        s_all = base_body - body_cycles(segment_runs(prog_one, SEGS_ONE, k, wire=w_all))
        cands.append(dict(id=cid, name=name, frame=frame, per_op_wire_saving=per_op_saving,
                          per_layer_saving_body_ops=s_body, per_layer_saving_all_me_ops=s_all,
                          A=gain(s_all, "A_measured_pos0_onstream"),
                          B=gain(s_body, "B_selected_near_hbm_calendar"),
                          C=gain(s_body, "C_near_hbm_corrected_body"),
                          exactness=exact, cost=cost, note=note))

    lvl = w12_geo["in_block_uniform_nws"] - w12_geo["in_block_per_level_sum"]
    wire_cand("W1", "per-level tree wire stages (NWS per level: 2,3,4,5,3 instead of 5 x 5)", lvl, "W12",
              "unchanged arithmetic: only register stages on the level-3..7 wires; every level keeps one stage "
              "count for all its nodes so children stay aligned",
              "none (fewer flops)", "W12-frame number; on B2-EW the per-level distances differ (not derived)")
    mono_best = (WIRE["NWS"] + WIRE["TWS"]) - w12_geo["monotone_return_stages"][0] + (WIRE["ORD"] - 1)
    mono_worst = (WIRE["NWS"] + WIRE["TWS"]) - w12_geo["monotone_return_stages"][1] + (WIRE["ORD"] - 4)
    wire_cand("W2", "spine-directed (monotone) in-block H-tree + result ports beside the VM, W12 frame, best",
              mono_best, "W12",
              "the logical pairing (group 2i with 2i+1 at every level, the golden split tree) is unchanged; only "
              "the physical slot of each logical group and the host tile of each tree node move",
              "weight image re-layout (group -> tile map), tree-node hosting, port groups re-floorplanned",
              "upper bound: return wire = broadcast distance, ORD 7 -> 1")
    wire_cand("W2w", "as W2, worst rounding (one extra stage per in-block level, ORD 4)", mono_worst, "W12",
              "as W2", "as W2", "")
    b2_head = max(0, b2_geo["headroom_vs_measured_optimistic"])
    wire_cand("W3", "B2-EW frame (selected): every reduction/broadcast tree at the 2 x farthest-tile floor",
              b2_head, "B2-EW",
              "as W2", "as W2",
              f"the selected frame's hub-to-farthest-tile Manhattan distance is {b2_geo['farthest_manhattan_um']} um "
              f"= {b2_geo['one_way_stages']} stages each way: floor {b2_geo['round_trip_floor_cycles']} "
              f"({b2_geo['round_trip_floor_near_corner']} with pins at the tile's near corner) vs 112 measured; priced at "
              "the optimistic floor")
    # W4 regional broadcast trees: distance-bound, zero; W5 tile placement nearer the hub: analytic optimum
    place = []
    for pc, n, o in me_ops:
        if n in ATTN:
            continue
        C, Wd = o.n_el, WIRE_TOTAL
        # fraction f of the tiles, all within radius sqrt(f) of the hub: compute C/f, wire W*sqrt(f)
        best = min(((C / f + Wd * math.sqrt(f)), f) for f in [x / 1000 for x in range(50, 1001)])
        place.append(dict(op=n, compute=C, wire=Wd, at_full=C + Wd, best=round(best[0], 1), best_fraction=best[1],
                          saving=round(C + Wd - best[0], 1)))
    cands.append(dict(id="W4", name="regional broadcast trees (x root replicated per region)", per_layer_saving_body_ops=0,
                      B=gain(0, "B_selected_near_hbm_calendar"),
                      exactness="n/a", cost="replicated VM/x roots",
                      note="the x elements are produced by the SU at the hub; any path from the hub to the farthest "
                           "tile is >= the hub-to-tile distance (triangle inequality), so regional roots add a hop and "
                           "save nothing; the existing broadcast is already a pipelined tree"))
    cands.append(dict(id="W5", name="place dependent ops' tiles nearer the hub (use a fraction f of the tiles)",
                      per_op=place, per_layer_saving_body_ops=round(sum(p["saving"] for p in place), 1),
                      B=gain(round(sum(p["saving"] for p in place)), "B_selected_near_hbm_calendar"),
                      exactness="NOT exact: fewer groups changes the split-tree depth and the golden reduction "
                                "order (it depends on G); excluded on that ground alone",
                      cost="re-partitioned weights", note="even ignoring exactness the optimum is f = 1 for QKV, GU "
                      "and down (compute C/f grows faster than wire W sqrt(f) shrinks)"))
    # W6 level 4: independent chains
    cands.append(dict(id="W6", name="level 4: interleave independent chains to hide ME wire stages",
                      per_layer_saving_body_ops=0, B=gain(0, "B_selected_near_hbm_calendar"),
                      exactness="exact (order unchanged)", cost="compiler only",
                      note="at batch 1 the layer's ME ops form one dependent chain: QKV (one fused op) -> attention "
                           "-> O -> AR -> GU (one fused op) -> SiLU -> down -> AR; the only independent SU work (input "
                           "and FFN norm sum of squares, KV writes) already overlaps the ME ops (norm folded after the "
                           "matvec). Nothing is left to interleave"))
    # W7 early chase: ME starts while the SU still produces x (k-major element order); reducer kept in golden order
    early = {}
    for n_ in ("O_ME", "GU_ME", "down_ME"):
        early[NAMES_ONE.index(n_)] = 1
    s_early = base_body - body_cycles(segment_runs(prog_one, SEGS_ONE, k, chase_n=early))
    cands.append(dict(id="W7", name="level 3/4: x produced in k-step order so O/GU/down chase the first SU vector "
                                    "(hides the 41-stage broadcast under the producer)",
                      per_layer_saving_body_ops=s_early,
                      B=gain(s_early, "B_selected_near_hbm_calendar"), C=gain(s_early, "C_near_hbm_corrected_body"),
                      exactness="elementwise producers are order-free; the residual pass's sum of squares must then "
                                "run as a separate golden-order pass (off the critical path, before the rsqrt it "
                                "feeds)", cost="SU stride programs + an extra off-path reducer pass; the ME x reads "
                                "must not outrun the SU (GU: 2 vectors per k step vs 1/cycle; down: 8 per 8 cycles = "
                                "equal rate, no margin)",
                      note="UPPER BOUND: chase_n = 1 on O, GU and down; the model does not check the ME x-read rate"))

    # ---- level 5: collective fusion, priced on a CONTINUOUS token program (no per-layer stage restart)
    # The runtime runs each layer as a stage: its last segment drains (the residual's next-norm reducer tail) and the
    # next stage restarts and recomputes that sum of squares (in_norm_sumsq).  The token program the generator emits
    # for consecutive layers (tools/hdc_program.build_program) instead carries the sum with the residual op and lets
    # the next QKV chase it (chase_n 512).  Level-5 savings are priced against that program, so no stage artifact is
    # counted as a gain.
    N = {n: i for i, n in enumerate(NAMES_ONE)}
    h_resume = AR1 - (256 + 339 + 17)                     # last fold -> resume (the gate's handoff, 12)
    qkv_chased = dict(prog_one[N["QKV_ME"]], chase=1, chase_n=512)

    def cont_segments(fused=False):
        """seg A: [AR2 epilogue] + QKV .. O + END(AR1); seg B: [AR1 epilogue] + GU .. down + END(AR2)"""
        ep2 = [prog_one[N["post_tp_scale_2"]], prog_one[N["residual_2_sumsq"]]]
        ep1 = [prog_one[N["post_tp_scale_1"]], prog_one[N["residual_1_sumsq"]]]
        if fused:      # one op: the residual op's shape (64 vectors, sum of squares kept); multiply then add stages
            ep2, ep1 = [prog_one[N["residual_2_sumsq"]]], [prog_one[N["residual_1_sumsq"]]]
        segA = ep2 + [qkv_chased] + prog_one[N["in_norm_rsqrt"]:N["AR1_barrier"] + 1]
        segB = ep1 + prog_one[N["GU_ME"]:N["AR2_barrier"] + 1]
        return segA, segB

    def run_cont(fused=False, start=None):
        out = []
        for p in cont_segments(fused):
            ops, end = simulate(p, k, start=start)
            out.append((ops, end))
        return out

    base_c = run_cont()
    segA0, segB0 = base_c[0][1].go, base_c[1][1].go
    stage_artifact = sum(seg_model[i] for i in (0, 2)) - segA0
    layer_cont = layer_meas - stage_artifact
    # cut-through send lead: END (the barrier's release) minus the first result slot of O / down
    o_ops = base_c[0][0]
    d_ops = base_c[1][0]
    o_op = [o for o in o_ops if o.unit == I.UNIT_ME][-1]
    d_op = [o for o in d_ops if o.unit == I.UNIT_ME][-1]
    lead_o = base_c[0][1].go - o_op.slots[0]
    lead_d = base_c[1][1].go - d_op.slots[0]
    words_per_round = I.W_LANES * (G >> o_op.f["me_split"]) * I.INTERLEAVE // 16
    # never starved: the 1-word-a-cycle send reaches round r's first word at r x words_per_round cycles, after the
    # round is written (r x k x IL cycles)
    starve_o = all(r * o_op.kc * I.INTERLEAVE <= r * words_per_round for r in range(o_op.rounds))
    starve_d = all(r * d_op.kc * I.INTERLEAVE <= r * words_per_round for r in range(d_op.rounds))
    # L5b1: fused epilogue op; the core keeps running across the collective, so the op waiting in NEXT issues one
    # cycle after the completion flag instead of a 3-cycle core restart
    f1 = run_cont(fused=True, start=1)
    # L5b2: the fused epilogue consumes the arriving words (16 a cycle; 4 words = one 64-lane vector): its last
    # vector enters one cycle after the last fold, i.e. the op behaves as if issued 64 + h_resume cycles earlier
    shift_b2 = -(h_resume + 64 - 1)
    f2 = [(ops, end.go + shift_b2) for ops, end in f1]

    def layer(segA, segB, lead_a=0, lead_b=0):
        return segA + segB + 2 * AR1 - lead_a - lead_b + boundary + 0

    L_base = layer(segA0, segB0)
    variants = dict(
        L5b1=layer(f1[0][1].go, f1[1][1].go),
        L5b2=layer(f2[0][1], f2[1][1]),
        L5c=layer(segA0, segB0, lead_o, lead_d),
        L5pkg=layer(f1[0][1].go, f1[1][1].go, lead_o, lead_d),
        L5max=layer(f2[0][1], f2[1][1], lead_o, lead_d),
    )
    sav = {kk: L_base - v for kk, v in variants.items()}
    # L5a (norm partials with the collective): in the continuous program the next-norm sum of squares rides on the
    # residual op and the rsqrt it feeds waits behind the QKV matvec; its critical-path share:
    segA_nored = [dict(f, red=0) if f is prog_one[N["residual_2_sumsq"]] else f for f in cont_segments()[0]]
    s_l5a = segA0 - simulate(segA_nored, k)[1].go
    l5 = dict(
        continuous_program=dict(segA=segA0, segB=segB0, stage_runtime_seg0_plus_seg2=seg_model[0] + seg_model[2],
                                stage_artifact_per_layer=stage_artifact, layer_continuous=layer_cont,
                                note="the per-layer stage runtime pays a drain + restart + a recomputed input-norm sum "
                                     "of squares that a continuous token program does not; the calendar's 2,599 body "
                                     "inherits it"),
        terms=dict(resume_handoff_after_last_fold=h_resume, lead_O=lead_o, lead_down=lead_d,
                   words_per_round=words_per_round, send_never_starved=bool(starve_o and starve_d),
                   next_norm_reducer_on_critical_path=s_l5a),
        layer_model_continuous=L_base, layer_variants=variants, savings=sav,
    )
    for cid, name, sv, exact, cost, note in (
        ("L5a", "level 5: norm partials (next-norm sum of squares) carried with the collective", s_l5a,
         "the reducer order is untouched", "none", "the sum rides on the residual op and is consumed after the "
         "QKV matvec (norm folded after the matvec): nothing on the critical path to save"),
        ("L5b1", "level 1+5: post-TP scale and residual in ONE SU op; the core keeps running across the collective",
         sav["L5b1"], "elementwise fl(fl(p x s) + x) exactly as the golden's two ops (multiply stage then add stage, "
         "each RNE, no FMA); the sum of squares stays in the reducer in its order",
         "sequencer: a collective issued from the program with a wait on its completion instead of a segment "
         "restart; generator: one fused op; no new arithmetic", "removes one 64-vector pass per all-reduce and the "
         "core restart"),
        ("L5b2", "level 2+5: that epilogue applied to the arriving all-reduce words (hub-edge staging)", sav["L5b2"],
         "as L5b1, in arrival order; the reducer fed 4 words = one 64-lane vector in its golden lane order",
         "as L5b1 + a receive-path epilogue (16 fp32 mul + 16 fp32 add, or per-vector SU issue chasing the receive "
         "count): NEW arithmetic that must close at SS", "upper bound of the epilogue lever"),
        ("L5c", "level 5: cut-through send (each output word leaves when its tree result is written)", sav["L5c"],
         "the per-word fold ((p0+p1)+p2)+p3 and the word tags are unchanged; only the send time moves",
         "TP sequencer reads chase the ME result-slot progress instead of the barrier/END",
         f"O: {o_op.rounds} rounds {o_op.kc * I.INTERLEAVE} cycles apart; down: {d_op.rounds} rounds "
         f"{d_op.kc * I.INTERLEAVE} apart; {words_per_round} words a round, so the 1-word-a-cycle send never starves"),
        ("L5pkg", "asynchronous collective: L5b1 + L5c (no new arithmetic)", sav["L5pkg"], "as L5b1 and L5c",
         "as L5b1 and L5c", "one mechanism: the collective becomes a core-issued unit with progress handshakes on "
         "both sides (send chases the ME slots, the epilogue waits on the receive)"),
        ("L5max", "L5b2 + L5c (with the receive-path epilogue)", sav["L5max"], "as L5b2 and L5c",
         "as L5b2 and L5c", "upper bound"),
    ):
        cands.append(dict(id=cid, name=name, per_layer_saving_body_ops=sv, A=gain(sv, "A_measured_pos0_onstream"),
                          B=gain(sv, "B_selected_near_hbm_calendar"), C=gain(sv, "C_near_hbm_corrected_body"),
                          exactness=exact, cost=cost, note=note))

    # ---- 7. verdict
    wire_sel = [c for c in cands if c["id"] in ("W1", "W3", "W4", "W5", "W6", "W7")]
    best_wire = max(wire_sel, key=lambda c: c["B"]["per_user_rate_gain"])
    w2 = next(c for c in cands if c["id"] == "W2")
    pkg = next(c for c in cands if c["id"] == "L5pkg")
    verdict = dict(
        wire=dict(decision="KEEP the current wire design",
                  best_wire_candidate=dict(id=best_wire["id"], B=best_wire["B"]["per_user_rate_gain"],
                                           C=best_wire.get("C", {}).get("per_user_rate_gain")),
                  w12_frame_detour_recovery=dict(id="W2", B=w2["B"]["per_user_rate_gain"],
                                                 C=w2["C"]["per_user_rate_gain"], A=w2["A"]["per_user_rate_gain"]),
                  reason=f"on the selected B2-EW frame the 112-cycle round trip is within "
                         f"{b2_geo['headroom_vs_measured']}-{b2_geo['headroom_vs_measured_optimistic']} cycles of the 2 x farthest-tile floor "
                         f"({b2_geo['round_trip_floor_cycles']}); the W12-frame detour recovery (W2) is "
                         f"{w2['B']['per_user_rate_gain']:.1%} on the selected design and does not exist on B2-EW; "
                         f"the best wire-side lever ({best_wire['id']}) is "
                         f"{best_wire['B']['per_user_rate_gain']:.1%} and an upper bound; level 4 has nothing "
                         "independent to interleave at batch 1. All are below the 3% bar on the selected design (B, C). "
                         f"W2 reaches {w2['A']['per_user_rate_gain']:.1%} only on basis A (the measured position-0 "
                         "runtime with on-core attention and the W12 frame), which is not the design being built"),
        recommended=dict(id="L5pkg", name=pkg["name"], per_layer_saved=pkg["per_layer_saving_body_ops"],
                         B=pkg["B"], C=pkg["C"], A=pkg["A"],
                         reason="the one priced lever above 3% on every basis without new arithmetic; L5b2's "
                                "receive-path epilogue adds a further "
                                f"{sav['L5max'] - sav['L5pkg']} cycles a layer but needs fp32 mul/add that must "
                                "close at SS (fp32_mul is open at SS 1.2 GHz)"),
        gates=dict(agents_priced_gate=0.01, user_threshold=0.03),
    )
    return dict(
        schema="opentallas.qwen-body-wire-latency.v1",
        status="MODEL_ONLY_NOT_ADOPTED",
        question="Decompose the Qwen3-8B ROM TP4 layer body; how many cycles are ME wire stages on the critical "
                 "path; can golden-order-preserving reductions recover them?",
        configuration=dict(tp=4, groups=G, su_width=SW, position=POS, me_wire_stages=WIRE, me_fill=ME_FILL,
                           tree_cycles=TREE, tree_levels=T.split_tree_levels(G), reach_um=REACH_UM,
                           clock_hz=CLOCK_HZ, layers=LAYERS),
        calibration=dict(segments=seg_rows, per_instruction=cal_rows,
                         max_abs_issue_delta=max(abs(r["delta"]) for r in cal_rows),
                         body_segments_trace=body_seg_trace, body_segments_model=body_seg_model,
                         body_model_over_trace=round(body_seg_model / body_seg_trace, 4),
                         me_clock_windows=me_windows,
                         split_layer_measured=layer_split,
                         note="trace = the split-128 build (a17a3c79); the body is identical in the one-stream "
                              "build (only the all-reduce descriptors differ: 4,668 - 3,930 = 738 = 2 x (987 - "
                              "624) + 12)"),
        composition=comp,
        level5=l5,
        critical_path=cp,
        decomposition=decomposition,
        geometry=dict(W12=w12_geo, B2EW=b2_geo),
        bases=bases,
        candidates=cands,
        verdict=verdict,
        sources_sha256={str(p.relative_to(ROOT)): sha(p) for p in list(FILES.values()) + SOURCES},
        claim_boundary="analytical model calibrated to one TP4 runtime trace at position 0 (die 0, split build) and "
                       "the one-stream measured layer; no RTL or P&R; geometry from two floorplan models (W12 "
                       "estimate, B2-EW r2); level-5 terms use the Verilator-gate all-reduce timing (256 words + LAT "
                       "339 + fold 17 + handoff); per-user gains are on the stated bases, not measured",
    )


def write(out_dir: Path):
    rec = study()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "study.json").write_text(json.dumps(rec, indent=1, sort_keys=False) + "\n")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--print", action="store_true")
    a = ap.parse_args()
    if a.verify:
        with tempfile.TemporaryDirectory() as td:
            write(Path(td))
            new = (Path(td) / "study.json").read_bytes()
        old = (REC / "study.json").read_bytes()
        if new != old:
            raise SystemExit("study.json differs from a fresh regeneration")
        print("verify: study.json byte-identical")
        return
    rec = write(REC)
    if a.print:
        print(json.dumps(dict(decomposition=rec["decomposition"], verdict=rec["verdict"]), indent=1))


if __name__ == "__main__":
    main()
