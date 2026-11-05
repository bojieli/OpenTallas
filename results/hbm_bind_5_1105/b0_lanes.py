#!/usr/bin/env python3
"""HBM-BIND-5 B0 adoption: plan the hub<->b113 lanes on the B0 plan, order unchanged, nothing ripped. usage: b0_lanes.py PLAN REPORT_JSON OUT"""
import heapq, json, os, sys, time, itertools, collections, re
sys.path.insert(0, "/srv/opentallas-scratch2/claude/hbm-bind-5/tools/die_plan")
import lane_add as LA, schema as S
PLAN, REP, OUT = sys.argv[1:4]; os.makedirs(OUT, exist_ok=True)
raw = json.load(open(PLAN)); T = raw["partition_types"]
U = json.load(open(REP))["lanes"]["unplanned_pairs"]
log = open(OUT + "/route_log.jsonl", "a")
def say(**k):
    k["t"] = time.strftime("%H:%M:%S"); log.write(json.dumps(k) + "\n"); log.flush()
cnt = collections.Counter(p["type"] for p in raw["partitions"])
hard = {p["name"] for p in raw["partitions"] if T[p["type"]].get("hard")}
SPECIAL = lambda n: n.endswith(("_io", "_mca", "_mcb"))
class B(LA.Builder):
    D = 8.0
    def pins_need(self, width, layers):
        return width + 1, self.D * len(layers) / float(self.P.budgets.get("face_pin_layers", 2))
    def resite(self, chain, slots, start, end):
        base = [sl[8] for sl in slots]
        Ls = [max(sl[10], 1.0) for sl in slots]; tot = sum(Ls)
        for extra in (0, 1, 2, 3, 4, 6, 8):
            for i, sl in enumerate(slots):
                sl[8] = base[i] + (int(round(extra * Ls[i] / tot)) if extra else 0)
            got = LA.Builder.resite(self, chain, slots, start, end)
            if got: return got
        for i, sl in enumerate(slots):
            sl[8] = base[i]
        return self.per_part(slots)
    def per_part(self, slots):
        import numpy as np, station_resite as SR
        P, G, H = self.P, SR.G, SR.HALO
        out = []
        for sl in slots:
            p = sl[0]; x0, y0, x1, y1 = P.rect(p)
            nx, ny = int((x1 - x0) / G) + 2, int((y1 - y0) / G) + 2
            xs = x0 + np.arange(nx) * G; ys = y0 + np.arange(ny) * G
            m = (xs[:, None] > x0 + H) & (xs[:, None] < x1 - H) & (ys[None, :] > y0 + H) & (ys[None, :] < y1 - H)
            for bx0, by0, bx1, by1 in S.placed_macro_boxes(P.ptype(p), halo=H).values():
                c0, c1 = P.to_die(p, (bx0, by0)), P.to_die(p, (bx1, by1))
                ux0, ux1 = sorted((c0[0], c1[0])); uy0, uy1 = sorted((c0[1], c1[1]))
                m &= ~((xs[:, None] > ux0 - 1e-6) & (xs[:, None] < ux1 + 1e-6) & (ys[None, :] > uy0 - 1e-6) & (ys[None, :] < uy1 + 1e-6))
            A = self.face_pt(P, p, LA.OPP[sl[2]], sl[3]); Z = self.face_pt(P, p, sl[5], sl[6])
            a = (A[0] - x0, A[1] - y0); z = (Z[0] - x0, Z[1] - y0)
            regs = None
            for n in range(sl[8], sl[8] + 13):
                regs = SR.route(m, a, z, n, self.reach)
                if regs is None or sl[10] / n > self.smax + 1e-6:
                    regs = None; continue
                h = self.reach / 2
                if abs(regs[0][0] - a[0]) + abs(regs[0][1] - a[1]) <= h and abs(regs[-1][0] - z[0]) + abs(regs[-1][1] - z[1]) <= h: break
                regs = None
            if regs is None: return None
            out.append([(round(r[0] + x0, 4), round(r[1] + y0, 4)) for r in regs])
        return out
def route(a, z, c, penal, least):
    ctr = lambda n: LA.centre(b.P, n)
    dist = {a: 0.0}; prev = {}; hq = [(0.0, a)]
    while hq:
        d, u = heapq.heappop(hq)
        if u == z: break
        if d > dist[u]: continue
        for (x, y), v in c.items():
            if x != u or v < least: continue
            if y == "root" and z != "root": continue
            cu, cv = ctr(u), ctr(y)
            nd = d + abs(cu[0] - cv[0]) + abs(cu[1] - cv[1]) + 300 + penal.get((x, y), 0)
            if nd < dist.get(y, 1e18):
                dist[y], prev[y] = nd, u; heapq.heappush(hq, (nd, y))
    if z not in prev: return None
    p = [z]
    while p[-1] != a: p.append(prev[p[-1]])
    return p[::-1]

first = max(int(re.sub(r"\D", "", l["id"]) or 0) for l in raw["lanes"]) + 100
b = B(raw, first_id=first, require_cycle_match=False)
names = [p["name"] for p in raw["partitions"]]
built = []; left = {}
for side in ("NW", "NE"):
    nodes = [n for n in names if n.startswith(side + "_") and n not in hard and not SPECIAL(n)]
    EDGES = [(x, y) for x, y in itertools.combinations(nodes, 2) if LA.shared_edge(b.P, x, y)]
    def caps():
        c = {}
        for x, y in EDGES:
            df, lo, hi = LA.shared_edge(b.P, x, y)
            layers = LA.face_layers(b.P, x, df)
            per = b.D * len(layers) / float(b.P.budgets.get("face_pin_layers", 2))
            occ = LA.face_intervals(b.P, x, df) + LA.face_intervals(b.P, y, LA.OPP[df]) + b.taken[(x, df)] + b.taken[(y, LA.OPP[df])]
            big = max([g1 - g0 for g0, g1 in LA.free_gaps(lo + 1.0, hi - 1.0, occ, b.guard)] or [0])
            c[(x, y)] = c[(y, x)] = max(0, int(big * per * 0.97) - 2)
        return c
    for a, z in ((f"{side}_hub", f"{side}_b113"), (f"{side}_b113", f"{side}_hub")):
        need0 = U[f"{a}->{z}"]; left[f"{a}->{z}"] = need0
        for D in (8.0, 12.0, 16.0):
            b.D = D; penal = {}; fails = 0; part = 0
            while left[f"{a}->{z}"] > 0 and fails < 3:
                c = caps(); need = left[f"{a}->{z}"]
                chain = route(a, z, c, penal, min(need, 256)) or route(a, z, c, penal, min(need, 16))
                if not chain: say(pair=f"{a}->{z}", D=D, need=need, why="no chain"); break
                w = min(need, min(c[(u, v)] for u, v in zip(chain, chain[1:])))
                got = b.build_one(a, z, w, chain, "path", None, record=False, part=int(D) * 100 + part)
                if got is None:
                    fails += 1
                    for e in zip(chain, chain[1:]):
                        penal[e] = penal.get(e, 0) + 4000; penal[e[::-1]] = penal.get(e[::-1], 0) + 4000
                    say(pair=f"{a}->{z}", D=D, w=w, chain=chain, why=b._why); continue
                left[f"{a}->{z}"] -= w; part += 1; got["density"] = D; got["pair"] = f"{a}->{z}"; built.append(got)
                say(pair=f"{a}->{z}", D=D, w=w, lane=got["lane"], cycles=got["cycles"], stations=got["stations"], chain=chain)
            if not left[f"{a}->{z}"]: break
json.dump(dict(built=built, left=left, flops=sum(x["bits"] * x["stations"] for x in built)), open(OUT + "/result.json", "w"), indent=0)
json.dump(b.raw, open(OUT + "/die_plan.json", "w"), indent=1)
say(done=True)
print(dict(lanes=len(built), bits=sum(x["bits"] for x in built), flops=sum(x["bits"] * x["stations"] for x in built), cycles=sorted({x["cycles"] for x in built}), left=left))
