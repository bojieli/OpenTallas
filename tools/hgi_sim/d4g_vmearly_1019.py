#!/usr/bin/env python3
"""HBM-VMEARLY (10-19): compiler early issue of on-chip VM-bank reads into double-buffered consumer operand slots.

WHAT IS PRICED.  LH-REPRICE3 (d4g_reprice3b_1019, row info_banklat_all = 1,206.3 DS / 407.0 Qwen) charges the d4g VM-bank
client round trips (x-load RD_LAT 55 + g4 10 = 65, COLL VM_RT 74 + 10 = 84, DMA lag 83 + 10 = 93, IDX op readers 171 + 10 =
181 / rootctl 65 + 10 = 75) as extra COST of every record.  In the S2 schedule (timing.schedule) a record's cost is unit
OCCUPANCY, so the round trip serialises even independent back-to-back records of one unit: fully exposed.

WHAT CHANGES.  The static schedule knows every address, so the compiler issues record i's VM read ISSUE_AHEAD = N records
early into NBUF = N + 1 operand slots at the consumer (slot = i mod NBUF, static; no credits / ready).  This module re-runs
the SAME programmes and the SAME LH-REPRICE3 terms with timing.schedule replaced by a copy whose only change is (S2/SX):

    d_i     = hideable bank-latency edges of record i (below); the record's occupancy becomes cost_i - d_i
    t_iss_i = min(t0_i, max(RAW producers of its VM operands retired + their retire wire,      (data ready)
                            start(i - N) of the same unit,                                     (issue-ahead window)
                            end(i - N - 1) of the same unit - d_i))                            (slot of i free on landing)
    start_i = max(t0_i, t_iss_i + d_i)          t0_i = the unchanged S2 start (dispatch + wire, unit free, pipelining)
    exposed_i = start_i - t0_i                  (N = 0: t_iss = t0, exposed = d_i: reproduces LH-REPRICE3 exactly)

d_i per client (the banklat increment of the record = RL.added at the plan_b_blall stages minus plan_b, and the bl_idx
constants), only the READ part:
    xl    SM.* / ATT.* records: the whole x-leg increment (SM_X 7.29 -> 32.5 inside max(x leg, weight-fetch leg))
    coll  COLL.* records: 2 of the 3 COLL_VM crossings (read request + read data); the result write stays exposed
    dma   DMA STORE / KVWB / SWAP-out (VM -> HBM, the dbk VM read): the VM_HBM increment; DMA LOAD / FENCE (HBM request
          leg) stay exposed (conservative)
    idx   IDX.INDEX / IDX.TOPK 181, ARGMAX 75 (bl_idx); the IDX result write (COLL_VM x1) stays exposed
Segments: DS schedules per layer segment (ds_mtp_verify.run), so no record prefetches across a layer boundary
(conservative).  Exposed / base edges are reported per client and per layer (rp_added keys vme:<client>:<base|exposed>,
vme_L<layer>:<client>:<base|exposed>).

PER-CLIENT RULES (integration 10-19 ~22:00, sub-lanes HBM-VMEARLY-DMA bc57f015e / -IDX 0b423e28d; N >= 1 enables a rule):
    xl, coll  the generic rule above (NBUF = N + 1 consumer operand slots; HBM-VMEARLY-XLCOLL builds them)
    dma       the DMA-back controller holds ONE move (ISSUE_AHEAD 0 is the only calendar the RTL takes):
              t_iss = min(t0, max(RAW, end(prev DMA record on the unit) - DMA_NEXT_CMD_K + DMA_CMD_LEAD))
              = d4g_bank_latency.dma_min_next_issue (issue_at(i+1) >= drain_at(i) + nchunk(i) + 4, >= producer retire);
              N is ignored beyond on/off.  bl_dma is charged only on VM-read DMA records (KVWB / STORE / swap-out);
              DMA.LOAD / FENCE keep the plan_b VM_HBM request stage (d4g_bl_dma_split_1019 --mode kvwb).
              OT_VME_BLDMA=all restores the committed every-DMA-record charge (LH-REPRICE3 reproduction).
    idx       the n12 reader is fully pipelined and the query store is the one static slot (NBUF 1):
              A_i = t_iss = min(t0, max(RAW_i, F_i - LB)), F_i = frame_start(i) = last use(i-1) + 1 (taken as
              end(i-1) + 1 of the unit: conservative), LB = VM_RT_EXTRA + 12 = bl_idx + 2 (183 at 171, measured)
LAYOUT (owner 10-19, HBM-MC2 89200325b): every HBM stream uses the ROTATED bank layout (blocks rotated across bank sets,
expert copies alternated).  It is what the successor PC controller's 90.67 B/edge/SM (+ bridge 1) assumes; without it the
successor gives 26-55 B/edge.  OT_VME_LAYOUT (default rotated) is recorded in the output; a run at a successor bandwidth
(--bw > 59.08, above H9b's packed 59.08) with any other layout is REFUSED (fail closed).

    PYTHONPATH=tools OT_VME_N=1 python3 -m hgi_sim.d4g_vmearly_1019 --bw 45.03 --out vme_n1.json
    PYTHONPATH=tools OT_VME_N=1 python3 -m hgi_sim.d4g_vmearly_1019 --bw 90.67 --bridge 1 --out vme_n1_succ.json
    OT_VME_N: issue-ahead N for every client, or per client "xl:1,coll:2,dma:1,idx:1" (missing client = 0).
"""
from __future__ import annotations

import math
import os
import sys
from collections import defaultdict

from hgi_sim import timing as T
from hgi_sim import d4g_reprice_1019 as R
from hgi_sim import ds_relay_latency as RL
from hbm_die_v16 import d4g_bank_latency as BLAT

BL_KEYS = ("SM_X", "COLL_VM", "VM_HBM")
CLIENTS = ("xl", "coll", "dma", "idx")
_ACTIVE = {}          # stage set of the running job, captured from RL._knob (DS set_variant and the Qwen job both call it)
_PLANB = {}


def _n_of():
    v = os.environ.get("OT_VME_N", "0").strip()
    if ":" not in v:
        return {c: int(v or 0) for c in CLIENTS}
    out = {c: 0 for c in CLIENTS}
    for part in v.split(","):
        k, n = part.split(":")
        out[k.strip()] = int(n)
    return out


N_OF = _n_of()

BLDMA = os.environ.get("OT_VME_BLDMA", "kvwb").strip()
LAYOUT = os.environ.get("OT_VME_LAYOUT", "rotated").strip()
BW_H9B_MAX = 59.08                 # H9b packed: the highest bandwidth any layout reaches on the release H9b master
IDX_LB_OVER_BL = 2                 # LB 183 = VM_RT_EXTRA 171 + 12; bl_idx 181 = 171 + 10 (HBM-VMEARLY-IDX bench)
DMA_WIN = BLAT.DMA_CMD_LEAD - BLAT.DMA_NEXT_CMD_K     # dma_min_next_issue relative to the previous move's end_at


def _install_bldma_split():
    """bl_dma only on VM-read DMA records (HBM-VMEARLY-DMA, d4g_bl_dma_split_1019 --mode kvwb)"""
    from hgi_sim import d4g_bl_dma_split_1019 as SP
    orig_cross, orig_knob = RL.crossings, RL._knob

    def crossings(r, upper=False):
        c = orig_cross(r, upper)
        op = getattr(r, "orig_op", f"{r.unit}.{r.op}")
        u, o = op.split(".", 1)
        if op == "DMA.SWAP":
            o = "LOAD" if "in" in (r.tag or "").split()[-1] else "STORE"
        if u == "DMA" and o in ("LOAD", "FENCE") and "VM_HBM" in c:
            c = dict(c)
            c["VM_HBM_RQ"] = c.pop("VM_HBM")
        return c

    def knob(b, o, only=None):
        b2, o2 = dict(b), dict(o)
        b2["VM_HBM_RQ"] = b.get("VM_HBM", 0.0)
        ov = o.get("VM_HBM", 0.0)
        o2["VM_HBM_RQ"] = SP.PLAN_B_VM_HBM if abs(ov - SP.BL_DMA) < 1e-9 else ov
        return orig_knob(b2, o2, only)
    RL.crossings, RL._knob = crossings, knob


if BLDMA == "kvwb":
    _install_bldma_split()
elif BLDMA != "all":
    raise SystemExit(f"OT_VME_BLDMA={BLDMA}: kvwb | all")

_KNOB0 = RL._knob


def _knob(b, o, only=None):
    _ACTIVE["b"], _ACTIVE["o"] = b, o
    return _KNOB0(b, o, only)


RL._knob = _knob


def _client(r):
    op = getattr(r, "orig_op", f"{r.unit}.{r.op}")
    u, o = op.split(".", 1)
    if u in ("SM", "ATT"):
        return "xl", op
    if u == "COLL":
        return "coll", op
    if u == "DMA":
        if o == "SWAP":
            w = (r.tag or "").split()
            o = "LOAD" if (w and "in" in w[-1]) else "STORE"
        return ("dma" if o not in ("LOAD", "FENCE") else None), op
    if u == "IDX" or u == "ARGMAX":
        return "idx", op
    return None, op


def hide_delta(r):
    """(client, hideable VM-bank round-trip edges) of one record under the running job's stage set"""
    cl, op = _client(r)
    if cl is None:
        return (None, 0.0)
    if cl == "idx":
        if not R.Q._D4G.get("bl_idx"):
            return (cl, 0.0)
        bl = R.INFO_TERMS["bl_idx"][0]
        return (cl, float(bl["idx"] if op in ("IDX.INDEX", "IDX.TOPK") else bl["argmax"] if r.unit == "ARGMAX" else 0.0))
    b, o = _ACTIVE.get("b"), _ACTIVE.get("o")
    if not b or not o or not _PLANB:
        return (cl, 0.0)
    o0 = dict(o, **{k: _PLANB[k] for k in BL_KEYS if k in _PLANB})
    if all(o.get(k) == o0.get(k) for k in BL_KEYS):
        return (cl, 0.0)
    k1, k0 = _KNOB0(b, o), _KNOB0(b, o0)
    d = RL.added(r, k1["delta"], False, None, b, o) - RL.added(r, k0["delta"], False, None, b, o0)
    if cl == "coll":
        d *= 2.0 / 3.0
    return (cl, max(0.0, d))


def early(i, u, c, t0, vdi, deps, fps, end, ex, recs, ret_w, starts_u, ends_u):
    """record i's start / occupancy with its VM read issued early (module doc)"""
    cl, d = vdi
    r = recs[ex[i][0]]
    lay = getattr(r, "layer", ex[i][1])
    lay = lay if isinstance(lay, int) else ex[i][1]
    N = N_OF.get(cl, 0)
    R._add(f"vme:{cl}:base", d)
    R._add(f"vme_L{lay}:{cl}:base", d)
    R._add(f"vme:{cl}:records", 1)
    if N <= 0:
        R._add(f"vme:{cl}:exposed", d)
        R._add(f"vme_L{lay}:{cl}:exposed", d)
        return c, t0
    rd = fps[i][0]
    raw = 0.0
    for j in deps[i]:
        if any(T.overlap(iv, w) for iv in rd for w in fps[j][1]):
            raw = max(raw, end[j] + ret_w[recs[ex[j][0]].unit])
    if cl == "dma":                       # one move held: ISSUE_AHEAD 0 calendar (dma_min_next_issue)
        win = (ends_u[-1] + DMA_WIN) if ends_u else 0.0
        slot = 0.0
    elif cl == "idx":                     # A_i = max(RAW_i, F_i - LB), F_i = end(i-1) + 1, LB = d + 2
        win = 0.0
        slot = (ends_u[-1] + 1.0 - (d + IDX_LB_OVER_BL)) if ends_u else 0.0
    else:
        win = starts_u[-N] if len(starts_u) >= N else 0.0
        slot = (ends_u[-(N + 1)] - d) if len(ends_u) >= N + 1 else 0.0
    t_iss = min(t0, max(raw, win, slot))
    s = max(t0, t_iss + d)
    R._add(f"vme:{cl}:exposed", s - t0)
    R._add(f"vme_L{lay}:{cl}:exposed", s - t0)
    R._add(f"vme:{cl}:bound_raw", 1 if raw >= max(win, slot) and raw + d > t0 else 0)
    _trace(lay, r, cl, d, s - t0, raw, win, slot, t0)
    return c - d, s


def _trace(lay, r, cl, d, exp, raw, win, slot, t0):
    """OT_VME_TRACE=<layer>:<path>: one TSV row per hidden-candidate record of that layer (debug / sub-lane record list)"""
    tr = os.environ.get("OT_VME_TRACE")
    if not tr or str(lay) != tr.split(":", 1)[0]:
        return
    bound = "raw" if raw >= max(win, slot) and raw + d > t0 else ("window" if win >= slot and win + d > t0 else
                                                                    ("slot" if slot + d > t0 else "hidden"))
    with open(f"{tr.split(':', 1)[1]}.{os.getpid()}", "a") as f:
        f.write(f"{lay}\t{getattr(r, 'orig_op', r.unit + '.' + r.op)}\t{(r.tag or '')[:60]}\t{cl}\t{d:.1f}\t{exp:.1f}\t{bound}\n")


def schedule(recs, pos, mode="S2", token=0, cost_fn=None, wires=True):
    """mode: S0 dataflow | S1 per-unit sequencers (drain waits, no HOL) | S2 the CP as specified | S3 S2 with free
    fetch / decode | SX S2 with dispatch skip-ahead (a held record blocks only later records it has a region hazard
    with, or of its own unit).  wires=False zeroes dispatch_wire / retire_wire."""
    dyn = T.Dyn(pos, token)
    ex = T.expand(recs, pos, token)
    n = len(ex)
    units = T.HGI.UNITS
    costs, fps = [], []
    for (k, L, L1) in ex:
        r = recs[k]
        dyn.v[4], dyn.v[8] = L, L1
        costs.append(cost_fn(r, dyn, L))
        fps.append(T.footprint(r, dyn, L))
    vd = [hide_delta(recs[k]) for (k, *_) in ex]          # VMEARLY: (client, hideable bank-latency edges) per record
    unit_ends = defaultdict(list)
    dread = []
    for (k, L, L1) in ex:
        r = recs[k]
        if "I" in r.desc and any(d.indexed for d in r.desc.values()):
            dyn.v[4], dyn.v[8] = L, L1
            dread.append([T.interval(r.desc["I"], dyn, L)])
        else:
            dread.append([])
    # true dependences (exact intervals): producer = last writer of an overlapping region (RAW / WAW), readers since
    deps = [[] for _ in range(n)]
    ddeps = [[] for _ in range(n)]     # WAR on an indexed record's I table: the id is read at dispatch (spec 2.2.4)
    writers, readers = [], []          # (interval, j)
    for i in range(n):
        rd, wr = fps[i]
        for iv in rd:
            for (w, j) in writers:
                if T.overlap(iv, w):
                    deps[i].append(j)
        for iv in wr:
            for (w, j) in writers:
                if T.overlap(iv, w):
                    deps[i].append(j)
            for (x, j) in readers:
                if T.overlap(iv, x):
                    (ddeps if x in dread[j] else deps)[i].append(j)
        for iv in wr:
            writers = [(w, j) for (w, j) in writers if not (w[0] == iv[0] and iv[1] <= w[1] and w[2] <= iv[2])]
            writers.append((iv, i))
            readers = [(x, j) for (x, j) in readers if not T.overlap(x, iv)]
        for iv in rd:
            readers.append((iv, i))
        deps[i] = sorted(set(deps[i]))
        ddeps[i] = sorted(set(ddeps[i]) - set(deps[i]))
    # STREAM producer -> consumer pairs (credit-ordered: the consumer runs alongside its producer, no wait bit)
    tails = T.CAL["units"].get("STREAM.tail", {}).get("value", {})
    sdep, last_prod = [None] * n, {}
    for i, (k, *_) in enumerate(ex):
        r = recs[k]
        for key in ("A", "B", "C", "D"):
            d = r.desc.get(key)
            if d is not None and d.space == "STREAM" and d.base in last_prod:
                sdep[i] = last_prod[d.base]                 # every consumer of the stream rides its producer
        for key in ("O", "R"):
            d = r.desc.get(key)
            if d is not None and d.space == "STREAM":
                last_prod[d.base] = i
    cpc = T.CAL["cp"]
    fetch_lat, fetch_iss, req = cpc["fetch_latency"]["value"], cpc["fetch_issue_cycles"]["value"], \
        cpc["fetch_req_bytes"]["value"]
    ring = cpc["ring_bytes"]["value"]
    dwire, rwire, qd = cpc["dispatch_wire"]["value"], cpc["retire_wire"]["value"], cpc["queue_depth"]["value"]
    if not wires:
        dwire = rwire = 0
    edges = cpc.get("dispatch_edges", {}).get("value", {}) if wires else {}

    def wire_of(rec):
        """per-unit dispatch / retire wire stages (R25G floorplan edges where priced, else the estimate)"""
        if rec.unit == "FUSED" and rec.op.startswith("QDQ") and "FUSED.QDQ" in edges:
            return edges["FUSED.QDQ"]
        return edges.get(rec.unit, dwire)
    nm_rd = [set(getattr(recs[k], "reads", ())) for k, *_ in ex]
    nm_wr = [set(getattr(recs[k], "writes", ())) for k, *_ in ex]
    # record byte offsets in the image (for fetch); loop replays hit the ring when the body fits
    offs, o = [], 0
    for r in recs:
        offs.append(o)
        o += T.rec_bytes(r)
    body = {}
    for k, r in enumerate(recs):
        if r.unit == "CTL" and r.op == "LOOP":
            e = next(j for j in range(k + 1, len(recs)) if recs[j].unit == "CTL" and recs[j].op == "ENDLOOP")
            body = dict(lo=k, hi=e, bytes=offs[e] - offs[k] + T.rec_bytes(recs[e]))
    fetched_at = {}

    def fetch_ready(i, k, L):
        if mode in ("S0", "S1", "S3"):
            return 0.0
        if body and body["lo"] < k <= body["hi"] and L > 0 and body["bytes"] <= ring:
            return 0.0                                         # replay from the ring
        key = (k, L if body and body["lo"] < k <= body["hi"] and body["bytes"] > ring else 0)
        if key not in fetched_at:
            end = offs[k] + T.rec_bytes(recs[k])
            nreq = math.ceil(end / req)
            fetched_at[key] = fetch_lat + nreq * fetch_iss    # streaming prefetch from the doorbell
        return fetched_at[key]
    start = [0.0] * n
    end = [0.0] * n
    disp = [0.0] * n
    unit_last = {}
    unit_starts = defaultdict(list)
    last_end_unit = defaultdict(float)
    outstanding_end = defaultdict(float)      # per unit: retire time of the last dispatched record
    cp_t = 0.0
    dec_t = 0.0
    ret_w = defaultdict(lambda: float(rwire))             # retire wire of each unit's last record
    hol_block = [0.0] * n
    wait_block = [0.0] * n
    why = [None] * n                          # S2: (ready, wait, queue, cp, wait unit) of each dispatch
    cp_busy = 0.0
    for i, (k, L, *_) in enumerate(ex):
        r = recs[k]
        c = costs[i][0]
        u = r.unit
        if mode == "S0":
            t0 = max([end[j] for j in deps[i]] + [start[j] for j in ddeps[i]] +
                     [last_end_unit[u] if u not in T.PIPELINED else 0.0] +
                     [outstanding_end["DMA"] if (u == "DMA" and r.op == "FENCE") else 0.0])
            if u in T.PIPELINED and unit_starts[u]:
                t0 = max(t0, unit_starts[u][-1] + T.PIPELINED[u])
            start[i] = t0
        else:
            nch = (1 if r.sut is not None else 0) + len(r.descs_in_order())
            dcyc = 0.0 if mode in ("S1",) else cpc["decode_header"]["value"] + nch * cpc["decode_per_chunk"]["value"]
            alat = 0.0 if mode in ("S1",) else cpc["addr_latency"]["value"]
            nidx = sum(1 for d in r.desc.values() if d.indexed)
            f_r = fetch_ready(i, k, L)
            dec_t = max(dec_t + dcyc, f_r + dcyc) if mode in ("S2", "SX") else (dec_t + dcyc)
            ready = dec_t + alat
            wt, wun = 0.0, None
            for b, un in enumerate(units):
                if r.wait >> b & 1 and outstanding_end[un] + ret_w[un] > wt:
                    wt, wun = outstanding_end[un] + ret_w[un], un
            q = unit_starts[u]
            qt = q[-qd] if len(q) >= qd else 0.0
            if nidx:
                # C3b: the dispatcher reads the index word only after its producer retired (the wait is satisfied)
                ivs = [T.interval(r.desc["I"], dyn, L)] if "I" in r.desc else []
                prod = max([end[j] + ret_w[recs[ex[j][0]].unit] for j in deps[i]
                            if any(T.overlap(w_, iv) for w_ in fps[j][1] for iv in ivs)] + [0.0])
                ready = max(ready, prod + cpc["indexed_read"]["value"] * nidx)
            if mode == "S1":
                # per-unit sequencers, drain semantics: wait for every unit that produced an input to drain
                wt = max([outstanding_end[recs[ex[j][0]].unit] for j in deps[i]] + [0.0])
                d_t = max(ready, wt)
            elif mode == "SX":
                # skip-ahead: order only against earlier records with a region hazard, and the unit's own queue
                lim = qt
                for j in range(i - 1, max(-1, i - 64), -1):
                    if recs[ex[j][0]].unit == u or (nm_rd[i] & nm_wr[j]) or (nm_wr[i] & (nm_rd[j] | nm_wr[j])):
                        lim = max(lim, disp[j] + 1)
                d_t = max(ready, wt, lim)
                hol_block[i] = max(0.0, d_t - max(ready, wt, qt))
                cp_busy += dcyc + cpc["dispatch_cycles"]["value"]
            else:
                d_t = max(ready, cp_t + cpc["dispatch_cycles"]["value"], wt, qt)
                why[i] = (ready, wt, qt, cp_t + cpc["dispatch_cycles"]["value"], wun)
                wait_block[i] = max(0.0, wt - max(ready, cp_t + 1, qt))
                hol_block[i] = max(0.0, d_t - max(ready, wt, qt))
                cp_busy += dcyc + cpc["dispatch_cycles"]["value"]
                cp_t = d_t
            disp[i] = d_t
            t0 = max(d_t + (wire_of(r) if mode != "S1" else 0.0), last_end_unit[u] if u not in T.PIPELINED else 0.0)
            if u == "DMA" and r.op == "FENCE":           # posted HBM writes: the fence completes after every DMA record
                t0 = max(t0, outstanding_end["DMA"])
            if u in T.PIPELINED and q:
                t0 = max(t0, q[-1] + T.PIPELINED[u])
            start[i] = t0
            if vd[i][1] > 0.0:
                c, start[i] = early(i, u, c, t0, vd[i], deps, fps, end, ex, recs, ret_w, unit_starts[u], unit_ends[u])
        if sdep[i] is not None:
            j = sdep[i]
            start[i] = max(start[i], start[j])
            end[i] = max(start[i] + c, end[j] + tails.get(u, 20))
        else:
            end[i] = start[i] + c
        if mode not in ("S0", "S1"):
            ret_w[u] = wire_of(r) if wires else 0.0
        if u in T.PIPELINED:
            end[i] = max(end[i], last_end_unit[u])         # in-order retire
        last_end_unit[u] = end[i]
        unit_starts[u].append(start[i])
        unit_ends[u].append(end[i])
        outstanding_end[u] = max(outstanding_end[u], end[i])
    total = max(end) if n else 0.0
    races = []
    if mode != "S0":
        for i in range(n):
            for j in deps[i]:
                same = recs[ex[i][0]].unit == recs[ex[j][0]].unit and j < i
                war_only = same and not any(T.overlap(w_, x) for w_ in fps[i][1] for x in fps[j][1]) and \
                    not any(T.overlap(x, w_) for x in fps[i][0] for w_ in fps[j][1])
                if end[j] > start[i] + 1e-9 and not (same and recs[ex[i][0]].unit not in T.PIPELINED) and \
                        not (war_only and start[j] <= start[i]):
                    races.append(dict(rec=ex[i][0], L=ex[i][1], tag=recs[ex[i][0]].tag, producer=recs[ex[j][0]].tag,
                                      early=round(end[j] - start[i], 1)))
            for j in ddeps[i]:
                if disp[j] > start[i] + 1e-9:
                    races.append(dict(rec=ex[i][0], L=ex[i][1], tag=recs[ex[i][0]].tag, producer=recs[ex[j][0]].tag,
                                      early=round(disp[j] - start[i], 1),
                                      kind="I table overwritten before the dispatcher read it"))
    # per-unit busy / idle split: idle caused by true dependences vs by issue (CP, HOL, drain waits)
    per_unit = defaultdict(lambda: dict(busy=0.0, idle_true_dep=0.0, idle_issue=0.0, records=0))
    prev = defaultdict(float)
    for i, (k, L, *_) in enumerate(ex):
        u = recs[k].unit
        pu = per_unit[u]
        pu["records"] += 1
        pu["busy"] += end[i] - start[i]
        e_true = max([prev[u]] + [end[j] for j in deps[i]])
        gap_true = max(0.0, e_true - prev[u])
        gap_issue = max(0.0, start[i] - max(e_true, prev[u]))
        pu["idle_true_dep"] += gap_true
        pu["idle_issue"] += gap_issue
        prev[u] = end[i]
    fam = defaultdict(float)
    for i, (k, L, *_) in enumerate(ex):
        fam[recs[k].family or recs[k].tag] += end[i] - start[i]
    return dict(mode=mode, total_cycles=total, records_executed=n, deps=deps, start=start, end=end, disp=disp,
                costs=costs, ex=ex, races=races, per_unit={k: {a: round(b, 1) for a, b in v.items()}
                                                           for k, v in per_unit.items()},
                why=why, cp_busy=round(cp_busy, 1), hol_block=round(sum(hol_block), 1), wait_block=round(sum(wait_block), 1),
                family_unit_cycles={k: round(v, 1) for k, v in sorted(fam.items(), key=lambda x: -x[1])})



T.schedule = schedule


def main():
    import json
    from pathlib import Path
    from hgi_sim import d4g_reprice3b_1019 as R3B
    a = sys.argv[1:]
    bw = float(a[a.index("--bw") + 1]) if "--bw" in a else 45.03
    if bw > BW_H9B_MAX and LAYOUT != "rotated":
        raise SystemExit(f"--bw {bw} is a successor-controller price: it holds ONLY with the rotated bank layout "
                         f"(owner 10-19, HBM-MC2 89200325b); OT_VME_LAYOUT={LAYOUT} refused")
    st = json.loads((R.ROOT / "results/arch/hbm_plan_study_1017/stages.json").read_text())
    _PLANB.update(st["plan_b"])
    argv = list(sys.argv[1:])
    sys.argv = [sys.argv[0]] + argv
    rc = R3B.main()
    out = Path(argv[argv.index("--out") + 1])
    doc = json.loads(out.read_text())
    doc["lane"] = "HBM-VMEARLY"
    doc["tool"] = "tools/hgi_sim/d4g_vmearly_1019.py (wraps d4g_reprice3b_1019 with an early-issue timing.schedule)"
    doc["vme"] = dict(issue_ahead=N_OF, bl_dma=BLDMA, layout=LAYOUT, bw=bw, rule=__doc__)
    summ = {}
    for k, row in doc["table"].items():
        s = {}
        for side in ("ds", "qwen"):
            ra = row.get("rp_added_sum", {}).get(side, {})
            s[side] = {cl: dict(base=round(ra.get(f"vme:{cl}:base", 0.0), 1), exposed=round(ra.get(f"vme:{cl}:exposed", 0.0), 1),
                                records=ra.get(f"vme:{cl}:records", 0), raw_bound=ra.get(f"vme:{cl}:bound_raw", 0))
                       for cl in CLIENTS}
        summ[k] = dict(ds_ar_tok_s=row["ds_ar_tok_s"], qwen_tok_s=row["qwen_tok_s"], ds_ar_cycles=row["ds_ar_cycles"],
                       qwen_cycles=row["qwen_cycles"], clients=s)
    doc["vme_summary"] = summ
    out.write_text(json.dumps(doc, indent=1, default=str) + "\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
