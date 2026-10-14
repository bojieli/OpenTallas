#!/usr/bin/env python3
"""Stimulus of tb_s81ph_gather_cl (s81-gather 2026-10-13): the 128 root lanes of the gather, phase by phase.

    gen_gather_cl_stim.py real <seed> <out> --trace trace.json --layer L     the REAL field order of one layer: every
        root's partial stream of every phase (tools/s81_ph/root_open_rows.py --trace-regions all)
    gen_gather_cl_stim.py stress <seed> <out>     every root: random rows / tree cuts, <= 4 rows open (S = 8)
    gen_gather_cl_stim.py ovf <seed> <out>        root 37: S + 1 rows open at once (capacity fault), the others quiet rows
    gen_gather_cl_stim.py refuse <seed> <out>     one root never returns a row (coverage refusal)

  P <phase>                           phase word (VM) + fld descriptor
  C <gap> <root> <tag> <data> <e>     gap 0 = same cycle as the previous C
  E                                   wait until quiet, then the capture's done event
"""
import argparse, json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_root_stim as G


def emit(f, rng, ph, ev):
    f.write(f"P {ph:x}\n")
    prev = None
    for t, r, tg in sorted(ev):
        f.write(f"C {(1 if prev is None else t - prev):x} {r:x} {tg:x} {G.fval(rng):x} 0\n"); prev = t
    f.write("E\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("case"); ap.add_argument("seed", type=int); ap.add_argument("out")
    ap.add_argument("--trace"); ap.add_argument("--layer"); ap.add_argument("--S", type=int, default=8)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    with open(a.out, "w") as f:
        if a.case == "real":
            tr = json.load(open(a.trace))["layers"][a.layer]["traces"]
            names = []
            for r in sorted(tr, key=int):
                for p in tr[r]:
                    if p["phase"] not in names: names.append(p["phase"])
            for i, nm in enumerate(names):
                ev = []
                for r in tr:
                    for p in tr[r]:
                        if p["phase"] == nm: ev += [(t, int(r), tg) for t, tg in p["events"]]
                emit(f, rng, i + 1, ev)
        elif a.case == "stress":
            for ph in range(6):
                ev = []
                for r in range(128):
                    row, t = 256 * ph + 2 * r, rng.randint(0, 8)
                    per = []
                    for _ in range(rng.randint(1, 4)):
                        n = rng.choice([1, 2, 2, 3, 4, 5, 8, 9, 16, 31])
                        p = G.cut(rng, rng.randint(0, 7), row & 0xFFFF, n, rng.choice([0.0, 0.3, 0.6]))
                        if rng.random() < 0.5: rng.shuffle(p)
                        per.append(p); row += 256
                    order = []
                    if rng.random() < 0.5:
                        for p in per: order += p
                    else:
                        while any(per):
                            p = rng.choice([x for x in per if x]); order.append(p.pop(0))
                    burst = rng.random() < 0.6
                    for tg in order:
                        t += 1 if burst else rng.randint(1, 3)
                        ev.append((t, r, tg))
                emit(f, rng, ph + 1, ev)
        elif a.case == "ovf":
            n = a.S + 1                                   # S + 1 rows open at once at root 37
            ev = [(i, 37, G.tag(0, 256 * i + 74, 0, 0, 2)) for i in range(n)]
            ev += [(80 + i, 37, G.tag(0, 256 * i + 74, 1, 0, 2)) for i in range(n)]
            ev += [(5 + r % 7, r, G.tag(0, 2 * r, 0, 0, 1)) for r in range(128) if r != 37]
            emit(f, rng, 1, ev)
        elif a.case == "refuse":                          # root 5 never returns a row: +NEED=1 must REFUSE the pass
            ev = [(5 + r % 7, r, G.tag(0, 2 * r, 0, 0, 1)) for r in range(128) if r != 5]
            emit(f, rng, 1, ev)
        else:
            raise SystemExit(a.case)


if __name__ == "__main__":
    main()
