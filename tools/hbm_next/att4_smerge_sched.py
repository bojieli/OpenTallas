#!/usr/bin/env python3
"""HBM-NEXT-ATT4 A1 (2026-10-19): turn-level model of the SHARED 4-lane PV merge schedule (rtl/hbm_next/att/
ot_hnx_att4_smerge.sv) -- the compiler's replay of the static schedule, and a collision stress.

All 8 ring slots of a column behave identically (a lane's chunk end produces the 8 slots' events on their 8 residues of
the same ring rotation), so one residue is modelled: time = TURNS of that residue (one turn = 8 cycles; the adder result
of a turn is back at the next turn).  Per turn, exactly as the RTL: each lane may deliver one chunk event (chunk c of its
run, run_last flag); an event writes its own free level; among lanes with a step (an event arriving now counts), the lane
whose result returns now keeps the turn, else the lowest lane; one add a turn.  COLLISION = FAULT, as the RTL: an event
on an entry with an unissued step, an event on the word an in-flight result is about to write, a run longer than
2^(LV-1) chunks.

A legal record gives every lane at most one token a union row and a PV union row lasts >= 8 cycles (one ring rotation),
so a lane's chunk events (8 of its tokens) are >= 8 turns apart.  `stress` draws random and adversarial (aligned,
staggered, back-to-back runs) event patterns under exactly that bound and reports faults and the worst node latency.

  att4_smerge_sched.py stress [--trials N] [--lv 3] [--seed S] [--out R.json]
"""
from __future__ import annotations

import argparse
import json
import random
import sys

IDLE, RIP, FL = 0, 1, 2


def tones(c):
    j = 0
    while c & 1:
        j += 1
        c >>= 1
    return j


def low(b):
    return (b & -b).bit_length() - 1


class Lane:
    def __init__(self):
        self.md, self.rk, self.rj, self.fin, self.ff, self.fb, self.n = IDLE, 0, 0, False, False, 0, 0


def simulate(events, nl=4, lv=3, max_turns=None):
    """events: {turn: {lane: (first, last)}}.  Returns dict(faults, nodes=[(lane, turn_out, chunks)], adds)."""
    top = lv - 1
    st = [Lane() for _ in range(nl)]
    ret = None                       # (lane, target, final, n) issued last turn
    faults, nodes, adds = [], [], 0
    last_t = max(events) if events else 0
    t, horizon = 0, (max_turns or last_t + 64)
    while t <= horizon:
        ev = events.get(t, {})
        desc = []
        for l in range(nl):
            s = st[l]
            if l in ev:
                first, last = ev[l]
                c = 0 if first else s.n
                ew = tones(c) if c & 1 else 0
                if s.md != IDLE:
                    faults.append((t, l, "event on an entry with an unissued step"))
                if ret and ret[0] == l and ret[1] == ew:
                    faults.append((t, l, "event on an in-flight word"))
                if c >= 1 << (lv - 1):
                    faults.append((t, l, "run longer than the stack"))
                n = c + 1
                d = dict(n=n, rk=0, rj=ew, fin=last, ff=True, fb=n & ((1 << lv) - 1),
                         md=RIP if c & 1 else (FL if last else IDLE))
            else:
                d = dict(n=s.n, rk=s.rk, rj=s.rj, fin=s.fin, ff=s.ff, fb=s.fb, md=s.md)
            desc.append(d)
        cand = [l for l in range(nl) if desc[l]["md"] != IDLE]
        sel = None
        if cand:
            sel = cand[0]
            if ret and ret[0] in cand:
                sel = ret[0]
        nret = None
        if ret and ret[2]:
            nodes.append((ret[0], t, ret[3]))
        for l in range(nl):
            d = desc[l]
            s = st[l]
            s.n, s.rj, s.fin = d["n"], d["rj"], d["fin"]
            s.md, s.rk, s.fb, s.ff = d["md"], d["rk"], d["fb"], d["ff"]
            if l != sel:
                continue
            adds += 1
            if d["md"] == RIP:
                lastr = d["rk"] + 1 == d["rj"]
                pone = (d["n"] & (d["n"] - 1)) == 0
                fin = lastr and d["fin"] and pone
                tgt = top if fin else d["rj"]
                if not lastr:
                    s.rk = d["rk"] + 1
                elif d["fin"] and not pone:
                    s.md, s.fb, s.ff = FL, d["n"] & ((1 << lv) - 1), True
                else:
                    s.md = IDLE
            else:
                k0 = low(d["fb"])
                rem0 = d["fb"] & ~(1 << k0)
                tgt = top
                if d["ff"] and rem0 == 0:
                    fin, s.fb = True, 0
                elif d["ff"]:
                    rem1 = rem0 & ~(1 << low(rem0))
                    fin, s.fb = rem1 == 0, rem1
                else:
                    fin, s.fb = rem0 == 0, rem0
                s.ff = False
                s.md = IDLE if fin else FL
            nret = (l, tgt, fin, d["n"])
        ret = nret
        t += 1
    busy = [l for l in range(nl) if st[l].md != IDLE]
    if busy or ret:
        faults.append((t, busy, "work left at the horizon"))
    return dict(faults=faults, nodes=nodes, adds=adds)


def pattern(rng, nl, lv, kind):
    """chunk-event pattern: each lane a sequence of runs (1 .. 2^(LV-1) chunks), consecutive events of a lane >= 8 turns
    apart (one chunk = 8 lane tokens, one token >= one union row >= one ring rotation)."""
    maxc = 1 << (lv - 1)
    ev, last_ev = {}, {}
    nruns = rng.randint(1, 4)
    for l in range(nl):
        t = {"aligned": 8, "stagger": 8 + l, "random": 8 + rng.randint(0, 16)}[kind]
        for _ in range(nruns):
            n = maxc if kind == "aligned" else rng.randint(1, maxc)
            for c in range(n):
                ev.setdefault(t, {})[l] = (c == 0, c == n - 1)
                last_ev[l] = t
                t += 8 if kind == "aligned" else 8 + (rng.randint(0, 3) if rng.random() < 0.5 else 0)
    return ev, last_ev


def stress(trials, nl, lv, seed):
    rng = random.Random(seed)
    worst_lat, faults, total_nodes, worst_case = 0, [], 0, None
    kinds = {"aligned": 0, "stagger": 0, "random": 0}
    for i in range(trials):
        kind = ("aligned", "stagger", "random")[i % 3] if i < 300 else "random"
        kinds[kind] += 1
        ev, last_ev = pattern(rng, nl, lv, kind)
        r = simulate(ev, nl, lv)
        if r["faults"]:
            faults.append(dict(trial=i, kind=kind, faults=r["faults"][:3]))
        total_nodes += len(r["nodes"])
        # latency of each node: turns from the run's last event to the node's result
        lastev = {}
        for t in sorted(ev):
            for l, (_, lst) in ev[t].items():
                if lst:
                    lastev.setdefault(l, []).append(t)
        for l, ts in lastev.items():
            outs = [to for (ll, to, _) in r["nodes"] if ll == l]
            for te, to in zip(ts, outs):
                if to - te > worst_lat:
                    worst_lat, worst_case = to - te, dict(trial=i, kind=kind, lane=l, event_turn=te, out_turn=to)
    return dict(trials=trials, kinds=kinds, nl=nl, lv=lv, seed=seed, nodes=total_nodes, faults=len(faults),
                fault_examples=faults[:5], worst_node_latency_turns=worst_lat,
                worst_node_latency_cycles=8 * worst_lat, worst_case=worst_case)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("stress")
    p.add_argument("--trials", type=int, default=20000)
    p.add_argument("--lv", type=int, default=3)
    p.add_argument("--nl", type=int, default=4)
    p.add_argument("--seed", type=int, default=1019)
    p.add_argument("--out")
    a = ap.parse_args(argv)
    r = stress(a.trials, a.nl, a.lv, a.seed)
    # negative control: an ILLEGAL record (the last lane's chunk 2 only 3 turns after its chunk 1, while the other lanes
    # ripple chunk 3) must fault -- the model and the RTL refuse it, never stall (P3 10-19: lane nl - 1, = lane 3 at nl 4)
    ev, il = {}, a.nl - 1
    for l in range(il):
        for c in range(4):
            ev.setdefault(8 * c, {})[l] = (c == 0, c == 3)
    ev.setdefault(16, {})[il] = (True, False)
    ev.setdefault(24, {})[il] = (False, False)
    ev.setdefault(27, {})[il] = (False, True)
    r["illegal_record_faults"] = len(simulate(ev, a.nl, a.lv)["faults"]) > 0
    ok = r["faults"] == 0 and r["illegal_record_faults"]
    print(("PASS" if ok else "FAIL") + " HNX_SMERGE_SCHED " + json.dumps({k: v for k, v in r.items() if k != "fault_examples"}))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(r, f, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
