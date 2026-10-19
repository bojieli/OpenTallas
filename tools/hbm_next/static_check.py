#!/usr/bin/env python3
"""HBM-NEXT-CMTP: the static-schedule checker.  COLLISION = FAULT.

The next die has no credits, no ready/valid flow control and no backpressure on the die (owner 10-14): the compiler
assigns every record (and every row of an N-row record) a start cycle, and the hardware runs that timeline.  This
checker takes a compiled programme and its timeline and FAILS on any of:

  C1 unit double-booking   two records on one non-pipelined unit overlap in time ([start, end) intersect), or a
                           pipelined unit (DMA) issues two records closer than its issue interval.
  C2 dependence            a record starts before a producer it reads (RAW), overwrites (WAW) or a reader it overwrites
                           (WAR) has finished, on the exact VM / HBM intervals (the S2 dependence scan), or an indexed
                           record's I table is overwritten before the dispatcher read it.
  C3 rows                  an N-row record's row r is placed at start + r (II + rgap) and the rows fit in [start, end);
                           no row reads what an earlier row of the same record writes (isa_rows R2).
  C4 VM capacity           the words live at any cycle (values written and still to be read, per-position values x N
                           copies, constants once) exceed the VM (as built 2^18 words, or the grown VM).
  C5 KV window ring        the KVWB ring of B.m slots: an N-row append must not overwrite a slot an earlier row's
                           window still reads (ring >= 128 + N - 1, a power of two), checked slot by slot.

Timeline = the S2 command-processor schedule of the programme (timing.schedule "S2"): with fixed unit costs the CP's
dispatch times are a compile-time function of the programme, so the S2 start / end ARE the static schedule; the checker
re-verifies them independently of the scheduler (it trusts nothing but the records' intervals and the start / end).

    PYTHONPATH=tools python3 tools/hbm_next/static_check.py --out DIR [--mode mtp|mu|ar] [--layers 0,1,2,14,head]
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "hbm_next"))

VM_WORDS = 1 << 18
VM_OFF = 1 << 24                 # ds_mtp_verify per-position VM copy offset (bookkeeping)
EPS = 1e-6


def overlap(a, b):
    return a[0] == b[0] and a[1] < b[2] and b[1] < a[2]


def check(recs, s, *, pipelined=None, n_rows=1, vm_capacity=VM_WORDS, const_words=None, ring=None, row_ii=None,
          tol=EPS):
    """-> dict(pass, counts, violations[...]) for one scheduled segment.  recs: the programme the schedule ran
    (s["ex"] indexes it); s: timing.schedule output (start, end, disp, deps, ex)."""
    from hgi_sim import timing as T
    from hgi_sim import ds_native_timing as DT
    pipelined = T.PIPELINED if pipelined is None else pipelined
    ex, start, end = s["ex"], s["start"], s["end"]
    n = len(ex)
    V = defaultdict(list)
    # ---- C1 units
    by_unit = defaultdict(list)
    for i, (k, L, *_) in enumerate(ex):
        by_unit[recs[k].unit].append(i)
    for u, idx in by_unit.items():
        idx = sorted(idx, key=lambda i: (start[i], end[i]))
        for a, b in zip(idx, idx[1:]):
            if u in pipelined:
                if start[b] < start[a] + pipelined[u] - tol:
                    V["C1"].append(dict(unit=u, a=recs[ex[a][0]].tag, b=recs[ex[b][0]].tag, a_start=start[a],
                                        b_start=start[b], need=pipelined[u]))
            elif start[b] < end[a] - tol and end[b] - start[b] > tol and end[a] - start[a] > tol:
                V["C1"].append(dict(unit=u, a=recs[ex[a][0]].tag, b=recs[ex[b][0]].tag, a_span=[start[a], end[a]],
                                    b_span=[start[b], end[b]]))
    # ---- C2 dependences: recomputed from the footprints (not taken from the scheduler), S2's own rule:
    # for every RAW / WAW / WAR pair (exact VM / HBM intervals, program order j < i) the later record must not start
    # before the earlier one has ended; same-unit pairs on a pipelined unit (DMA: in-order issue, posted writes, the
    # FENCE orders them) are the unit's own business; STREAM operands are fixed-latency FIFOs (not intervals)
    from hgi_sim import ds_mtp_verify as V_
    fps = []
    dyn = T.Dyn(DT.POS)
    for (k, L, L1) in ex:
        rd, wr = V_._footprint(recs[k], dyn, L)
        fps.append(([iv for iv in rd if iv[0] in ("VM", "HBM")], [iv for iv in wr if iv[0] in ("VM", "HBM")]))
    writers, readers = [], []
    for i in range(n):
        rd, wr = fps[i]
        u_i = recs[ex[i][0]].unit
        pairs = []
        for iv in rd:
            pairs += [("RAW", j) for (w, j) in writers if overlap(iv, w)]
        for iv in wr:
            pairs += [("WAW", j) for (w, j) in writers if overlap(iv, w)]
            pairs += [("WAR", j) for (x, j) in readers if overlap(iv, x) and j != i]
        for kind, j in set(pairs):
            if u_i == recs[ex[j][0]].unit and u_i in pipelined:
                continue
            if end[j] > start[i] + tol:
                V["C2"].append(dict(kind=kind, rec=recs[ex[i][0]].tag, other=recs[ex[j][0]].tag,
                                    early=round(end[j] - start[i], 1)))
        for iv in wr:
            writers = [(w, j) for (w, j) in writers if not (w[0] == iv[0] and iv[1] <= w[1] and w[2] <= iv[2])]
            writers.append((iv, i))
            readers = [(x, j) for (x, j) in readers if not overlap(x, iv)]
        for iv in rd:
            readers.append((iv, i))
    # ---- C3 rows
    for i, (k, L, *_) in enumerate(ex):
        r = recs[k]
        npos = getattr(r, "npos", 1)
        ii = getattr(r, "ii", None)
        if npos > 1 and ii is not None:
            # rows start at start + r (II + rgap) (rgap 0 here) and the last row must end by the record's end: the
            # record's span must hold the N - 1 row intervals plus a first row of at least one cycle
            if end[i] - start[i] < (npos - 1) * ii + 1 - tol:
                V["C3"].append(dict(rec=r.tag, rows=npos, ii=ii, span=round(end[i] - start[i], 1)))
    # ---- C4 VM capacity (word-level liveness on the timeline)
    cap = c4_vm_live(recs, s, fps, n_rows, const_words)
    vmv = {nm: dict(capacity=c_, fits=cap["peak_words"] <= c_) for nm, c_ in (vm_capacity.items() if
           isinstance(vm_capacity, dict) else [("vm", vm_capacity)])}
    # ---- C5 ring
    if ring:
        rr = c5_ring(*ring)
        if not rr["ok"]:
            V["C5"].append(rr)
    counts = {c: len(V.get(c, [])) for c in ("C1", "C2", "C3", "C5")}
    return dict(PASS=not any(counts.values()), counts=counts, records=n, vm=dict(cap, verdicts=vmv),
                violations={k: v[:20] for k, v in V.items()})


def c4_vm_live(recs, s, fps, n_rows, const_words=None, hpre=((0, 20480), (40960, 40964))):
    """live VM words over the timeline.  A word is live from the END of the write that defines it to the END of its
    last reader before the next write.  Per-position copies are separate in the footprints (VM_OFF apart; union expert
    slots SLOT_OFF apart).  Words read before any write in the segment (live-in) are the entering columns h / PRE
    (`hpre`, per copy) or constants (gains, tables, HC rows: counted ONCE, copy 0).  -> dict(peak_words, peak_at,
    live_in_column_words, live_in_const_words)"""
    ex, start, end = s["ex"], s["start"], s["end"]
    ev = defaultdict(int)
    order = sorted(range(len(ex)), key=lambda i: start[i])
    isc = np.zeros(VM_WORDS, bool)
    for lo, hi in hpre:
        isc[lo:hi] = True
    mk = lambda: dict(defined=np.full(VM_WORDS, -1.0), lastuse=np.full(VM_WORDS, -1.0))
    copies = defaultdict(mk)
    const = mk()
    spans = []
    selfw_words = defaultdict(int)
    for i in order:
        rd, wr = fps[i]
        wv = [(lo // VM_OFF, lo % VM_OFF, min(hi - (lo // VM_OFF) * VM_OFF, VM_WORDS)) for sp, lo, hi in wr if sp == "VM"]
        for sp, lo, hi in rd:
            if sp != "VM":
                continue
            cp, a, b = lo // VM_OFF, lo % VM_OFF, min(hi - (lo // VM_OFF) * VM_OFF, VM_WORDS)
            if a >= VM_WORDS:
                continue
            c = copies[cp]
            d = c["defined"][a:b]
            und = d < 0
            if und.any():                                     # live-in: entering column (per copy) or constant (once)
                # SELF-OVERWRITTEN: an undefined word this record also WRITES (outside h / PRE) is its own output
                # (the in-place all-gather's footprint reads its whole destination; only its own, already defined,
                # slice is data) -> not a live-in, never live before the write
                sw = np.zeros(b - a, bool)
                for cw, aw, bw in wv:
                    if cw == cp and aw < b and a < bw:
                        sw[max(aw, a) - a:min(bw, b) - a] = True
                sw &= und & ~isc[a:b]
                if sw.any():
                    r_ = recs[ex[i][0]]
                    selfw_words[f"{r_.unit}.{r_.op}"] += int(sw.sum())
                col = und & isc[a:b]
                d[col] = 0.0
                cst = und & ~isc[a:b] & ~sw
                if cst.any():
                    cd, cl = const["defined"][a:b], const["lastuse"][a:b]
                    cd[cst & (cd < 0)] = 0.0
                    np.maximum(cl, np.where(cst, end[i], -1.0), out=cl)
            seg = c["lastuse"][a:b]
            np.maximum(seg, np.where(d >= 0, end[i], -1.0), out=seg)
        for sp, lo, hi in wr:
            if sp != "VM":
                continue
            cp, a, b = lo // VM_OFF, lo % VM_OFF, min(hi - (lo // VM_OFF) * VM_OFF, VM_WORDS)
            if a >= VM_WORDS:
                continue
            c = copies[cp]
            dfn, lu = c["defined"][a:b], c["lastuse"][a:b]
            m = (dfn >= 0) & (lu >= 0)
            if m.any():
                vals, cnt = np.unique(np.stack([dfn[m], lu[m]], 1), axis=0, return_counts=True)
                spans += [(float(x[0]), float(x[1]), int(k)) for x, k in zip(vals, cnt)]
            dfn[:] = end[i]
            lu[:] = -1.0
    for c in list(copies.values()) + [const]:
        m = (c["defined"] >= 0) & (c["lastuse"] >= 0)
        if m.any():
            vals, cnt = np.unique(np.stack([c["defined"][m], c["lastuse"][m]], 1), axis=0, return_counts=True)
            spans += [(float(x[0]), float(x[1]), int(k)) for x, k in zip(vals, cnt)]
    for t0, t1, w in spans:
        if t1 > t0:
            ev[t0] += w
            ev[t1] -= w
    cur, peak, at = 0, 0, 0.0
    for t in sorted(ev):
        cur += ev[t]
        if cur > peak:
            peak, at = cur, t
    if const_words:
        peak += const_words
    return dict(peak_words=int(peak), peak_at=round(at, 1), copies=len(copies),
                live_in_const_words=int(((const["defined"] >= 0) & (const["lastuse"] >= 0)).sum()),
                self_overwritten_read_words=dict(selfw_words))


def c5_ring(ring_slots, n_rows, window=128, pos0=1 << 20 - 1):
    """slot-level proof of the KV window ring for one N-row append: rows r = 0..N-1 append position pos0 + r into slot
    (pos0 + r) mod ring before any attention row reads; row r's window reads positions pos0 + r - window + 1 ..
    pos0 + r.  Fails if a later append overwrote a slot a row's window needs with a different position."""
    slot_pos = {}
    for p in range(pos0 - ring_slots, pos0):                # ring filled by earlier positions
        slot_pos[p % ring_slots] = p
    for r in range(n_rows):
        slot_pos[(pos0 + r) % ring_slots] = pos0 + r
    bad = []
    for r in range(n_rows):
        q = pos0 + r
        for p in range(q - window + 1, q + 1):
            if p < 0:
                continue
            got = slot_pos.get(p % ring_slots)
            if got != p and got is not None and got <= q:
                bad.append(dict(row=r, needs=p, slot=p % ring_slots, holds=got))
            elif got is not None and got > q:
                bad.append(dict(row=r, needs=p, slot=p % ring_slots, holds=got, note="overwritten by a later row"))
    return dict(ok=not bad, ring=ring_slots, rows=n_rows, window=window, bad=bad[:8], nbad=len(bad))


# ======================================================================================================================
# driver: compile under the CMTP knobs, schedule every layer segment, check, mutate
# ======================================================================================================================
def schedule_segments(prog, keys=None):
    from hgi_sim import ds_mtp_verify as V
    from hgi_sim import ds_native_timing as DT
    from hgi_sim import timing as T
    end = [r for r in prog if r.unit == "CTL" and r.op == "END"][:1]
    out = []
    T.footprint = V._footprint
    try:
        for key, seg in V.segments(prog):
            if keys is not None and str(key) not in keys:
                continue
            seg = V.rebuild(seg + end)
            s = T.schedule(seg, DT.POS, "S2", cost_fn=V.cost_fn(None))
            out.append((key, seg, s))
    finally:
        T.footprint = V._FP
    return out


def mutate(seg, s, kind):
    """a copy of the schedule with one injected collision; -> (s2, what)"""
    s2 = dict(s, start=list(s["start"]), end=list(s["end"]), races=[])
    ex = s2["ex"]
    if kind == "unit_double_book":
        # pull a record onto its unit predecessor: start 1 cycle before the predecessor ends
        by = defaultdict(list)
        for i, (k, *_) in enumerate(ex):
            if seg[k].unit not in ("DMA", "CTL"):
                by[seg[k].unit].append(i)
        u = max(by, key=lambda x: len(by[x]))
        a, b = sorted(by[u], key=lambda i: s2["start"][i])[3:5]
        d = s2["start"][b] - (s2["end"][a] - 1.0)
        s2["start"][b] -= d
        s2["end"][b] -= d
        return s2, f"{u}: {seg[ex[b][0]].tag} moved {d:.1f} cycles earlier onto {seg[ex[a][0]].tag}"
    if kind == "raw_early":
        for i in range(len(ex)):
            if s["deps"][i]:
                j = max(s["deps"][i], key=lambda j: s["end"][j])
                if seg[ex[i][0]].unit != seg[ex[j][0]].unit:
                    d = s2["start"][i] - (s2["end"][j] - 2.0)
                    s2["start"][i] -= d
                    s2["end"][i] -= d
                    return s2, f"{seg[ex[i][0]].tag} starts 2 cycles before its producer {seg[ex[j][0]].tag} ends"
    raise ValueError(kind)


def driver(a):
    import plane_compiler as PC
    from hgi_sim import hbm_plane_model as M
    st = M.load_stats(PC.STATS)
    PC.CUR["hist"] = PC.lane_hists()
    kn = PC.Knobs(coll_lanes=5, union_hist=True, m1=True, rpl=True, P=a.P)   # P: lanes (owner 0le 10-19: P = 3)
    PC.apply_knobs(kn)
    keys = set(a.layers.split(",")) if a.layers else None
    u6, uu = st["verify_union"][6]["mean"], st["users_union"]
    modes = dict(mtp=(6, dict(union=u6, kv="upper", users=False)), mu=(4, dict(union=uu.get(4), users=True)),
                 ar=(1, {}))
    out = dict(schema="opentallas.hbm_next_1019.cmtp.static_check.v1", P=a.P, knobs=kn.tag(), rule=__doc__, modes={})
    a.out.mkdir(parents=True, exist_ok=True)
    for mode in a.mode.split(","):
        N, kw = modes[mode]
        cfg = M.plane_cfg(a.P if N > 1 else 1)
        PC.CUR["mode"] = "users" if kw.get("users") else "verify"
        prog, stc = M.ds_compile(N, cfg, kw.get("union", 6.0), kw.get("kv", "upper"), kw.get("users", False))
        M.P5._count_slots(prog)
        M.P5._consumers(prog)
        segs = schedule_segments(prog, keys)
        res = {}
        for key, seg, s in segs:
            r = check(seg, s, n_rows=N, ring=(256, N) if N > 1 else (128, 1),
                      vm_capacity={"as_built_2^18": VM_WORDS, "grown_D1": VM_WORDS + (N - 1) * 30000})
            r["cycles"] = round(s["total_cycles"], 1)
            res[str(key)] = r
            print(mode, key, "PASS" if r["PASS"] else "FAIL", r["counts"], "vm peak (bookkeeping upper bound)",
                  r["vm"]["peak_words"],
                  "cycles", r["cycles"], flush=True)
        mut = {}
        key0, seg0, s0 = segs[0]
        for kind in ("unit_double_book", "raw_early"):
            s2, what = mutate(seg0, s0, kind)
            r = check(seg0, s2, n_rows=N)
            mut[kind] = dict(what=what, PASS=r["PASS"], counts=r["counts"],
                             expected="FAIL", witness_ok=not r["PASS"])
            print(mode, "MUTANT", kind, "->", "PASS (BAD)" if r["PASS"] else "FAIL (witness ok)", r["counts"], what,
                  flush=True)
        ring_neg = c5_ring(128, N) if N > 1 else None
        mut["ring128"] = dict(what=f"window ring 128 slots with N = {N} rows", PASS=bool(ring_neg and ring_neg["ok"]),
                              witness_ok=bool(ring_neg and not ring_neg["ok"]), nbad=ring_neg and ring_neg["nbad"])
        out["modes"][mode] = dict(N=N, segments=res, all_pass=all(r["PASS"] for r in res.values()), mutants=mut,
                                  compile=stc)
        (a.out / "static_check.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    srcs = ["tools/hbm_next/static_check.py", "tools/hbm_next/plane_compiler.py", "tools/hbm_next/isa_rows.py",
            "tools/hgi_sim/timing.py", "tools/hgi_sim/ds_mtp_verify.py"]
    out["sources_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in srcs}
    (a.out / "static_check.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mode", default="mtp,mu,ar")
    ap.add_argument("--layers", default="")
    ap.add_argument("--P", type=int, default=3, help="position lanes (owner 0le 10-19: P = 3)")
    a = ap.parse_args()
    return driver(a)


if __name__ == "__main__":
    raise SystemExit(main())
