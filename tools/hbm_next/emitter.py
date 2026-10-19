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
PINNED = list(HPRE)     # pinned row arrays at fixed addresses: h / PRE + (whole token) the carried values
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
    """row-0 (AR) VM intervals per operand -- the SAME extents as timing.footprint: SU b_half halves B / D (adjacent-
    pair tables read at i >> 1; before 10-19 the full n over-read 32 words past the RoPE table = a false layer-20
    live-in)"""
    from hgi_sim import timing as T
    out = {}
    half = rec.unit == "SU" and rec.sut is not None and rec.sut.get("b_half")
    for k, d in rec.desc.items():
        if d.space == "VM":
            if half and k in ("B", "D") and not (0 < d.n_sel < 63):
                d = type(d)(**{**d.__dict__, "n": (d.n + 1) // 2})
            out[k] = [(lo, hi) for sp, lo, hi in T.intervals(d, dyn, L) if sp == "VM"]
    return out


def values(seg, s, fps, dyn, skip=frozenset(), joins=()):
    """VALUE-LEVEL liveness.  Every write of an operand interval in a copy creates a value [a, b) with lifetime
    [writer start, last reader end]; every operand read joins (union-find) the values it reads, so a component is a
    set of values some descriptor reads TOGETHER (their AR-relative layout is kept: one base shift relocates it).
    Live-in reads: union-slot copies j >= 1 read the position's slot-0 copy (compile_verify shifts every footprint of
    a union-slot record, inputs included); HPRE words = the pinned entering columns; words no copy ever writes =
    CONSTANTS (one shared value); other words = data live from cycle 0.
    -> (vals, uf, opmap {(i, opk, cp): value id}, seg_end)"""
    from hgi_sim import timing as T
    ex, start, end = s["ex"], s["start"], s["end"]
    order = [i for i in sorted(range(len(ex)), key=lambda i: start[i]) if i not in skip]
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
            isw = T.is_write_operand(r, opk)
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
    for a_, b_ in PINNED:
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
                    for h0, h1 in PINNED:
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
                    for h0, h1 in PINNED:
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
    ncp = {cp for (_, _, cp) in opmap}
    fam_pitch = []
    for fam, S_ in joins:                   # step 4: the union's e-indexed cells of all slots kappa form ONE component
        for cp in ncp:
            ids = [opmap[(i, opk, cp)] for i, opk in fam if (i, opk, cp) in opmap]
            for x in ids[1:]:
                uf.u(ids[0], x)
            if ids:
                fam_pitch.append((ids[0], S_))
    for v in list(pitch):
        pitch[uf.f(v)] |= pitch.pop(v) if uf.f(v) != v else set()
    for n, v in enumerate(vals):
        v["_root"] = uf.f(n)
    pr = defaultdict(set)
    for v, sset in pitch.items():
        pr[uf.f(v)] |= sset
    for v, S_ in fam_pitch:                 # a joined union family is laid out at its AR slot pitch
        pr[uf.f(v)] = {S_}
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


def carried_values(segs):
    """WHOLE TOKEN cross-segment VM flow from the footprints (AR word offsets; every copy folds onto its AR word):
    per segment, the words read before any in-segment writer (a record's own self-overwritten destination excluded,
    as C4) and the words written.  CARRIED = read-before-write in segment k AND written by an earlier segment (outside
    h / PRE): a value one segment produces and a later one consumes -- it must sit at ONE address in both, so it is
    pinned like h / PRE.  The pinned runs are closed over every footprint interval that touches them (a writer or
    reader is wholly inside or wholly outside).  HOST = read-before-write and written by no segment (preloaded).
    segs: [(key, s, fps)] in programme order -> dict(carried=[(lo, hi)], host=[...], detail)"""
    hp = np.zeros(VW, bool)
    for a_, b_ in HPRE:
        hp[a_:b_] = True
    rbw, wm, ivs_all = {}, {}, []
    for key, s, fps in segs:
        w, rb = np.zeros(VW, bool), np.zeros(VW, bool)
        for i in sorted(range(len(s["ex"])), key=lambda i: s["start"][i]):
            rd, wr = fps[i]
            own = np.zeros(VW, bool)
            wv = [(lo % VO, min(lo % VO + hi - lo, VW)) for sp, lo, hi in wr if sp == "VM" and lo % VO < VW]
            for a_, b_ in wv:
                own[a_:b_] = True
            for sp, lo, hi in rd:
                if sp == "VM" and lo % VO < VW:
                    a_, b_ = lo % VO, min(lo % VO + hi - lo, VW)
                    rb[a_:b_] |= ~w[a_:b_] & ~own[a_:b_]
                    ivs_all.append((a_, b_))
            for a_, b_ in wv:
                w[a_:b_] = True
                ivs_all.append((a_, b_))
        rbw[str(key)], wm[str(key)] = rb & ~hp, w
    keys = [str(k) for k, _, _ in segs]
    car, host, det = np.zeros(VW, bool), np.zeros(VW, bool), []
    before = np.zeros(VW, bool)
    anyw = np.zeros(VW, bool)
    for k in keys:
        anyw |= wm[k]
    for k in keys:
        c = rbw[k] & anyw                           # earlier segment, or a later one / itself (next-token state)
        if c.any():
            det.append(dict(segment=k, words=int(c.sum()), from_earlier=int((c & before).sum())))
        car |= c
        host |= rbw[k] & ~anyw
        before |= wm[k]
    while True:                                     # close the runs over every interval that touches them
        grow = False
        for a_, b_ in ivs_all:
            seg_ = car[a_:b_]
            if seg_.any() and not seg_.all():
                car[a_:b_] = True
                grow = True
        if not grow:
            break

    def runs(m):
        w = np.nonzero(m)[0]
        return [(int(r[0]), int(r[-1]) + 1) for r in np.split(w, np.nonzero(np.diff(w) != 1)[0] + 1)] if w.size else []
    return dict(carried=runs(car), host=runs(host), consumers=det)


def pinned_layout(n_rows):
    """the token-wide pinned map: every PINNED interval as an n_rows row array at a fixed base, in AR order (the same
    in every segment, whether or not the segment touches it) -> ({lo: base}, floor words)"""
    addr, out = 0, {}
    for lo, hi in sorted(PINNED):
        out[lo] = addr
        addr += n_rows * (-(-(hi - lo) // ALIGN) * ALIGN)
    return out, addr


def place(objs, pinmap=None):
    """pinned columns at 0 (in AR order; pinmap = the token-wide fixed layout, whole-token images); the rest by the
    better of first-fit by start time and greedy by size;
    -> dict(pinned_words, high_water, object_bound, method, per-method high water)"""
    addr = 0
    for o in sorted([o for o in objs if o["kind"] == "pinned_column"], key=lambda o: o["lo"]):
        o["base"] = addr if pinmap is None else pinmap[0][o["lo"]]
        addr += _need(o)
    floor = addr if pinmap is None else pinmap[1]
    tries = dict(first_fit_by_time=_first_fit_by_time(objs, floor), greedy_by_size=_greedy_by_size(objs, floor))
    meth = min(tries, key=lambda k: tries[k][0])
    for n, b in tries[meth][1].items():
        objs[n]["base"] = b
    ob, tb = object_bound(objs)
    return dict(pinned_words=floor, high_water=tries[meth][0], object_bound=ob, object_peak_at=tb,
                peak_objects=peak_objects(objs, tb), method=meth, tries={k: v[0] for k, v in tries.items()})


# ======================================================================================================================
# step 4: the expert-union loops (IDX.UNION + rsel CTL.LOOPs), the ATT plan mode (IDX.KVUNION), the users image
# ======================================================================================================================
UNIT_BIT = {u: 1 << i for i, u in enumerate(("CTL", "SM", "SU", "SFU", "FUSED", "ATT", "COLL", "ARGMAX", "DMA", "IDX",
                                              "HC", "SIMT"))}
EXPERTS = 384
TOPK = 6
W_WIN = 128
STORE_ROWS = 512
USER_HSH = 12                       # users: HBM row strides in 4 KiB units (ROWX hsh)
ATT_BUDGET = 128                    # lines a SM the calendar reserves (model upper bound at T 640 x 4 lanes: 109; ATT4
#                                     disjoint balanced 72, aligned 128)


def slot_group(fp):
    """union slot group of a compiled record (compile_verify shifts union slot j's footprints by (j // 6) SLOT_OFF)"""
    g = {lo // SLOT_OFF for side in fp for sp, lo, hi in side if sp == "VM"}
    return max(g) if g else 0


def union_skip(seg, s, fps):
    """records of union slot groups >= 1 (they exist only as the priced model's bookkeeping; the image runs the union
    as rsel loops over the slot-group-0 cells)"""
    out = set()
    for i, (k, L, _) in enumerate(s["ex"]):
        r = seg[k]
        if getattr(r, "mtp_kind", "") in ("expert", "egather") and slot_group(fps[i]) >= 1:
            out.add(i)
    return out


def union_join_families(seg, s, skip):
    """[(i, opk) of slot kappa = 0 .. 6] per e-indexed family (w1 O, w3 O, w2 O, the intermediate gather A / O): the
    rsel loop addresses cell (rho, kappa) as base + (rho K + kappa) S, so the slots of a family must share one object"""
    ex = s["ex"]
    by_tag = {}
    for i, (k, L, _) in enumerate(ex):
        if i in skip:
            continue
        by_tag.setdefault(seg[k].tag or "", i)
    fams = []
    for pat, ops in (("expert slot {} w1", ("O",)), ("expert slot {} w3", ("O",)), ("expert slot {} w2", ("O",)),
                     ("expert_intermediate_gather.s{}", ("A", "O"))):
        for opk in ops:
            fam = [(by_tag[pat.format(k)], opk) for k in range(TOPK + 1) if pat.format(k) in by_tag]
            if len(fam) > 1:
                b0 = seg[ex[fam[0][0]][0]].desc[opk].base
                b1 = seg[ex[fam[1][0]][0]].desc[opk].base
                fams.append((fam, b1 - b0))
    return fams


class Aux:
    """VM words the step-4 records add (union list / count / row tables, KVUNION plans, the users table), placed
    above the allocator's high-water mark, 32-word aligned"""
    def __init__(self, base):
        self.base = self.top = -(-base // 32) * 32
        self.items = {}

    def take(self, name, words):
        a = self.top
        self.items[name] = (a, int(words))
        self.top = -(-(a + words) // 32) * 32
        return a


def _md(d, **kw):
    d2 = copy.copy(d)
    for k, v in kw.items():
        setattr(d2, k, v)
    return d2


def _u32(base, n, m=1, stride=0):
    from hgi_sim import records as RC
    return RC.MDesc(space="VM", fmt="U32", base=int(base), n=int(n), m=int(m), stride=int(stride))


class SegEmit:
    """per-segment emission context: object lookup per (record, operand, copy), the aux region, the users HBM rule"""
    def __init__(self, seg, s, dyn, objs, comp2obj, uf, opmap, n_rows, mode, P, aux, fps, skip):
        self.seg, self.s, self.dyn, self.objs, self.c2o, self.uf, self.opmap = seg, s, dyn, objs, comp2obj, uf, opmap
        self.N, self.mode, self.P, self.aux, self.fps, self.skip = n_rows, mode, P, aux, fps, skip
        self.cps_of = defaultdict(set)
        for (i, opk, cp) in opmap:
            self.cps_of[(i, opk)].add(cp)
        self.idx = {}
        for i, (k, L, _) in enumerate(s["ex"]):
            self.idx.setdefault(k, i)
        self.user_hbm = self._user_hbm() if mode == "mu" else []
        self.notes = defaultdict(int)

    def obj(self, i, opk, cp=0):
        root = self.uf.f(self.opmap[(i, opk, cp)])
        return self.c2o[root]

    def rows(self, i, opk):
        return [self.obj(i, opk, cp) for cp in sorted(self.cps_of.get((i, opk), ()))]

    def cell(self, i, r0, opk, row=0):
        """VM base of operand opk of record i in object row `row` (+ the operand's offset inside its row)"""
        oi, row0 = self.obj(i, opk, 0)
        o = self.objs[oi]
        return o, o["base"] + (row0 + row) * o["stride"] + amap(o, r0.desc[opk].base)

    def _user_hbm(self):
        """users mode: per-user HBM state = every HBM interval some record of the segment writes (window ring, compressed
        rows, list stores) and every HBM read overlapping one; weights / tables stay shared (rs 0)"""
        from hgi_sim import timing as T
        w = []
        for i, (rd, wr) in enumerate(self.fps):
            w += [(lo, hi) for sp, lo, hi in wr if sp == "HBM"]
            r = self.seg[self.s["ex"][i][0]]
            op = getattr(r, "orig_op", f"{r.unit}.{r.op}")
            if op in ("COLL.ROW_GATHER", "DMA.KVWB_DS") or op.startswith("ATT.") or op.startswith("IDX."):
                L = r.layer if isinstance(r.layer, int) else 0
                for k, d in r.desc.items():      # KV state a user owns even where this layer only reads it
                    if d.space == "HBM" and not (op == "COLL.ROW_GATHER" and k == "I"):
                        w += [(lo, hi) for sp, lo, hi in T.intervals(d, self.dyn, L) if sp == "HBM"]
        return sorted(set(w))

    def per_user(self, iv):
        return any(a < iv[2] and iv[1] < b for a, b in self.user_hbm)


def user_stride(segemit_list):
    """smallest power-of-two per-user HBM stride (>= 1 GiB) whose user regions s = 1 .. N-1 collide with no HBM interval
    of the segments (per the footprint model) -> (stride bytes, collisions per candidate)"""
    tried = {}
    for sh in range(30, 37):
        st = 1 << sh
        bad = 0
        for se in segemit_list:
            allh = sorted({(lo, hi) for rd, wr in se.fps for sp, lo, hi in rd + wr if sp == "HBM"})
            usr = [iv for iv in allh if any(a < iv[1] and iv[0] < b for a, b in se.user_hbm)]
            oth = [iv for iv in allh if iv not in set(usr)]
            for u in range(1, se.N):
                for a, b in usr:
                    a2, b2 = a + u * st, b + u * st
                    bad += sum(1 for c, d in oth + usr if c < b2 and a2 < d)
        tried[st] = bad
        if bad == 0:
            return st, tried
    return None, tried


def att_plan_lanes(N, P, users):
    """lane passes of an N-row attention record: [(slot0, lanes)]"""
    return [(p0, min(P, N - p0)) for p0 in range(0, N, P)]


def emit_rec(blob, st, errs, rec, rx, tag, check_rows=None):
    """encode + decode round trip + legality; check_rows(r2, rx2) for row bounds"""
    try:
        b = IR.encode(rec, rx)
        r2, rx2, nxt = IR.decode_one(b, 0)
        assert nxt == len(b) and IR.encode(r2, rx2) == b, "round trip"
        if check_rows:
            check_rows(r2, rx2)
        blob += b
        st["ok"] += 1
        st["rowx_records" if rx is not None else "plain_records"] += 1
        return True
    except Exception as e:                                       # noqa: BLE001
        import traceback
        tb = traceback.extract_tb(e.__traceback__)[-1]
        errs.append(dict(rec=tag, op=f"{rec.unit}.{rec.op}", err=f"{type(e).__name__}: {e}"[:300],
                         at=f"{Path(tb.filename).name}:{tb.lineno}"))
        st["fail"] += 1
        return False


def union_records(se, st, errs, blob, which, ctx):
    """which = 'union' (IDX.UNION) | 'loop1' (w1 / w3 rsel loop) | 'loop2' (w2 rsel loop).  The e-indexed operands
    (expert outputs g / u / d and the gathered intermediate ea) are ROW ARRAYS whose row (position rho) holds the K
    slots kappa at pitch S: cell (rho, kappa) = base + (rho K + kappa) S = base + e S, so the rsel entry's e = rho K +
    kappa (IDX.UNION imm_b = K) addresses it with rs = S under emask; A (x) steps by rho."""
    from hgi_sim import records as RC
    seg, N = se.seg, se.N
    U = ctx["U"]
    if which == "union":
        i = ctx["i_union"]
        r0 = seg[se.s["ex"][i][0]]
        o, a_base = se.cell(i, r0, "O")          # rid row array (the TOPK rows' output), row 0
        rid_stride = o["stride"]
        rec = RC.Rec("IDX", "UNION", wait=r0.wait | UNIT_BIT["IDX"], imm_a=EXPERTS, imm_b=ctx["K"],
                     desc=dict(A=RC.MDesc(space="VM", fmt="U32", base=a_base, n=TOPK, m=N, stride=rid_stride),
                               O=_u32(U["list"], TOPK * N), D=_u32(U["count"], 1),
                               R=_u32(U["tab"], IR.TABLE_ROW_WORDS, TOPK * N, IR.TABLE_ROW_WORDS)))
        ok = emit_rec(blob, st, errs, rec, None, "IDX.UNION")
        ctx["union_rec"] = rec
        return ok
    tmpl = ctx["w13"] if which == "loop1" else ctx["w2"]
    loop = RC.Rec("CTL", "LOOP", param=(1 << 17), imm_a=U["count"], wait=UNIT_BIT["IDX"])
    ok = emit_rec(blob, st, errs, loop, None, f"CTL.LOOP {which}")
    for i in tmpl:
        r0 = seg[se.s["ex"][i][0]]
        rec = copy.copy(r0)
        rec.unit, rec.op = r0.orig_op.split(".")
        rec.desc = {k: copy.copy(d) for k, d in r0.desc.items()}
        rec.param = r0.param & 3
        rec.slot = 0
        rec.wait = (r0.wait | (UNIT_BIT["COLL"] if which == "loop2" else 0)) if i == tmpl[0] else 0
        rs, emask = {}, 0
        eind = ("O",) if which == "loop1" else ("A", "O")
        for opk in rec.desc:
            d = rec.desc[opk]
            if opk == "I":
                rec.desc["I"] = _md(d, base=U["list"], n=1, m=1)
                continue
            if d.space != "VM":
                continue
            o, b = se.cell(i, r0, opk)
            d.base = b
            if opk in eind:
                S = ctx["S"][(i, opk)]
                rs[opk] = S
                emask |= 1 << IR.OPND.index(opk)
            elif o["rows"] > 1:
                rs[opk] = o["stride"]
        rx = IR.RowX(n=N, rsel=1, rtab=U["tab"], emask=emask, rs=rs)
        ok &= emit_rec(blob, st, errs, rec, rx, f"{r0.orig_op} {r0.tag} ({which})", ctx["rsel_check"])
        ctx.setdefault("loop_recs", []).append((rec, rx))
    ok &= emit_rec(blob, st, errs, RC.Rec("CTL", "ENDLOOP"), None, f"CTL.ENDLOOP {which}")
    return ok


def union_setup(se, seg_ex_kind):
    """locate the union templates (slot-group-0, kappa = 0 records), check the e-indexed objects share ONE row pitch
    K (rows of K slots), allocate the aux words, build the rsel row-bound check.  -> ctx or None (no union)"""
    seg, s = se.seg, se.s
    ex = s["ex"]
    iu = [i for i in range(len(ex)) if getattr(seg[ex[i][0]], "mtp_kind", "") == "expert_union"]
    if not iu:
        return None
    N = se.N
    ctx = dict(i_union=iu[0], w13=[], w2=[], S={}, K=None, errs=[])

    def find(tag):
        for i in range(len(ex)):
            r = seg[ex[i][0]]
            if i not in se.skip and getattr(r, "mtp_kind", "") == "expert" and (r.tag or "") == tag:
                return i
        return None
    for tg in ("expert slot 0 w1", "expert slot 0 w3"):
        ctx["w13"].append(find(tg))
    ctx["w2"].append(find("expert slot 0 w2"))
    if None in ctx["w13"] + ctx["w2"]:
        return dict(error="union templates not found")
    Ks = {}
    for which, lst, ops in (("loop1", ctx["w13"], ("O",)), ("loop2", ctx["w2"], ("A", "O"))):
        for i in lst:
            r0 = seg[ex[i][0]]
            i1 = find(r0.tag.replace("slot 0", "slot 1"))
            r1 = seg[ex[i1][0]]
            for opk in ops:
                (oi, row0), (oi1, _) = se.obj(i, opk, 0), se.obj(i1, opk, 0)
                o = se.objs[oi]
                if oi1 != oi:
                    return dict(error=f"{r0.tag} {opk}: slot 0 and slot 1 cells in different objects")
                S = amap(o, r1.desc[opk].base) - amap(o, r0.desc[opk].base)
                if S <= 0 or o["stride"] % S:
                    return dict(error=f"{r0.tag} {opk}: object row {o['stride']} not a multiple of the slot pitch {S}")
                ctx["S"][(i, opk)] = S
                Ks[(r0.tag, opk)] = o["stride"] // S
    if len(set(Ks.values())) != 1:
        return dict(error=f"e-indexed objects disagree on K: {Ks}")
    ctx["K"] = K = Ks.popitem()[1]
    if TOPK * (N - 1) + TOPK > 256 or K * (N - 1) + TOPK - 1 > 255:
        return dict(error=f"e = rho K + kappa exceeds 8 bits (K {K}, N {N})")
    U = dict(list=se.aux.take("union.list", TOPK * N), count=se.aux.take("union.count", 1),
             tab=se.aux.take("union.tables", IR.TABLE_ROW_WORDS * TOPK * N))
    ctx["U"] = U

    def rsel_check(r2, rx2):
        """every row of every loop iteration of a SYNTHETIC union (random ascending top-6 a position, seed 1019)
        writes exactly cell e = rho K + kappa of its position's slot kappa, reads x row rho, and covers every
        (rho, kappa) once over the loop (gate E2: each position's slot kappa holds ITS kappa-th expert)"""
        rng = np.random.default_rng(1019)
        ids = [sorted(rng.choice(EXPERTS, TOPK, replace=False).tolist()) for _ in range(N)]
        uni, tabs = IR.idx_union(ids, EXPERTS, K)
        vm = np.zeros(1 << 19, np.uint32)
        for L, (c, ent) in enumerate(tabs):
            vm[U["tab"] + 32 * L] = c
            for j, (rho, e) in enumerate(ent):
                vm[U["tab"] + 32 * L + 1 + j] = IR.entry_word(rho, e)
        seen = {}
        for L, u in enumerate(uni):
            for bank, rr in IR.expand(r2, rx2, vm, L):
                rho = bank - rx2.slot0
                for opk in IR.OPND:
                    if not (rx2.emask >> IR.OPND.index(opk) & 1):
                        continue
                    S = rx2.rs[opk]
                    e = (rr.desc[opk].base - r2.desc[opk].base) // S
                    assert (rr.desc[opk].base - r2.desc[opk].base) % S == 0
                    kap = e - rho * K
                    assert 0 <= kap < TOPK and ids[rho][kap] == u, f"iteration {L}: row {rho} cell e {e} is not " \
                                                                   f"position {rho}'s slot for expert {u}"
                    seen[(opk, rho, kap)] = seen.get((opk, rho, kap), 0) + 1
                assert IR.check_rows_independent(r2, rx2, vm, L) is None
        for opk in IR.OPND:
            if rx2.emask >> IR.OPND.index(opk) & 1:
                cells = {(rho, kap) for (o_, rho, kap) in seen if o_ == opk}
                assert len(cells) == TOPK * N and all(v == 1 for (o_, _, _), v in seen.items() if o_ == opk), \
                    f"operand {opk}: {len(cells)} of {TOPK * N} cells, multiplicity {set(seen.values())}"
    ctx["rsel_check"] = rsel_check
    last_eg = [i for i in range(len(ex)) if getattr(seg[ex[i][0]], "mtp_kind", "") == "egather" and i not in se.skip]
    ctx["after_last_egather"] = max(last_eg, key=lambda i: s["start"][i]) if last_eg else None
    return ctx


def kvunion_and_att(se, i, r0, blob, st, errs, ctx_att, users):
    """emit the attention record i (orig ATT.QK / PV, N rows) as plan-mode ATT records, one a lane pass, each after
    its IDX.KVUNION (emitted once a layer before the QK record)"""
    from hgi_sim import records as RC
    from hgi_sim import timing as T
    seg, N, P = se.seg, se.N, se.P
    passes = att_plan_lanes(N, P, users)
    if not ctx_att.get("plans"):
        sel_i = ctx_att.get("sel_i")
        ctx_att["plans"] = []
        for p0, nl in passes:
            R = se.aux.take(f"kvunion.plan.p{p0}", IR.NSM_ATT * IR.PLAN_WORDS)
            D = se.aux.take(f"kvunion.map.p{p0}", IR.DMAP + IR.RUN_MAX * nl)
            desc = dict(R=_u32(R, IR.PLAN_WORDS, IR.NSM_ATT, IR.PLAN_WORDS), D=_u32(D, IR.DMAP + IR.RUN_MAX * nl))
            if sel_i is not None:
                rs_ = seg[se.s["ex"][sel_i][0]]
                o, b = se.cell(sel_i, rs_, "O", row=p0)
                desc["A"] = RC.MDesc(space="VM", fmt="U32", base=b, n=rs_.desc["O"].n, m=nl, stride=o["stride"])
            param = (nl - 1) | (p0 << 4) | (int(users) << 8) | (ATT_BUDGET << 16)
            rec = RC.Rec("IDX", "KVUNION", param=param, imm_a=W_WIN, imm_b=STORE_ROWS,
                         wait=UNIT_BIT["COLL"] if sel_i is not None else 0, desc=desc)
            emit_rec(blob, st, errs, rec, None, f"IDX.KVUNION pass {p0}")
            ctx_att["plans"].append((p0, nl, R))
    for p0, nl, R in ctx_att["plans"]:
        rec = copy.copy(r0)
        rec.unit, rec.op = r0.orig_op.split(".")
        rec.desc = {k: copy.copy(d) for k, d in r0.desc.items()}
        rec.slot = p0 & 7
        rs = {}
        hsh = 0
        for opk, d in rec.desc.items():
            if d.space == "VM" and se.cps_of.get((i, opk)):
                o, b = se.cell(i, r0, opk, row=p0)
                d.base = b
                if o["rows"] > 1:
                    rs[opk] = o["stride"]
            elif d.space == "HBM" and users and any(se.per_user(iv) for iv in
                                                    T.intervals(d, se.dyn, r0.layer if isinstance(r0.layer, int) else 0)):
                rs[opk] = se.ustride >> USER_HSH
                d.base = d.base + p0 * se.ustride
                hsh = USER_HSH
        rx = IR.RowX(n=nl, slot0=p0, rsel=1, rtab=R, rs=rs, hsh=hsh)
        emit_rec(blob, st, errs, rec, rx, f"{r0.orig_op} plan pass {p0}")
        se.notes["att_plan_records"] += 1


def emit_segment(seg, s, dyn, objs, comp2obj, uf, opmap, n_rows, se=None):
    """relocate + ROWX-encode every record; with se (step 4): the union loops, the ATT plan mode, users HBM strides.
    -> (bytes, stats, errors)"""
    ex, start = s["ex"], s["start"]
    st = defaultdict(int)
    errs = []
    blob = bytearray()
    SPC = SLOT_OFF // VO
    cps_of = defaultdict(set)
    for (i, opk, cp) in opmap:
        cps_of[(i, opk)].add(cp)
    uctx = union_setup(se, None) if se is not None and n_rows > 1 else None
    if uctx and uctx.get("error"):
        errs.append(dict(rec="union", err=uctx["error"]))
        st["fail"] += 1
        uctx = None
    users = se is not None and se.mode == "mu"
    actx = {}
    if se is not None and n_rows > 1:
        sel = [i for i in range(len(ex)) if getattr(seg[ex[i][0]], "orig_op", "") == "COLL.TOPK_MERGE"
               and "index merge" in (seg[ex[i][0]].tag or "") and getattr(seg[ex[i][0]], "npos", 1) > 1]
        actx["sel_i"] = sel[0] if sel else None
    loop1 = False
    for i in sorted(range(len(ex)), key=lambda i: start[i]):
        k, L, _ = ex[i]
        r0 = seg[k]
        if r0.unit == "CTL" and r0.op == "END":
            continue
        kind = getattr(r0, "mtp_kind", "")
        if se is not None and i in se.skip:
            st["union_slot_group_copies_folded"] += 1
            continue
        if kind in ("expert", "egather", "expert_union") and uctx is None and n_rows > 1:
            st["skipped_union_" + kind] += 1        # no union context (AR: not reached; error: reported)
            continue
        if kind == "expert_union" and uctx is not None:
            union_records(se, st, errs, blob, "union", uctx)
            continue
        if kind == "expert" and uctx is not None:
            if (r0.tag or "").endswith(("w1", "w3")) and not loop1:
                union_records(se, st, errs, blob, "loop1", uctx)
                loop1 = True
            st["union_expert_in_loop"] += 1
            continue
        if se is not None and n_rows > 1 and kind.startswith("att_B") and kind.endswith("_rows"):
            kvunion_and_att(se, i, r0, blob, st, errs, actx, users)
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
            hsh = 0
            if users:
                from hgi_sim import timing as T
                for opk, d in rec.desc.items():
                    if d.space == "HBM" and any(se.per_user(iv) for iv in T.intervals(d, dyn, L)):
                        rs[opk] = se.ustride >> USER_HSH
                        hsh = USER_HSH
                        st["users_hbm_strided_operands"] += 1
                if rec.unit == "IDX" and rec.op == "INDEX":      # R11: the implicit key store steps by rs_I << hsh
                    rs["I"] = se.ustride >> USER_HSH
                    hsh = USER_HSH
                    st["users_idx_key_store_strides"] += 1
            rx = IR.RowX(n=npos, slot0=0, rpl=rpl, rs=rs, hsh=hsh)
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
        if uctx is not None and i == uctx.get("after_last_egather"):
            union_records(se, st, errs, blob, "loop2", uctx)
    if se is not None:
        st.update({f"note_{k}": v for k, v in se.notes.items()})
        if uctx is not None:
            st["union_K"] = uctx["K"]
    return bytes(blob), dict(st), errs[:20]


def _all_wait():
    from hgi_sim import records as RC
    return (1 << len(RC.UNITS)) - 1


def _merge_rows_ok(r2, rx2):
    IR.check(r2, rx2)
    if rx2 is not None:
        conf = IR.check_rows_independent(r2, rx2)
        assert conf is None, f"ARGMAX_MERGE rows not independent: {conf}"
        rows = [x.desc["O"].base for _, x in IR.expand(r2, rx2)]
        assert rows == [rows[0] + i for i in range(rx2.n)], f"tokx ids not contiguous: {rows}"


def head_tail(blob, se, N, mode):
    """step 5 head tail of a whole-token image (R9).  The head segment ends with COLL.ARGMAX_MERGE (N rows, one id a
    row).  Its O is re-pointed to the aux TOKX table: tokx[0] = k, tokx[1 + rho] = row rho's winning id (rs_O = 1, so
    the ids are contiguous: TOKX A = U32 [1 + N]).  Then:
      MTP:   CTL.ACCEPT (A = accept.a, U32 [1]) -> CTL.TOKX (param 0, A = tokx, k = a + 1 beats) -> CTL.END.
             a and tokx[0] = a + 1 are written by the DSpark accept compare (d4g ot_dshbm_dspark_ctl accept_a0, the
             CP-side control block: verify ids tokx[1..5] against the drafted ids; priced in mh_ctl) -- NOT a record.
      users: CTL.TOKX (param 1, A = tokx, tokx[0] = N: an image constant the host writes with the image) -> CTL.END.
    Every tail record drains every unit first (wait = all).  -> (bytes, stats, errors)"""
    from hgi_sim import records as RC
    st, errs, out = defaultdict(int), [], bytearray()
    tok = se.aux.take("tokx", 1 + N)
    acc = se.aux.take("accept.a", 1) if mode == "mtp" else None
    off, recs = 0, []
    while off < len(blob):
        r, rx, nxt = IR.decode_one(blob, off)
        recs.append((r, rx))
        off = nxt
    hit = 0
    for r, rx in recs:
        if r.unit == "COLL" and r.op == "ARGMAX_MERGE":
            r = copy.copy(r)
            r.desc = dict(r.desc)
            r.desc["O"] = _md(r.desc["O"], base=tok + 1, n=1, m=1, stride=0)
            if rx is not None:
                rx = copy.deepcopy(rx)
                rx.rs = dict(rx.rs, O=1)
            hit += 1
            emit_rec(out, st, errs, r, rx, "head ARGMAX_MERGE -> tokx", check_rows=_merge_rows_ok)
        else:
            emit_rec(out, st, errs, r, rx, f"head {r.unit}.{r.op}")
    if hit != 1:
        errs.append(dict(rec="head", err=f"expected one COLL.ARGMAX_MERGE in the head, found {hit}"))
        st["fail"] += 1
    W = _all_wait()
    if mode == "mtp":
        emit_rec(out, st, errs, RC.Rec("CTL", "ACCEPT", wait=W, desc=dict(A=_u32(acc, 1))), None, "CTL.ACCEPT")
        emit_rec(out, st, errs, RC.Rec("CTL", "TOKX", wait=W, param=0, desc=dict(A=_u32(tok, 1 + N))), None,
                 "CTL.TOKX mtp")
    else:                                 # users: one beat a user; AR: an MTP-mode commit of k = 1 (tokx[0] = 1)
        emit_rec(out, st, errs, RC.Rec("CTL", "TOKX", wait=W, param=1 if mode == "mu" else 0,
                                       desc=dict(A=_u32(tok, 1 + N))), None, f"CTL.TOKX {mode}")
    emit_rec(out, st, errs, RC.Rec("CTL", "END", wait=W), None, "CTL.END")
    st["tokx_base"], st["accept_base"] = tok, acc
    return bytes(out), dict(st), errs


def assemble_token(out_dir, mode, N, segblobs, prologue, res):
    """one whole-token image: [users prologue] + every segment in programme order (layers ascending, head last; the
    head carries the tail).  Checked: the whole image decodes record by record (round trip), exactly one END (last),
    the record count = the per-segment sums, every aux table below 2^19 words."""
    order = sorted([k for k, _ in segblobs if k != "head"], key=int) + ["head"]
    by = dict(segblobs)
    img, table = bytearray(prologue), []
    if prologue:
        table.append(dict(segment="users_prologue", offset=0, bytes=len(prologue)))
    for k in order:
        b = by[k]
        table.append(dict(segment=str(k), offset=len(img), bytes=len(b), sha256=hashlib.sha256(b).hexdigest()))
        img += b
    off, nrec, ends, ops = 0, 0, [], defaultdict(int)
    while off < len(img):
        r, rx, nxt = IR.decode_one(bytes(img), off)
        assert IR.encode(r, rx) == bytes(img[off:nxt]), f"whole-image round trip at {off}"
        if r.unit == "CTL" and r.op == "END":
            ends.append(nrec)
        if r.unit == "CTL":
            ops[r.op] += 1
        off, nrec = nxt, nrec + 1
    need = max(int(s.get("vm_need_words", 0)) for s in res["segments"].values())
    name = f"{mode}_N{N}_token.hgi1r"
    (out_dir / name).write_bytes(bytes(img))
    liveins = {k: dict(words=s["livein_words"], top=s["livein_top"][:4]) for k, s in res["segments"].items()
               if s.get("livein_words")}
    pins = defaultdict(set)                 # every pinned interval at ONE base in every segment that touches it
    for s in res["segments"].values():
        for lo, b in s["alloc"].get("pinned_bases", {}).items():
            pins[lo].add(b)
    pin_ok = all(len(v) == 1 for v in pins.values())
    car = res.get("carried", {})
    host = car.get("host", [])
    return dict(image=name, bytes=len(img), records=nrec, sha256=hashlib.sha256(bytes(img)).hexdigest(),
                liveins=liveins, pinned_bases={k: sorted(v) for k, v in pins.items()}, pinned_one_base=pin_ok,
                host_preloaded=host,
                one_vm_map=(not liveins) and pin_ok and not host,
                end_at=ends, end_ok=(ends == [nrec - 1]), ctl_ops=dict(ops), segments=table,
                vm_need_words=need, fits_2p19=need <= 1 << 19,
                errors=sum(len(s.get("errors", ())) for s in res["segments"].values()))


def users_prologue(N, aux_base):
    """the users image prologue: CTL.USERS (ROWX n = N, slot0 0) reading the host-written {token_s, pos_s} table"""
    from hgi_sim import records as RC
    rec = RC.Rec("CTL", "USERS", desc=dict(A=_u32(aux_base, 2 * N)))
    rx = IR.RowX(n=N, slot0=0)
    st, errs, blob = defaultdict(int), [], bytearray()
    emit_rec(blob, st, errs, rec, rx, "CTL.USERS")
    return bytes(blob), dict(st), errs


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", default="mtp", choices=("mtp", "ar", "mu"))
    ap.add_argument("--layers", default="0,1")
    ap.add_argument("--P", type=int, default=4)
    ap.add_argument("--legacy", action="store_true", help="step-3 behaviour (union records skipped, no ATT plan)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--N", type=int, default=0, help="rows (mu: users 1..4; default mtp 6 / mu 4 / ar 1)")
    ap.add_argument("--whole", action="store_true",
                    help="step 5: every segment + the head, ONE VM map (common aux base = the largest high-water mark), "
                         "assembled into one whole-token image with the head tail (TOKX / ACCEPT / END)")
    a = ap.parse_args()
    from hgi_sim import hbm_plane_model as M
    from hgi_sim import ds_native_timing as DT
    from hgi_sim import timing as T
    st = M.load_stats(PC.STATS)
    PC.CUR["hist"] = PC.lane_hists()
    PC.apply_knobs(PC.Knobs(**dict(PC.HEAD, P=a.P)))
    IR.P_LANES = a.P
    N = a.N or {"mtp": 6, "ar": 1, "mu": 4}[a.mode]
    assert a.mode != "mtp" or N == 6, "MTP verify is N = 6"
    assert a.mode != "ar" or N == 1
    cfg = M.plane_cfg(a.P if N > 1 else 1)
    users = a.mode == "mu"
    PC.CUR["mode"] = "users" if users else "verify"
    if users:
        union = PC.users_union(st["users_union"], N) if N > 1 else 6.0
    else:
        union = st["verify_union"][6]["mean"]
    prog, _ = M.ds_compile(N, cfg, union, "upper", users)
    M.P5._count_slots(prog)
    M.P5._consumers(prog)
    dyn = T.Dyn(DT.POS)
    import engram_groups as EG
    res = dict(schema="opentallas.hbm_next_1019.cmtp.emitter.v2", generated_utc=datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), rule=__doc__, mode=a.mode, N=N, P=a.P,
        isa_version=IR.VERSION, segments={})
    a.out.mkdir(parents=True, exist_ok=True)
    work, pre = [], [(key, seg, s, EG.footprints(seg, s))
                     for key, seg, s in SC.schedule_segments(prog, None if a.whole else set(a.layers.split(",")))]
    pinmap = None
    if a.whole and not a.legacy:            # carried values -> pinned (one address for producer and consumers)
        cv = carried_values([(k, s, f) for k, _, s, f in pre])
        PINNED[:] = list(HPRE) + cv["carried"]
        pinmap = pinned_layout(N)
        res["carried"] = dict(cv, pinned=[[lo, hi, pinmap[0][lo]] for lo, hi in sorted(PINNED)],
                              pinned_words=pinmap[1],
                                    rule="AR intervals read before any in-segment writer and written by some segment "
                                   "(outside h / PRE): pinned N-row arrays at one token-wide base, like h / PRE")
        print("carried", json.dumps(res["carried"])[:800], flush=True)
    for key, seg, s, fps in pre:
        skip = frozenset() if (a.legacy or N == 1) else frozenset(union_skip(seg, s, fps))
        joins = () if (a.legacy or N == 1) else union_join_families(seg, s, skip)
        vals, uf, opmap, seg_end = values(seg, s, fps, dyn, skip, joins)
        objs, comp2obj = build_objects(vals, uf, N)
        pl = place(objs, pinmap)
        pl["pinned_bases"] = {str(o["lo"]): o["base"] for o in objs if o["kind"] == "pinned_column"}
        se = None
        if not a.legacy:
            se = SegEmit(seg, s, dyn, objs, comp2obj, uf, opmap, N, a.mode, a.P, Aux(pl["high_water"]), fps, skip)
        work.append((key, seg, s, fps, vals, uf, opmap, objs, comp2obj, pl, se))
    gh = None
    if a.whole and not a.legacy:            # one VM map: pinned columns at 0, every segment's aux at the same base
        gh = max(w[9]["high_water"] for w in work)
        for w in work:
            w[-1].aux = Aux(gh)
        res["vm_map"] = dict(aux_base=-(-gh // 32) * 32, largest_high_water=gh,
                             note="pinned columns h / PRE + the carried values (res.carried) at one token-wide base, "
                                  "every segment's aux at aux_base; token.one_vm_map requires no live-ins, one base "
                                  "per pinned interval, no host-preloaded words")
    if users and not a.legacy:
        ustride, tried = user_stride([w[-1] for w in work])
        res["users_hbm"] = dict(hsh=USER_HSH, stride_bytes=ustride, collisions_by_stride={str(k): v for k, v in
                                                                                         tried.items()})
        for w in work:
            w[-1].ustride = ustride or (1 << 36)
        pb, pst, perr = users_prologue(N, (-(-gh // 32) * 32) if gh is not None else 0)
        (a.out / "mu_prologue.hgi1r").write_bytes(pb)
        res["users_prologue"] = dict(stats=pst, errors=perr, sha256=hashlib.sha256(pb).hexdigest(),
                                     note="A = the host-written {token_s, pos_s} table at the image's users.table aux "
                                          "address (the per-segment aux map below); relocated by the whole-token "
                                          "assembler")
    segblobs = []
    for key, seg, s, fps, vals, uf, opmap, objs, comp2obj, pl, se in work:
        li = defaultdict(lambda: [0, 0.0, 0])
        for v in vals:
            if v["kind"] == "livein":
                x = li[(v["anchor"], v["cp"] % (SLOT_OFF // VO))]
                x[0] += v["b"] - v["a"]
                x[1] = max(x[1], v["t1"])
                x[2] += 1
        livein = sorted(([k[0], k[1], w, round(t, 1), n] for k, (w, t, n) in li.items()), key=lambda z: -z[2])
        c4 = SC.c4_vm_live(seg, s, fps, N)
        if se is not None and users:
            se.aux.take("users.table", 2 * N)
        blob, est, errs = emit_segment(seg, s, dyn, objs, comp2obj, uf, opmap, N, se)
        if a.whole and key == "head" and se is not None:
            blob, tst, terr = head_tail(blob, se, N, a.mode)
            est = dict(est, tail=tst)
            errs = errs + terr
        segblobs.append((key, blob))
        if not a.whole:
            (a.out / f"{a.mode}_L{key}.hgi1r").write_bytes(blob)
        kinds = defaultdict(int)
        for o in objs:
            kinds[o["kind"]] += 1
        need = se.aux.top if se is not None else pl["high_water"]
        r = dict(values=len(vals), objects=dict(kinds), alloc=pl, c4_peak=c4["peak_words"],
                 frag_over_c4=round(pl["high_water"] / max(1, c4["peak_words"]), 3),
                 objects_over_c4=round(pl["object_bound"] / max(1, c4["peak_words"]), 3),
                 aux=dict(se.aux.items) if se is not None else {}, vm_need_words=need,
                 fits=dict(as_built=need <= VW, grown_412k=need <= VM_GROWN, vm_2p19=need <= 1 << 19),
                 emit=est, errors=errs, image_bytes=len(blob),
                 livein_words=sum(z[2] for z in livein), livein_top=livein[:16],
                 self_overwritten_read_words=getattr(uf, "selfw_words", {}),
                 c4_self_overwritten=c4.get("self_overwritten_read_words", {}),
                 image_sha256=hashlib.sha256(blob).hexdigest())
        res["segments"][str(key)] = r
        print(a.mode, key, json.dumps(dict(emit=est, errors=errs[:3], need=need, hw=pl["high_water"]))[:1500],
              flush=True)
        (a.out / "emitter.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    if a.whole:
        res["token"] = assemble_token(a.out, a.mode, N, segblobs, (a.out / "mu_prologue.hgi1r").read_bytes()
                                      if users and not a.legacy else b"", res)
        print("token", json.dumps(res["token"])[:1500], flush=True)
    srcs = ["tools/hbm_next/emitter.py", "tools/hbm_next/isa_rows.py", "tools/hbm_next/plane_compiler.py",
            "tools/hbm_next/static_check.py"]
    res["sources_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in srcs}
    (a.out / "emitter.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
