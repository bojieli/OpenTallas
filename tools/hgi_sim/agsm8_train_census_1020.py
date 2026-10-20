#!/usr/bin/env python3
"""HBM-AGSM8 (10-20): census variants of the DS expert-intermediate all-gather -> w2 SM.MATVEC chain.

Runs tools/hgi_sim/toksim_hbm_census_1019 (--measured, job info_banklat_all) unchanged and, per DS layer segment,
re-emits the 7 `expert_intermediate_gather.s<k>` COLL records and the 7 `expert slot <k> w2` SM records as one of:

  base        the compiled order (reproduces the census row).
  interleave  compiler order only (no RTL): s0, w2 s0, s1, w2 s1, ... (wait bits unchanged).
  batch       (a) ONE multi-segment gather record (the 7 slices back to back, one issue): segment k issues
              STEP after segment k-1 instead of after its retire; every w2 keeps the whole-record COLL wait.
  go          (b) per-record gathers as today, the w2 of slot k is statically started on its OWN gather's
              publication + LEAD (no COLL wait bit: segment-granular RAW resolved by the compiler).
  train_go    (c) = batch + go: segment k of the train publishes at t0 + C_SEG + k STEP and the w2 of slot k starts
              statically at that publication + LEAD.

Pricing (no new constants beyond the measured ones):
  C_SEG  = the census measured record cost of the 2304-word gather (260.2 = on-die adders 149.8 as priced + measured
           off-die train step 110.4) -- each segment keeps its full single-record latency.
  STEP   = max(on-die, off-die) segment step.  Off-die: 773 / 7 = 110.43, the MEASURED AG(144) train (tb_xdie_hbm_step
           reg_ds_ag144, launch -> last publication 773 for the 7 records of the train, coll.json).  On-die: the gather
           master's busy span SP = 129 edges at VM_RT 74 (MEASURED, tb_agsm8_chain: fires L+3+129k, a fire at 128
           faults), so the release figure is --step 129 (the default 110.43 is the off-die-only bound).
  LEAD   = the COLL retire wire + the SM dispatch wire the wait-bit path pays today (4 + 12 = 16): the static GO keeps
           the same publication -> SM start distance (bench: tb_agsm8_chain measures it).
Order inside the window: gathers in slot order, then w2 in slot order, the moe_sum / hc records keep their relative
order (moe_sum.* after the w2 they read).  The best of the candidate orders is taken per variant (compiler choice).

    PYTHONPATH=tools python3 -m hgi_sim.agsm8_train_census_1020 --variant train_go --out X.json \
        --measured M.json --bw 98 --bridge 1
"""
from __future__ import annotations

import copy
import dataclasses
import inspect
import re
import sys
import textwrap

from hgi_sim import timing as T
from hgi_sim import toksim_hbm_census_1019 as C

import hbm_generic_iface as HGI  # noqa: E402

AG_RE = re.compile(r"^expert_intermediate_gather\.s(\d+)$")
W2_RE = re.compile(r"^expert slot (\d+) w2$")
STEP = 773.0 / 7.0
LEAD = 16.0
COLL_BIT = 1 << HGI.UNITS.index("COLL")
VAR = {"v": "base", "orders": ("a",)}
HOOK = {}            # per schedule call: k (record index) -> dict(train_prev=k', go_after=k'')

# ---- patched copy of timing.schedule: two hooks, otherwise byte-identical source ----------------------------------
_src = textwrap.dedent(inspect.getsource(T._ORIG_SCHEDULE if hasattr(T, "_ORIG_SCHEDULE") else C._ORIG_SCHED))
_anchor = "            start[i] = t0\n            if mode in (\"S2\", \"SX\"):\n" \
          "                bind[i] = [bd if mode == \"S2\" else (\"ready\", i - 1 if i > 0 else None), bs, (\"cost\", i)]\n"
assert _src.count(_anchor) == 1, "timing.schedule anchor moved"
_hook = _anchor + textwrap.indent(textwrap.dedent("""
    _h = HOOK.get(k)
    if _h and mode not in ("S0", "S1"):
        _w = wire_of(r)
        if _h.get("train_prev") is not None:              # train segment: issue STEP after the previous segment
            jp = _h["train_prev"]
            t1 = max(d_t + _w, start[jp] + STEP, _h.get("_floor", 0.0))
            if t1 < start[i] - 1e-9 or t1 > start[i] + 1e-9:
                start[i] = t1
                if bind[i] is not None:
                    bind[i][1] = ("pipe", jp) if start[jp] + STEP >= d_t + _w - 1e-9 else ("disp", i)
        if _h.get("go_after") is not None:                # static GO on the producing segment's publication
            jg = _h["go_after"]
            jg = max(jg, key=lambda j: end[j]) if isinstance(jg, list) else jg
            t1 = end[jg] + LEAD
            if t1 > start[i] + 1e-9:
                start[i] = t1
                if bind[i] is not None:
                    bind[i][1] = ("unit", jg)
"""), " " * 12)
_src = _src.replace(_anchor, _hook)
# the train segment start must ignore the unit-serial term of the previous SEGMENT (it is pipelined), but keep it for
# any other COLL record before the train: record the COLL end before the train in _floor (set in transform)
_g = dict(T.__dict__)
_g.update(HOOK=HOOK, STEP=STEP, LEAD=LEAD)
exec(compile(_src, "<agsm8 patched timing.schedule>", "exec"), _g)
SCHED_PATCHED = _g["schedule"]


def _patched_with_floor(recs, pos, mode="S2", token=0, cost_fn=T.cost, wires=True):
    return SCHED_PATCHED(recs, pos, mode, token, cost_fn, wires)


SW_LEAD_NOTE = "swiglu_k static GO = the SM retire wire + SU dispatch wire the wait path pays (LEAD)"


def transform_ep(recs, lag, static_su):
    """expert-granular pipeline (info): swiglu split per expert (m = 1, same golden op per row), gather k right after
    swiglu k, w2 k on the SM after the w1 / w3 of the expert `lag` places later (static GO on gather k); swiglu k
    waits on its w1 / w3 (+ route.weights) by the unit wait bit (static_su=False) or a static GO (static_su=True)"""
    tags = [(r.tag or "") for r in recs]
    ag = {int(AG_RE.match(t).group(1)): i for i, t in enumerate(tags) if AG_RE.match(t)}
    w2 = {int(W2_RE.match(t).group(1)): i for i, t in enumerate(tags) if W2_RE.match(t)}
    w13 = {}
    for i, t in enumerate(tags):
        m = re.match(r"^expert slot (\d+) (w1|w3)$", t)
        if m:
            w13.setdefault(int(m.group(1)), []).append(i)
    sw = [i for i, t in enumerate(tags) if t == "swiglu"]
    rw = [i for i, t in enumerate(tags) if t == "route.weights"]
    if len(ag) != 7 or len(sw) != 1 or len(rw) != 1 or sorted(w13) != sorted(ag) or sorted(w2) != sorted(ag):
        return None
    sw, rw = sw[0], rw[0]
    lo = min(i for v in w13.values() for i in v)
    hi = max(list(ag.values()) + list(w2.values()))
    moe = [i for i in range(lo, hi + 1) if tags[i].startswith("moe_sum")]
    pulled = set(ag.values()) | set(w2.values()) | {sw} | set(moe)
    base = [i for i in range(lo, hi + 1) if i not in pulled]
    R = recs[sw]
    split = {}
    for s in sorted(ag):
        r = copy.copy(R)
        r.desc = {k_: dataclasses.replace(d, base=d.base + s * d.stride, m=1) if d.m == 7 else d for k_, d in R.desc.items()}
        r.tag = f"swiglu.e{s}"
        r.reads = [f"e{s}.g@0", f"e{s}.u@0", "route_w@0"]
        r.writes = [f"ea.s{s}@0"]
        split[s] = r
    done = sorted(ag, key=lambda s: max(max(w13[s]), rw))          # expert ready order
    seq = list(base)
    ins = {}
    for s in done:
        anchor = max(max(w13[s]), rw)
        ins.setdefault(anchor, []).extend([("sw", s), ("ag", s)])
    out = []
    for i in seq:
        out.append(("r", i))
        for x in ins.get(i, []):
            out.append(x)
    # w2 k after the w3 of the expert `lag` places later in ready order, else at the end
    w3pos = {s: max(j for j, x in enumerate(out) if x == ("r", max(w13[s]))) for s in done}
    tail = []
    for n_, s in enumerate(done):
        if n_ + lag < len(done):
            tgt = done[n_ + lag]
            p = max(j for j, x in enumerate(out) if x in (("r", max(w13[tgt])), ("ag", tgt)))
            out.insert(p + 1, ("w2", s))
        else:
            tail.append(("w2", s))
    out += tail
    for o in moe:                                                   # after the last w2 it reads
        rd = set(getattr(recs[o], "reads", ()) or ())
        need = [("w2", s) for s in ag if f"e{s}.d@0" in rd]
        p = max(out.index(x) for x in need)
        out.insert(p + 1, ("r", o))
    lst = [recs[i] for i in range(lo)]
    kind = []
    for x in out:
        if x[0] == "r":
            lst.append(recs[x[1]])
        elif x[0] == "sw":
            lst.append(split[x[1]])
        elif x[0] == "ag":
            lst.append(recs[ag[x[1]]])
        else:
            lst.append(recs[w2[x[1]]])
        kind.append(x)
    lst += [recs[i] for i in range(hi + 1, len(recs))]
    new = T.rebuild_waits(lst)
    HOOK.clear()
    pos = {x: lo + j for j, x in enumerate(kind)}
    SMBIT, SUBIT = 1 << HGI.UNITS.index("SM"), 1 << HGI.UNITS.index("SU")
    for s in ag:
        new[pos[("w2", s)]].wait &= ~COLL_BIT
        HOOK.setdefault(pos[("w2", s)], {})["go_after"] = pos[("ag", s)]
        if static_su:
            k = pos[("sw", s)]
            new[k].wait &= ~SMBIT
            HOOK.setdefault(k, {})["go_after"] = [pos[("r", j)] for j in w13[s]] + [pos[("r", rw)]]
    return new


def transform(recs, variant, order="a"):
    """-> (records, hook) for one segment; identity when the segment has no expert-intermediate chain"""
    HOOK.clear()
    ag = {int(AG_RE.match(r.tag or "").group(1)): i for i, r in enumerate(recs) if AG_RE.match(r.tag or "")}
    w2 = {int(W2_RE.match(r.tag or "").group(1)): i for i, r in enumerate(recs) if W2_RE.match(r.tag or "")}
    if variant == "base" or len(ag) != 7 or sorted(w2) != sorted(ag):
        return recs
    lo, hi = min(ag.values()), max(list(ag.values()) + list(w2.values()))
    win = list(range(lo, hi + 1))
    chain = set(ag.values()) | set(w2.values())
    others = [i for i in win if i not in chain]
    slots = sorted(ag)
    if variant == "interleave":
        mid = [x for s in slots for x in (ag[s], w2[s])]
    else:
        mid = [ag[s] for s in slots] + [w2[s] for s in slots]
    # moe_sum.* records read e<k>.d: place each after the last w2 it reads (order a) or all at the end (order b)
    if order == "a":
        seq, front = list(mid), []
        for o in others:
            rd = set(getattr(recs[o], "reads", ()) or ())
            need = [w2[s] for s in slots if f"e{s}.d@0" in rd]
            if need:
                p = max(seq.index(j) for j in need)
                seq.insert(p + 1, o)
            else:
                front.append(o)                           # hc_ffn etc.: independent, issue first (own order kept)
        seq = front + seq
    else:
        seq = [o for o in others if not (getattr(recs[o], "tag", "") or "").startswith("moe_sum")] + mid + \
              [o for o in others if (getattr(recs[o], "tag", "") or "").startswith("moe_sum")]
    order_idx = list(range(lo)) + seq + list(range(hi + 1, len(recs)))
    if variant == "base_rb":                          # check: compiled order, waits rebuilt (== base)
        order_idx = list(range(len(recs)))
    assert sorted(order_idx) == list(range(len(recs)))
    pos_of = {k_old: k_new for k_new, k_old in enumerate(order_idx)}
    # the compiler's wait masks are minimal for ITS order: recompute them for the new order (Builder hazard rule)
    new = T.rebuild_waits([recs[k] for k in order_idx])
    if variant in ("go", "train_go"):
        for s in slots:                               # static GO replaces the COLL wait of every w2
            new[pos_of[w2[s]]].wait &= ~COLL_BIT
    if variant in ("batch", "train_go"):
        prev = None
        for s in slots:
            k = pos_of[ag[s]]
            if prev is not None:
                HOOK.setdefault(k, {})["train_prev"] = prev
            prev = k
    if variant in ("go", "train_go"):
        for s in slots:
            HOOK.setdefault(pos_of[w2[s]], {})["go_after"] = pos_of[ag[s]]
    return new


_CENSUS_SCHED = C.schedule


def schedule(recs, pos, mode="S2", token=0, cost_fn=T.cost, wires=True):
    v = VAR["v"]
    if v == "base" or mode != "S2" or C.DESIGN["d"] != "ds_ar":
        HOOK.clear()
        return _CENSUS_SCHED(recs, pos, mode, token, cost_fn, wires)
    if any(r.unit == "CTL" for r in recs):         # hooks index records == executed records (straight line)
        HOOK.clear()
        return _CENSUS_SCHED(recs, pos, mode, token, cost_fn, wires)
    if v.startswith("ep"):                           # ep_wait / ep_static: expert-granular pipeline (info)
        best = None
        for lag in (1, 2, 3):
            nr = transform_ep(recs, lag, v == "ep_static")
            if nr is None:
                HOOK.clear()
                return _CENSUS_SCHED(recs, pos, mode, token, cost_fn, wires)
            s = SCHED_PATCHED(nr, pos, mode, token, cost_fn, wires)
            if best is None or s["total_cycles"] < best[0]:
                best = (s["total_cycles"], lag)
        nr = transform_ep(recs, best[1], v == "ep_static")
        VAR.setdefault("picked", {}).setdefault(best[1], 0)
        VAR["picked"][best[1]] += 1
        return _CENSUS_SCHED(nr, pos, mode, token, cost_fn, wires)
    best = None
    for o in VAR["orders"]:
        # dry run (no census accounting) to pick the compiler order
        nr = transform(recs, v, o)
        s = SCHED_PATCHED(nr, pos, mode, token, cost_fn, wires)
        if best is None or s["total_cycles"] < best[0]:
            best = (s["total_cycles"], o)
    nr = transform(recs, v, best[1])
    VAR.setdefault("picked", {}).setdefault(best[1], 0)
    VAR["picked"][best[1]] += 1
    return _CENSUS_SCHED(nr, pos, mode, token, cost_fn, wires)


def main():
    argv = list(sys.argv[1:])
    if "--variant" in argv:
        i = argv.index("--variant")
        VAR["v"] = argv[i + 1]
        del argv[i:i + 2]
    if "--step" in argv:                          # train segment issue step (default the off-die measured 773 / 7)
        i = argv.index("--step")
        SCHED_PATCHED.__globals__["STEP"] = float(argv[i + 1])
        del argv[i:i + 2]
    VAR["orders"] = ("a", "b")
    sys.argv = [sys.argv[0]] + argv
    C._ORIG_SCHED = SCHED_PATCHED                 # every census schedule call runs the hooked copy (no-op w/o HOOK)
    T.schedule = schedule
    C.ONLY = "info_banklat_all"
    try:
        return C.main()
    except KeyError as e:                         # reprice main's table needs 'all'; the job files are written
        print(f"agsm8: reprice summary skipped ({e}); job files in the _jobs dir", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
