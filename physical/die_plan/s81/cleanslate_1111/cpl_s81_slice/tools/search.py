#!/usr/bin/env python3
"""CPL-S81-SLICE B34-style legal local search (simulated annealing) on the 4.32 lattice.
usage: search.py PLAN TYPE OUTDIR [--seed-json F] [--iters N] [--rng K]
Moves: shift (lattice steps), relocate, swap equal-outline cores, flip (R0/MX/MY/R180).
Legal: inside outline (edge margin of the current plan), core gap >= current min gap, no NEW overlap with a landing
band, ft station reg, fixed content macro or the clock tap (pairs already present in the plan are grandfathered),
no station needing more stages than sited (EQ: station counts unchanged).
cost = bitmm/bitmm0 + 3*max(0, worst_cut - 0.5) [+ hard reject on legality]."""
import os
import json
import math
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpl  # noqa: E402
import common  # noqa: E402

LAT = 8.64   # S81 core origin lattice (G0C hard_cores: origins on 8.64, track offsets keep pins on tracks)
ORI = ["R0", "MX", "MY", "R180"]


def snap(v):
    return round(round(v / LAT) * LAT, 3)


class Search:
    def __init__(self, M):
        self.M = M
        self.pl0 = M.current()
        self.edge, self.gap = M.legality_params()
        self.grand = set((i, v) for i, v in M.violations(self.pl0, self.edge, self.gap))
        self.st_need0 = {}
        for s in M.st:
            pass
        self.need0 = {b[0]: b[2] for b in M.station_check(self.pl0)}
        self.b0 = max(1e-6, M.bitmm(self.pl0))
        self.intent = False

    def set_intent(self, disp=250.0, minbits=32, grow=1.2, slack=20.0, reach=396.9):
        """COORD 02:1x intent rule: the plan layout is the dataflow structure; search only fine-tunes it.  Every
        dataflow link of >= minbits (and every station link) may not grow beyond grow*len0+slack nor cross the
        reach if it was inside; each core stays within disp um (Manhattan) of its plan origin."""
        self.intent = True
        self.disp, self.grow, self.slack, self.reach = disp, grow, slack, reach
        self.ilinks = [l for l in self.M.links if l["bits"] >= minbits or l["kind"] == "st"]
        c = {}
        self.ilen0 = [cpl.man(*self.M.link_pts(l, self.pl0, c)) for l in self.ilinks]

    def intent_ok(self, pl):
        for i, (p, q) in enumerate(zip(pl, self.pl0)):
            if abs(p[0] - q[0]) + abs(p[1] - q[1]) > self.disp + 1e-6:
                return False
        c = {}
        for l, l0 in zip(self.ilinks, self.ilen0):
            d = cpl.man(*self.M.link_pts(l, pl, c))
            if d > self.grow * l0 + self.slack or (l0 <= self.reach < d):
                return False
        return True

    def legal(self, pl):
        if self.intent and not self.intent_ok(pl):
            return False
        for v in self.M.violations(pl, self.edge, self.gap):
            if v not in self.grand:
                return False
            # added clock taps: padded blocker; a near-touch in the plan is only grandfathered for an unmoved core
            if v[1].startswith("addtap:") and tuple(pl[v[0]]) != tuple(self.pl0[v[0]]):
                return False
        for (si, d, need, n) in self.M.station_check(pl):
            if need > max(n, self.need0.get(si, 0)):
                return False
        return True

    def cost(self, pl):
        bm = self.M.bitmm(pl)
        wv, wh = self.M.worst_cut(pl)
        wc = max(wv[3], wh[3])
        ep, _ = self.M.entry(pl)
        return bm / self.b0 + 3 * max(0.0, wc - 0.5) + ep, bm, wc, ep

    def greedy(self, start, step=34.56, passes=1):
        """connectivity-driven construction: cores in order of linked bits; each goes to the legal lattice spot and
        orient with the least bit-mm given the others (one pass), then the worst cut is checked by the SA."""
        M = self.M
        pl = list(start)
        wt = [0] * len(M.cores)
        for l in M.links:
            wt[l["a"][0]] += l["bits"]
            if l["b"][0] == "core":
                wt[l["b"][1]] += l["bits"]
        order = sorted(range(len(M.cores)), key=lambda i: -wt[i])
        for _ in range(passes):
            for i in order:
                w, hh = M.cores[i]["outline_um"]
                bestv, bestp = M.bitmm(pl) / self.b0 + M.entry(pl)[0], pl[i]
                xs = [snap(self.edge + k * step) for k in range(int((M.W - 2 * self.edge - w) / step) + 1)]
                ys = [snap(self.edge + k * step) for k in range(int((M.H - 2 * self.edge - hh) / step) + 1)]
                xs.append(snap(M.W - self.edge - w - LAT / 2 + 0.001) if False else xs[-1])
                for x in xs:
                    for y in ys:
                        for o in ORI:
                            cand = list(pl)
                            cand[i] = (x, y, o)
                            v = M.bitmm(cand) / self.b0 + M.entry(cand)[0]
                            if v < bestv - 1e-6 and self.legal(cand):
                                bestv, bestp = v, (x, y, o)
                pl[i] = bestp
        return pl

    def run(self, start, iters, rng, T0=0.05):
        M = self.M
        n = len(M.cores)
        cur = list(start)
        cc = self.cost(cur)
        best, bc = list(cur), cc
        same = {}
        for i, h in enumerate(M.cores):
            same.setdefault(tuple(h["outline_um"]), []).append(i)
        for it in range(iters):
            T = T0 * (1 - it / iters) + 1e-4
            new = list(cur)
            r = rng.random()
            i = rng.randrange(n)
            w, hh = M.cores[i]["outline_um"]
            x, y, o = new[i]
            if r < 0.45:
                s = rng.choice([1, 1, 2, 4, 8, 16, 32])
                dx, dy = rng.choice([(s, 0), (-s, 0), (0, s), (0, -s)])
                new[i] = (snap(x + dx * LAT), snap(y + dy * LAT), o)
            elif r < 0.65 and self.intent:
                continue
            elif r < 0.65:
                new[i] = (snap(rng.uniform(self.edge, M.W - self.edge - w)),
                          snap(rng.uniform(self.edge, M.H - self.edge - hh)), o)
            elif r < 0.85:
                grp = same[tuple(M.cores[i]["outline_um"])]
                if len(grp) < 2:
                    continue
                j = rng.choice([g for g in grp if g != i])
                new[i], new[j] = (new[j][0], new[j][1], new[i][2]), (new[i][0], new[i][1], new[j][2])
            elif self.intent:
                continue   # intent mode keeps the plan orient (flips move pins off the plan tracks, G0C hard_cores)
            else:
                new[i] = (x, y, rng.choice([q for q in ORI if q != o]))
            if not self.legal(new):
                continue
            nc = self.cost(new)
            if nc[0] < cc[0] or rng.random() < math.exp(-(nc[0] - cc[0]) / T):
                cur, cc = new, nc
                if cc[0] < bc[0]:
                    best, bc = list(cur), cc
        return best, bc


def main():
    plan, tname, out = sys.argv[1:4]
    args = sys.argv[4:]
    iters = int(args[args.index("--iters") + 1]) if "--iters" in args else 3000
    k = int(args[args.index("--rng") + 1]) if "--rng" in args else 1
    P, conns = cpl.load(plan)
    M = common.model(P, conns, tname)
    S = Search(M)
    if "--intent" in args:
        S.set_intent()
    rng = random.Random(k)
    starts = [("current", S.pl0)]
    if "--seed-json" in args:
        sj = json.load(open(args[args.index("--seed-json") + 1]))
        for nm, d in sj.items():
            pl = list(S.pl0)
            for inst, v in d.items():
                pl[M.ix[inst]] = (v[0], v[1], v[2])
            if S.legal(pl):
                starts.append((nm, pl))
            else:
                print("seed %s illegal: %s" % (nm, [v for v in M.violations(pl, S.edge, S.gap) if v not in S.grand][:6],
                      ), M.station_check(pl)[:4])
    if "--greedy" in args:
        t0 = time.time()
        g = S.greedy(S.pl0)
        print(tname, "greedy built", S.cost(g), round(time.time() - t0), "s", flush=True)
        starts.append(("hand_greedy", g))
    res = {"type": tname, "edge": S.edge, "gap": S.gap, "bitmm0": S.b0, "cost0": S.cost(S.pl0), "runs": []}
    for nm, st in starts:
        t0 = time.time()
        best, bc = S.run(st, iters, rng)
        res["runs"].append(dict(start=nm, cost=bc, start_cost=S.cost(st), pl=best, sec=round(time.time() - t0)))
        print(tname, nm, "start", S.cost(st), "->", bc, round(time.time() - t0), "s", flush=True)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
