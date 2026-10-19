#!/usr/bin/env python3
"""HBM-NEXT-CMTP: object-level VM allocator + HGI-1R binary record emitter (FIRST VERSION, step 2).

Input: the compiled N-row programme (plane_compiler headline knobs; M.ds_compile) and its S2 timeline per layer
segment (static_check.schedule_segments).  The compiled records keep the AR descriptors (row 0 addresses of the AR VM
map) plus per-position footprints shifted by VM_OFF per position (and SLOT_OFF per union expert slot): the allocator
turns that bookkeeping into a real VM map; the emitter writes HGI-1R bytes (isa_rows.encode) against it.

ALLOCATOR (per layer segment):
  1. CLUSTERS: AR VM word ranges joined by any footprint interval and by all intervals of one descriptor (so every
     descriptor addresses exactly one cluster; relocation is one base shift a cluster).
  2. INSTANCES: word-level liveness as static_check C4 (a word is live from the START of its writer -- the writer
     owns the words while it runs -- to the END of its last reader before the next write); a cluster copy's live
     spans are merged into instances (gaps with no live word split them).
  3. OBJECTS: the per-position copies (p = 0 .. N - 1) of one cluster whose instances overlap in time form ONE ROW
     ARRAY: N rows at a fixed row stride (cluster size rounded up to 8 words), lifetime = the union -- so an N-row
     record addresses row rho at base + rho x rs (ROWX rs_k).  Clusters only read in the segment (gains, tables, HC
     rows) are CONSTANTS: one row, rs = 0 (broadcast).  The entering columns h / PRE are PINNED row arrays at VM 0
     (live across segments).  Union expert slot j copies are separate objects (one per slot).
  4. PLACEMENT: first-fit by start time into the address space; the high-water mark is the VM this map needs.  It is
     >= the C4 word-level peak (C4 = lower bound: no fragmentation, no cluster granularity).
EMITTER: every record with VM operands in clusters gets its bases relocated (row 0) and, when it carries N > 1
positions, a ROWX (n = N, slot0 = 0, rs_k = the row stride of operand k's object or 0, SM: rpl = best_rpl, param
[5:2] = N - 1).  Checked per record: isa_rows.check (legality), encode -> decode round trip identical, expand(): every
row's descriptor intervals fall inside that row of the allocated object, rows independent (R2).  AR (N = 1) is the
identity: no relocation, no ROWX, bytes == records.Rec.encode.
NOT YET (next): union expert slots as the IDX.UNION + rsel CTL.LOOP form (emitted here as SKIPPED, counted), the
IDX.UNION record itself, CTL.USERS banks for the users image, implicit engine state (fixed-address intervals no
descriptor names: reported, pinned at their AR address), whole-token image assembly + VEH hand-off.

    PYTHONPATH=tools python3 tools/hbm_next/emitter.py --mode mtp --layers 0,1 --out DIR
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "hbm_next"))

import isa_rows as IR  # noqa: E402
import plane_compiler as PC  # noqa: E402
import static_check as SC  # noqa: E402

VW, VO = SC.VM_WORDS, SC.VM_OFF
SLOT_OFF = 1 << 28
ALIGN = 8
HPRE = ((0, 20480), (40960, 40964))
VM_GROWN = VW + 5 * 30000


class UF:
    def __init__(self):
        self.p = {}

    def f(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def u(self, a, b):
        a, b = self.f(a), self.f(b)
        if a != b:
            self.p[max(a, b)] = min(a, b)


def desc_ivs(rec, dyn, L):
    """row-0 (AR) VM intervals per operand"""
    from hgi_sim import timing as T
    out = {}
    for k, d in rec.desc.items():
        if d.space == "VM":
            out[k] = [(lo, hi) for sp, lo, hi in T.intervals(d, dyn, L) if sp == "VM"]
    return out


def values(seg, s, fps, dyn):
    """VALUE-LEVEL liveness.  Every write of an operand interval in a copy creates a value [a, b) with lifetime
    [writer start, last reader end]; every operand read joins (union-find) the values it reads, so a component is a
    set of values some descriptor reads TOGETHER (their AR-relative layout is kept: one base shift relocates it).
    Live-in reads: union-slot copies j >= 1 read the position's slot-0 copy (compile_verify shifts every footprint of
    a union-slot record, inputs included); HPRE words = the pinned entering columns; words no copy ever writes =
    CONSTANTS (one shared value); other words = data live from cycle 0.
    -> (vals, uf, opmap {(i, opk, cp): value id}, seg_end)"""
    ex, start, end = s["ex"], s["start"], s["end"]
    order = sorted(range(len(ex)), key=lambda i: start[i])
    SPC = SLOT_OFF // VO
    # per record: (opk, is_write, [(cp, a, b)]) -- descriptor operands per copy, then implicit intervals as anonymous
    acc = {}
    wmask = np.zeros(VW, bool)
    for i in order:
        k, L, _ = ex[i]
        r = seg[k]
        rd, wr = fps[i]
        cps = sorted({lo // VO for side in (rd, wr) for sp, lo, hi in side if sp == "VM"})
        ops = []
        seen = set()
        for opk, lst in desc_ivs(r, dyn, L).items():
            isw = opk in ("O", "R")
            ivs = [(cp, a_, min(b_, VW)) for cp in cps for a_, b_ in lst if a_ < VW]
            ops.append((opk, isw, ivs))
            seen.update((isw, cp * VO + a_, cp * VO + b_) for cp, a_, b_ in ivs)
        for isw, side in ((False, rd), (True, wr)):
            for n_, (sp, lo, hi) in enumerate(side):
                if sp == "VM" and (isw, lo, hi) not in seen:
                    cp, a_ = lo // VO, lo % VO
                    if a_ < VW:
                        ops.append((f"imp{n_}", isw, [(cp, a_, min(hi - cp * VO, VW))]))
        acc[i] = ops
        for opk, isw, ivs in ops:
            if isw:
                for cp, a_, b_ in ivs:
                    wmask[a_:b_] = True
    hp = np.zeros(VW, bool)
    for a_, b_ in HPRE:
        hp[a_:b_] = True
    vals = []
    uf = UF()
    vid = defaultdict(lambda: np.full(VW, -1, np.int64))
    const_vid = np.full(VW, -1, np.int64)
    pin_vid = {}

    def new(cp, a_, b_, t0, t1, kind, anchor):
        vals.append(dict(cp=cp, a=a_, b=b_, t0=t0, t1=t1, kind=kind, anchor=anchor))
        uf.f(len(vals) - 1)
        return len(vals) - 1

    def read(cp, a_, b_, t, anchor, selfw=None, swlog=None):
        """value ids covering [a_, b_) of copy cp at a read ending at t (creating live-ins).  selfw: the reader's
        own VM write intervals in this copy -- an undefined word it also writes (outside h / PRE) is its own output
        (in-place all-gather destination), not a live-in: skipped (static_check C4 does the same)"""
        ids = set()
        v = vid[cp][a_:b_]
        und = v < 0
        if selfw and und.any():
            sw = np.zeros(b_ - a_, bool)
            for aw, bw in selfw:
                if aw < b_ and a_ < bw:
                    sw[max(aw, a_) - a_:min(bw, b_) - a_] = True
            sw &= und & ~hp[a_:b_]
            if sw.any():
                selfw_words[anchor.split("|")[1]] += int(sw.sum())
                if swlog is not None:
                    ws = np.nonzero(sw)[0] + a_
                    for run in np.split(ws, np.nonzero(np.diff(ws) != 1)[0] + 1):
                        swlog.append((cp, int(run[0]), int(run[-1]) + 1))
                und = und & ~sw
                for x in np.unique(v[v >= 0]).tolist():
                    ids.add(int(x))
                    vals[x]["t1"] = max(vals[x]["t1"], t)
                w = np.nonzero(und)[0] + a_
                if w.size:
                    for run in np.split(w, np.nonzero(np.diff(w) != 1)[0] + 1):
                        ids |= read(cp, int(run[0]), int(run[-1]) + 1, t, anchor)
                return ids
        if und.any():
            j, p_ = cp // SPC, cp % SPC
            w = np.nonzero(und)[0] + a_
            runs = np.split(w, np.nonzero(np.diff(w) != 1)[0] + 1)
            for run in runs:
                x0, x1 = int(run[0]), int(run[-1]) + 1
                if j >= 1:
                    ids |= read(p_, x0, x1, t, anchor)
                    continue
                if hp[x0:x1].all():
                    for h0, h1 in HPRE:
                        if h0 <= x0 < h1:
                            if (p_, h0) not in pin_vid:
                                pin_vid[(p_, h0)] = new(p_, h0, h1, -1.0, 1e18, "pinned_column", f"hpre{h0}")
                            vid[cp][x0:x1] = pin_vid[(p_, h0)]
                elif not wmask[x0:x1].any():
                    cv = const_vid[x0:x1]
                    if (cv < 0).any():
                        nv = new(-1, x0, x1, 0.0, t, "constant", anchor)
                        cv[cv < 0] = nv
                    vid[cp][x0:x1] = const_vid[x0:x1]
                else:
                    vid[cp][x0:x1] = new(cp, x0, x1, 0.0, t, "livein", anchor)
            v = vid[cp][a_:b_]
        for x in np.unique(v[v >= 0]).tolist():
            ids.add(int(x))
            vals[x]["t1"] = max(vals[x]["t1"], t)
        return ids
    opmap = {}
    selfw_words = defaultdict(int)
    pitch = defaultdict(set)                 # value id -> descriptor strides of multi-row operands that join it
    for i in order:
        k, L, _ = ex[i]
        r = seg[k]
        anchor = f"{L}|{r.unit}.{r.op}|{r.tag}"
        dstr = {opk: (r.desc[opk].stride if opk in r.desc and r.desc[opk].m > 1 else 0) for opk, _, _ in acc[i]}
        pend_join = []
        wr_by_cp = defaultdict(list)
        for opk, isw, ivs in acc[i]:
            if isw:
                for cp, a_, b_ in ivs:
                    wr_by_cp[cp].append((a_, b_))
        for opk, isw, ivs in acc[i]:
            if isw:
                continue
            per = defaultdict(set)
            swlog = []
            for cp, a_, b_ in ivs:          # every interval of the operand in one copy: one component
                per[cp] |= read(cp, a_, b_, end[i], anchor, selfw=wr_by_cp.get(cp), swlog=swlog)
            if swlog:
                pend_join.append((opk, swlog))
            for cp, ids in per.items():
                ids = sorted(ids)
                for x in ids[1:]:
                    uf.u(ids[0], x)
                if ids:
                    opmap[(i, opk, cp)] = ids[0]
                    if len(ids) > 1 and dstr.get(opk):
                        pitch[ids[0]].add(dstr[opk])
        shared_load = (getattr(r, "orig_op", "") == "DMA.LOAD" and getattr(r, "mtp_kind", "") == "shared"
                       and getattr(r, "npos", 1) > 1)
        for opk, isw, ivs in acc[i]:
            if not isw:
                continue
            one = {}
            first = {}
            for cp, a_, b_ in ivs:
                if hp[a_:b_].all() and cp // SPC == 0:      # the residual column h / PRE: updated IN PLACE
                    for h0, h1 in HPRE:
                        if h0 <= a_ < h1:
                            if (cp, h0) not in pin_vid:
                                pin_vid[(cp, h0)] = new(cp, h0, h1, -1.0, 1e18, "pinned_column", f"hpre{h0}")
                            nv = pin_vid[(cp, h0)]
                elif shared_load:        # position-independent constant load: ONE value every copy reads (rs = 0)
                    if (a_, b_) not in one:
                        one[(a_, b_)] = new(-1, a_, b_, start[i], end[i], "shared_load", anchor)
                    nv = one[(a_, b_)]
                else:
                    nv = new(cp, a_, b_, start[i], end[i], "data", anchor)
                vid[cp][a_:b_] = nv
                if (opk, cp) in first:
                    uf.u(first[(opk, cp)], nv)
                else:
                    first[(opk, cp)] = nv
                opmap[(i, opk, cp)] = first[(opk, cp)]
        for opk, swlog in pend_join:        # the self-overwritten words join the read operand to this record's output
            for cp, a_, b_ in swlog:
                outv = np.unique(vid[cp][a_:b_])
                outv = [int(x) for x in outv if x >= 0]
                if not outv:
                    continue
                if (i, opk, cp) in opmap:
                    for x in outv:
                        uf.u(opmap[(i, opk, cp)], x)
                else:
                    opmap[(i, opk, cp)] = outv[0]
                    for x in outv[1:]:
                        uf.u(outv[0], x)
    for v in list(pitch):
        pitch[uf.f(v)] |= pitch.pop(v) if uf.f(v) != v else set()
    for n, v in enumerate(vals):
        v["_root"] = uf.f(n)
    pr = defaultdict(set)
    for v, sset in pitch.items():
        pr[uf.f(v)] |= sset
    uf.pitch = dict(pr)
    uf.selfw_words = dict(selfw_words)
    return vals, uf, opmap, float(max(end) if end else 0.0)


def compaction(lst, uf, lo, hi):
    """a SPARSE component (strided multi-row descriptors over mostly unused AR space, e.g. the expert-slot pitch
    9,728 words holding 24-53 used words a slot) is re-laid at its own row pitch: x -> base + row x S' + off,
    row = (x - lo) div S, off = (x - lo) mod S, S' = the widest used row (aligned); every descriptor addressing it
    gets base mapped and stride S -> S'.  -> dict(S, S2, nrow, size) or None"""
    S = set()
    for root, c in lst:
        S |= getattr(uf, "pitch", {}).get(root, set())
    if len(S) != 1:
        return None
    S = S.pop()
    if S <= 0:
        return None
    w = 0
    for root, c in lst:
        for a_, b_ in c["mem"]:
            off = (a_ - lo) % S
            if off + (b_ - a_) > S:
                return None
            w = max(w, off + (b_ - a_))
    S2 = -(-w // ALIGN) * ALIGN
    nrow = -(-(hi - lo) // S)
    size = nrow * S2
    if size >= (hi - lo) * 0.8:
        return None
    return dict(S=S, S2=S2, nrow=nrow, size=size)


def amap(o, x):
    """AR address x (row 0 copy) -> offset inside the object's row"""
    pk = o.get("pack")
    if not pk:
        return x - o["lo"]
    r_, off = divmod(x - o["lo"], pk["S"])
    return r_ * pk["S2"] + off


def build_objects(vals, uf, n_rows):
    """components -> objects.  Components of the per-position copies with the same AR range and the same anchor
    (the record that first defines them) overlapping in time are ONE ROW ARRAY (row = position); constants and pinned
    columns are shared / pinned.  -> (objs, comp2obj {root: (obj index, row)})"""
    SPC = SLOT_OFF // VO
    comp = defaultdict(lambda: dict(a=VW, b=0, t0=1e18, t1=-1.0, cp=None, kind=None, anchor=None, mem=[]))
    for n, v in enumerate(vals):
        c = comp[uf.f(n)]
        c["mem"].append((v["a"], v["b"]))
        c["a"], c["b"] = min(c["a"], v["a"]), max(c["b"], v["b"])
        c["t0"], c["t1"] = min(c["t0"], v["t0"]), max(c["t1"], v["t1"])
        if c["cp"] is None or v["t0"] < c.get("_ft", 1e18):
            c["_ft"] = v["t0"]
            c["cp"], c["kind"], c["anchor"] = v["cp"], v["kind"], v["anchor"]
    objs, comp2obj = [], {}
    by = defaultdict(list)
    for root, c in comp.items():
        if c["kind"] in ("constant", "pinned_column", "shared_load"):
            key = (c["kind"], c["a"], c["b"]) if c["kind"] == "pinned_column" else ("constant", root)
            by[key].append((root, c))
        else:
            j, p_ = c["cp"] // SPC, c["cp"] % SPC
            by[(j, c["a"], c["b"], c["anchor"])].append((root, c))
    for key, lst in by.items():
        if key[0] == "pinned_column":
            size = -(-(key[2] - key[1]) // ALIGN) * ALIGN
            o = dict(kind="pinned_column", rows=n_rows, stride=size, size=size, lo=key[1], hi=key[2], t0=-1.0, t1=1e18)
            objs.append(o)
            for root, c in lst:
                comp2obj[root] = (len(objs) - 1, c["cp"] % SPC)
            continue
        if key[0] == "constant":
            (root, c), = lst
            size = -(-(c["b"] - c["a"]) // ALIGN) * ALIGN
            objs.append(dict(kind=c["kind"], rows=1, stride=0, size=size, lo=c["a"], hi=c["b"],
                             t0=0.0 if c["kind"] == "constant" else c["t0"], t1=c["t1"], anchor=c["anchor"]))
            comp2obj[root] = (len(objs) - 1, 0)
            continue
        lst.sort(key=lambda rc: rc[1]["t0"])
        groups = []
        for root, c in lst:
            p_ = c["cp"] % SPC
            g = groups[-1] if groups else None
            if g and c["t0"] <= g["t1"] and p_ not in g["ps"]:
                g["t1"] = max(g["t1"], c["t1"])
                g["t0"] = min(g["t0"], c["t0"])
                g["ps"][p_] = root
            else:
                groups.append(dict(t0=c["t0"], t1=c["t1"], ps={p_: root}))
        size = -(-(key[2] - key[1]) // ALIGN) * ALIGN
        pk = compaction(lst, uf, key[1], key[2])
        if pk:
            size = pk["size"]
        for g in groups:
            rows = max(g["ps"]) + 1
            objs.append(dict(kind="row_array" if rows > 1 else "single", rows=rows, stride=size if rows > 1 else 0,
                             size=size, lo=key[1], hi=key[2], t0=g["t0"], t1=g["t1"], slot=key[0],
                             positions=sorted(g["ps"]), pack=pk, anchor=key[3]))
            for p_, root in g["ps"].items():
                comp2obj[root] = (len(objs) - 1, p_ if rows > 1 else 0)
    return objs, comp2obj


def _need(o):
    return o["size"] * max(1, o["rows"]) if o["kind"] != "pinned_column" else o["rows"] * o["stride"]


def object_bound(objs):
    """max over time of the live OBJECT words (pinned columns + every object whose [t0, t1) holds t): the floor any
    placement of these objects can reach; its excess over C4 is the object granularity (row arrays live as the union
    of their rows, clusters live as a whole), the excess of the placement over it is fragmentation"""
    pin = sum(_need(o) for o in objs if o["kind"] == "pinned_column")
    ev = []
    for o in objs:
        if o["kind"] != "pinned_column":
            ev.append((o["t0"], 1, _need(o)))
            ev.append((o["t1"], 0, -_need(o)))
    cur = best = 0
    tbest = 0.0
    for t, k, d in sorted(ev):              # ends (k 0) before starts (k 1) at the same t: [t0, t1) half-open
        cur += d
        if cur > best:
            best, tbest = cur, t
    return pin + best, tbest


def peak_objects(objs, t, top=12):
    """the objects live at cycle t, largest first (what the object bound is made of)"""
    live = [o for o in objs if o["kind"] != "pinned_column" and o["t0"] <= t < o["t1"]]
    live.sort(key=lambda o: -_need(o))
    return [dict(kind=o["kind"], anchor=o.get("anchor") or o.get("slot"), rows=o["rows"], size=o["size"], need=_need(o),
                 ar=[o["lo"], o["hi"]], t0=round(o["t0"], 1), t1=round(o["t1"], 1), packed=bool(o.get("pack")))
            for o in live[:top]]


def _first_fit_by_time(objs, floor):
    live, hw, out = [], floor, {}
    for n, o in sorted(((n, o) for n, o in enumerate(objs) if o["kind"] != "pinned_column"),
                       key=lambda no: (no[1]["t0"], -no[1]["size"])):
        live = [x for x in live if x[0] > o["t0"]]
        need = _need(o)
        a = floor
        for b0, b1 in sorted((b, b + s_) for _, b, s_ in live):
            if a + need <= b0:
                break
            a = max(a, b1)
        out[n] = a
        live.append((o["t1"], a, need))
        hw = max(hw, a + need)
    return hw, out


def _greedy_by_size(objs, floor):
    """offline dynamic storage allocation, greedy by size (largest first, ties: longest life), each object at the
    BEST-FIT gap among the already placed objects it overlaps in time (TFLite / XLA style planner)"""
    order = sorted((n for n, o in enumerate(objs) if o["kind"] != "pinned_column"),
                   key=lambda n: (-_need(objs[n]), -(objs[n]["t1"] - objs[n]["t0"])))
    placed, hw, out = [], floor, {}
    for n in order:
        o, need = objs[n], _need(objs[n])
        occ = sorted((b, b + s_) for (t0, t1, b, s_) in placed if t0 < o["t1"] and o["t0"] < t1)
        best, a = None, floor
        for b0, b1 in occ:
            if b0 - a >= need and (best is None or b0 - a < best[1]):
                best = (a, b0 - a)
            a = max(a, b1)
        base = best[0] if best else a
        out[n] = base
        placed.append((o["t0"], o["t1"], base, need))
        hw = max(hw, base + need)
    return hw, out


def place(objs):
    """pinned columns at 0 (in AR order); the rest by the better of first-fit by start time and greedy by size;
    -> dict(pinned_words, high_water, object_bound, method, per-method high water)"""
    addr = 0
    for o in sorted([o for o in objs if o["kind"] == "pinned_column"], key=lambda o: o["lo"]):
        o["base"] = addr
        addr += _need(o)
    floor = addr
    tries = dict(first_fit_by_time=_first_fit_by_time(objs, floor), greedy_by_size=_greedy_by_size(objs, floor))
    meth = min(tries, key=lambda k: tries[k][0])
    for n, b in tries[meth][1].items():
        objs[n]["base"] = b
    ob, tb = object_bound(objs)
    return dict(pinned_words=floor, high_water=tries[meth][0], object_bound=ob, object_peak_at=tb,
                peak_objects=peak_objects(objs, tb), method=meth, tries={k: v[0] for k, v in tries.items()})


def emit_segment(seg, s, dyn, objs, comp2obj, uf, opmap, n_rows):
    """relocate + ROWX-encode every record; -> (bytes, stats, errors)"""
    ex, start = s["ex"], s["start"]
    st = defaultdict(int)
    errs = []
    blob = bytearray()
    SPC = SLOT_OFF // VO
    cps_of = defaultdict(set)
    for (i, opk, cp) in opmap:
        cps_of[(i, opk)].add(cp)
    for i in sorted(range(len(ex)), key=lambda i: start[i]):
        k, L, _ = ex[i]
        r0 = seg[k]
        if r0.unit == "CTL" and r0.op == "END":
            continue
        kind = getattr(r0, "mtp_kind", "")
        if kind in ("expert", "egather", "expert_union"):
            st["skipped_union_" + kind] += 1        # IDX.UNION + rsel loop form: next step
            continue
        npos = getattr(r0, "npos", 1)
        rec = copy.copy(r0)
        rec.desc = {kk: copy.copy(d) for kk, d in r0.desc.items()}
        rec.unit, rec.op = r0.orig_op.split(".") if getattr(r0, "orig_op", "") else (r0.unit, r0.op)
        rs, omap = {}, {}
        ok = True
        relocate = n_rows > 1
        for opk in (desc_ivs(r0, dyn, L) if relocate else ()):
            cps = sorted(cps_of.get((i, opk), ()))
            if not cps:
                continue
            rows = []
            for cp in cps:
                root = uf.f(opmap[(i, opk, cp)])
                rows.append(comp2obj[root])
            oi, row0 = rows[0]
            o = objs[oi]
            if npos > 1 and len(cps) > 1:
                same = all(x[0] == oi for x in rows) and [x[1] for x in rows] == [row0 + n for n in range(len(rows))]
                bcast = all(x[0] == oi for x in rows) and o["rows"] == 1
                if not (same or bcast):
                    errs.append(dict(rec=r0.tag, op=r0.orig_op, err=f"operand {opk}: copies map to objects/rows "
                                     f"{rows[:6]} (no constant row stride)"))
                    ok = False
                    continue
                if same and o["rows"] > 1:
                    rs[opk] = o["stride"]
            rec.desc[opk].base = o["base"] + row0 * o["stride"] + amap(o, r0.desc[opk].base)
            pk = o.get("pack")
            if pk and r0.desc[opk].m > 1:
                if r0.desc[opk].stride != pk["S"]:
                    errs.append(dict(rec=r0.tag, op=r0.orig_op, err=f"operand {opk}: stride {r0.desc[opk].stride} "
                                     f"!= packed pitch {pk['S']}"))
                    ok = False
                    continue
                rec.desc[opk].stride = pk["S2"]
            omap[opk] = (o, row0)
        rx = None
        if npos > 1 and rec.unit != "CTL" and rec.desc:          # CTL / descriptor-less records take no ROWX
            rpl = 0
            if rec.unit == "SM":
                K, fmt, nc, rows_sm, esz = PC._sm_shape(r0)
                rpl = IR.best_rpl(npos, IR.P_LANES, nc, rows_sm)[0]
                rec.param = (r0.param & 3) | ((npos - 1) << 2)
            rx = IR.RowX(n=npos, slot0=0, rpl=rpl, rs=rs)
        try:
            b = IR.encode(rec, rx)
            r2, rx2, nxt = IR.decode_one(b, 0)
            assert nxt == len(b)
            assert IR.encode(r2, rx2) == b, "round trip"
            if not relocate:
                assert b == rec.encode(), "AR record not byte-identical to records.Rec.encode"
            for bank, rr in IR.expand(r2, rx2):
                rho = bank - rx2.slot0 if rx2 else 0
                for opk, lst in desc_ivs(rr, dyn, L).items():
                    if opk not in omap:
                        continue
                    o, row0 = omap[opk]
                    row = row0 + rho if opk in rs else row0
                    lo_ = o["base"] + row * o["stride"]
                    for a_, b_ in lst:
                        assert lo_ <= a_ and b_ <= lo_ + o["size"], \
                            (f"row {rho} operand {opk} [{a_},{b_}) outside its object row [{lo_},"
                             f"{lo_ + o['size']}) (object {o['kind']} AR [{o['lo']},{o['hi']}) rows "
                             f"{o['rows']}; AR base {r0.desc[opk].base}; copies {sorted(cps_of.get((i, opk), ()))})")
            if rx is not None:
                conf = IR.check_rows_independent(r2, rx2)
                assert conf is None, f"rows not independent: {conf}"
                st["rowx_records"] += 1
            else:
                st["plain_records"] += 1
            blob += b
        except Exception as e:                                       # noqa: BLE001
            ok = False
            import traceback
            tb = traceback.extract_tb(e.__traceback__)[-1]
            errs.append(dict(rec=r0.tag, op=f"{rec.unit}.{rec.op}", kind=kind, err=f"{type(e).__name__}: {e}"[:200],
                             at=f"{Path(tb.filename).name}:{tb.lineno} {tb.line}"[:200],
                             pred=getattr(r0, "pred", None), descs=sorted(r0.desc)))
        st["ok" if ok else "fail"] += 1
    return bytes(blob), dict(st), errs[:20]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", default="mtp", choices=("mtp", "ar"))
    ap.add_argument("--layers", default="0,1")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    from hgi_sim import hbm_plane_model as M
    from hgi_sim import ds_native_timing as DT
    from hgi_sim import timing as T
    st = M.load_stats(PC.STATS)
    PC.CUR["hist"] = PC.lane_hists()
    PC.apply_knobs(PC.Knobs(**PC.HEAD))
    N = 6 if a.mode == "mtp" else 1
    cfg = M.plane_cfg(4 if N > 1 else 1)
    PC.CUR["mode"] = "verify"
    prog, _ = M.ds_compile(N, cfg, st["verify_union"][6]["mean"], "upper", False)
    M.P5._count_slots(prog)
    M.P5._consumers(prog)
    dyn = T.Dyn(DT.POS)
    import engram_groups as EG
    res = dict(schema="opentallas.hbm_next_1019.cmtp.emitter.v1", generated_utc=datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), rule=__doc__, mode=a.mode, N=N, segments={})
    a.out.mkdir(parents=True, exist_ok=True)
    for key, seg, s in SC.schedule_segments(prog, set(a.layers.split(","))):
        fps = EG.footprints(seg, s)
        vals, uf, opmap, seg_end = values(seg, s, fps, dyn)
        objs, comp2obj = build_objects(vals, uf, N)
        li = defaultdict(lambda: [0, 0.0, 0])
        for v in vals:
            if v["kind"] == "livein":
                x = li[(v["anchor"], v["cp"] % (SLOT_OFF // VO))]
                x[0] += v["b"] - v["a"]
                x[1] = max(x[1], v["t1"])
                x[2] += 1
        livein = sorted(([k[0], k[1], w, round(t, 1), n] for k, (w, t, n) in li.items()), key=lambda z: -z[2])
        pl = place(objs)
        c4 = SC.c4_vm_live(seg, s, fps, N)
        blob, est, errs = emit_segment(seg, s, dyn, objs, comp2obj, uf, opmap, N)
        (a.out / f"{a.mode}_L{key}.hgi1r").write_bytes(blob)
        kinds = defaultdict(int)
        for o in objs:
            kinds[o["kind"]] += 1
        r = dict(values=len(vals), objects=dict(kinds), alloc=pl, c4_peak=c4["peak_words"],
                 frag_over_c4=round(pl["high_water"] / max(1, c4["peak_words"]), 3),
                 objects_over_c4=round(pl["object_bound"] / max(1, c4["peak_words"]), 3),
                 fits=dict(as_built=pl["high_water"] <= VW, grown_412k=pl["high_water"] <= VM_GROWN),
                 emit=est, errors=errs, image_bytes=len(blob),
                 livein_words=sum(z[2] for z in livein), livein_top=livein[:16],
                 self_overwritten_read_words=getattr(uf, "selfw_words", {}),
                 c4_self_overwritten=c4.get("self_overwritten_read_words", {}),
                 image_sha256=hashlib.sha256(blob).hexdigest())
        res["segments"][str(key)] = r
        print(a.mode, key, json.dumps(r)[:900], flush=True)
        (a.out / "emitter.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    srcs = ["tools/hbm_next/emitter.py", "tools/hbm_next/isa_rows.py", "tools/hbm_next/plane_compiler.py",
            "tools/hbm_next/static_check.py"]
    res["sources_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in srcs}
    (a.out / "emitter.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
