#!/usr/bin/env python3
"""Stimulus of tb_s81ph_root_s (s81-gather 2026-10-13): ONE root's partial stream, ot_v41_ret_pkg tags.

    gen_root_stim.py <case> <seed> <out> [--trace trace.json --layer L --region R] [--S 16]

  C <gap> <tag> <data> <e>     a partial <gap> cycles after the previous one (gap >= 1)
  E                            wait until both roots are quiet (end of a field phase)
Cases
  real    the REAL field order of one root over one layer: tools/s81_ph/root_open_rows.py --trace (the S81 binding's
          phases; every row's segment partials in segment-end order, one a cycle, phases separated by E)
  stress  random rows, 1..31 segments, random cuts of the golden tree (nodes added below the root arrive as k > 0
          partials), random interleave of <= S/2 open rows, gaps 1..3, plus runs that put siblings back to back
  full    exactly S rows open at once (first segment of S rows, then the others), twice (slots are reused)
  deep    a burst of 31-segment rows, one partial a cycle: the queue passes 64 words
  ovf     S + 1 rows open at once: ot_s81ph_ret_root_s must raise fault (capacity, fail closed)
  qfull   one partial a cycle until the 128-word queue is full: both roots fault
  bad     a partial that is not a tree node (lo not a multiple of 2^k): ot_s81ph_ret_root_s faults
  dup     the same partial twice, then its sibling: both roots fault
"""
import argparse, json, random, sys


def fval(rng):
    e = rng.randint(100, 150)
    return (rng.getrandbits(1) << 31) | (e << 23) | rng.getrandbits(23)


def tag(pos, row, lo, k, n):
    return (pos << 29) | (row << 13) | (lo << 8) | (k << 5) | n


def cut(rng, pos, row, nseg, bias):
    """random cut of the golden tree over [0, nseg): tags of the nodes that reach the root"""
    K = max(0, (nseg - 1).bit_length())
    out = []

    def rec(lo, k):
        if lo >= nseg:
            return
        if k == 0 or rng.random() < bias:
            out.append(tag(pos, row, lo, k, nseg))
        else:
            rec(lo, k - 1); rec(lo + (1 << (k - 1)), k - 1)
    rec(0, K)
    return out


class W:
    def __init__(self, f, rng):
        self.f, self.rng, self.gap = f, rng, 1

    def c(self, tg, gap=None, e=0):
        self.f.write(f"C {gap if gap is not None else self.gap:x} {tg:x} {fval(self.rng):x} {e:x}\n")
        self.gap = 1

    def wait(self, n):
        self.gap += n

    def end(self):
        self.f.write("E\n"); self.gap = 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("case"); ap.add_argument("seed", type=int); ap.add_argument("out")
    ap.add_argument("--trace"); ap.add_argument("--layer"); ap.add_argument("--region")
    ap.add_argument("--S", type=int, default=16)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    S = a.S
    with open(a.out, "w") as f:
        w = W(f, rng)
        if a.case == "real":
            tr = json.load(open(a.trace))["layers"][a.layer]["traces"][a.region]
            for ph in tr:
                prev = None
                for t, tg in ph["events"]:
                    w.c(tg, 1 if prev is None else max(1, t - prev)); prev = t
                w.end()
        elif a.case == "stress":
            row = 0
            for rep in range(40):
                nrow = rng.randint(1, S // 2)
                per = []
                for _ in range(nrow):
                    n = rng.choice([1, 2, 2, 3, 4, 5, 7, 8, 9, 16, 17, 31])
                    p = cut(rng, rng.randint(0, 7), row, n, rng.choice([0.0, 0.0, 0.3, 0.6]))
                    if rng.random() < 0.5:
                        rng.shuffle(p)
                    per.append(p); row = (row + rng.randint(1, 5)) & 0xFFFF
                mode = rng.choice(["rr", "seq", "rand"])
                order = []
                if mode == "seq":
                    for p in per: order += p
                elif mode == "rr":
                    i = 0
                    while any(per):
                        if per[i % nrow]: order.append(per[i % nrow].pop(0))
                        i += 1
                else:
                    while any(per):
                        p = rng.choice([x for x in per if x]); order.append(p.pop(0))
                burst = rng.random() < 0.6
                for tg in order:
                    w.c(tg, 1 if burst else rng.randint(1, 3))
                w.end()
        elif a.case == "full":
            row = 100
            for rep in range(3):
                rows = [(rng.randint(0, 7), row + 3 * i, rng.choice([2, 2, 3, 4])) for i in range(S)]
                row += 3 * S
                for pos, r, n in rows: w.c(tag(pos, r, 0, 0, n))
                w.wait(40)
                for pos, r, n in rows:
                    for lo in range(1, n): w.c(tag(pos, r, lo, 0, n), rng.randint(1, 2))
                w.end()
        elif a.case == "deep":
            for r in range(6):
                p = cut(rng, 1, 7 + r, 31, 0.0)
                for tg in p: w.c(tg, 1)
            w.end()
        elif a.case == "ovf":
            for i in range(S + 1): w.c(tag(0, 2 * i, 0, 0, 2))
            w.wait(60)
            for i in range(S + 1): w.c(tag(0, 2 * i, 1, 0, 2))
            w.end()
        elif a.case == "qfull":
            for r in range(40):
                p = cut(rng, 0, r, 31, 0.0)
                for tg in p: w.c(tg, 1)
            w.end()
        elif a.case == "bad":
            w.c(tag(0, 4, 0, 0, 4)); w.c(tag(0, 4, 1, 1, 4)); w.c(tag(0, 4, 1, 0, 4)); w.c(tag(0, 4, 2, 1, 4))
            w.end()
        elif a.case == "dup":
            w.c(tag(0, 4, 0, 0, 2)); w.c(tag(0, 4, 0, 0, 2)); w.wait(30); w.c(tag(0, 4, 1, 0, 2))
            w.end()
        else:
            raise SystemExit(a.case)


if __name__ == "__main__":
    main()
