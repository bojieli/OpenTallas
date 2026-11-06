#!/usr/bin/env python3
"""HBM-BIND-5 option C router test, candidate only: reorder the NW partitions in the two SU/SFU rows (widths, row heights, spine x unchanged),
rip every buildable lane touching them, route as-built demand + U on the new floorplan with hb3_route3's builder.  Lanes that end on shared or
hard types, or cross NE/io, are kept as reservations: their windows stay occupied, their flops are carried unchanged (limit of this test).
usage: c_route.py PLAN LAT_JSON REPORT_JSON OUT ROW_A ROW_B   (rows comma-separated, without NW_)"""
import heapq, json, os, sys, time, itertools, collections
W4 = "/srv/opentallas-scratch2/claude/hbm-bind-5/tools/die_plan"
sys.path.insert(0, W4)
import lane_add as LA, schema as S
PLAN, LAT, REP, OUT, RA, RB = sys.argv[1:7]; os.makedirs(OUT, exist_ok=True)
raw = json.load(open(PLAN)); T = raw["partition_types"]
parts = {p["name"]: p for p in raw["partitions"]}
rows = [["NW_" + x for x in RA.split(",")], ["NW_" + x for x in RB.split(",")]]
FIX = {"NW_spu0", "NW_spu1"}
M = {n for r in rows for n in r} - FIX
log = open(OUT + "/route_log.jsonl", "a")
def say(**k):
    k["t"] = time.strftime("%H:%M:%S"); log.write(json.dumps(k) + "\n"); log.flush()
used = collections.Counter(); 
for x in json.load(open(LAT))["buses"]: used[x["lane"]] += x["width"]
U = json.load(open(REP))["lanes"]["unplanned_pairs"]
P0 = S.Plan(raw)
cnt = collections.Counter(p["type"] for p in raw["partitions"])
hard = {p["name"] for p in raw["partitions"] if T[p["type"]].get("hard")}
shared = {p["name"] for p in raw["partitions"] if cnt[p["type"]] > 1}
SPECIAL = lambda n: n.endswith(("_io", "_mca", "_mcb"))
demand = collections.Counter(); rip, keep = [], []
for lid, ln in P0.lanes.items():
    hp = [P0.ports[q] for q in ln["ports"]]
    chain = [hp[0]["src"]["part"]] + [x["dst"]["part"] for x in hp]
    if not set(chain) & M: continue
    bad = set(chain) & (shared | hard) or any(c.startswith("NE_") for c in chain) or S.DIE_PART in chain or any(SPECIAL(c) for c in chain)
    (keep if bad else rip).append((lid, chain))
base_flops = dict(rip=sum(used[l] * P0.lane_natural(l)["stations"] for l, _ in rip), keep=sum(used[l] * P0.lane_natural(l)["stations"] for l, _ in keep))
# reservations from the old plan, die frame
resv = []
for lid, chain in keep:
    for q in P0.lanes[lid]["ports"]:
        pr = P0.ports[q]
        for _, _, win in S.port_segments(pr):
            resv.append((lid, pr["src"]["part"], pr["face"], tuple(sorted(win))))
line = {}
for lid, a, df, win in resv:
    x0, y0, x1, y1 = P0.rect(a) if a in P0.parts and a != S.DIE_PART else (None,) * 4
    if x0 is None: continue
    line.setdefault(lid, []).append((df, {"E": x1, "W": x0, "N": y1, "S": y0}[df], win))
for lid, chain in rip:
    demand[(chain[0], chain[-1])] += used[lid]
for k, v in U.items():
    a, b = k.split("->")
    if a.startswith("NW_") and (b.startswith("NW_") or b == "root") or a == "root" and b.startswith("NW_"): demand[(a, b)] += v
# strip rip lanes fully; keep lanes lose ports and their buses on moved partitions only
kill = {l for l, _ in rip} | {l for l, _ in keep}
ports = {p["id"]: p for p in raw["ports"]}
for lid in kill:
    for q in P0.lanes[lid]["ports"]:
        pr = ports.pop(q)
        for end in ("src", "dst"):
            pn = pr[end]["part"]
            if pn == S.DIE_PART or pn in shared: continue
            t = T[parts[pn]["type"]]; bn = pr[end]["bus"]
            if lid in {l for l, _ in keep} and pn not in M: continue
            t["buses"] = [b for b in t.get("buses", []) if b["name"] != bn]
            if bn.endswith(("_i", "_o")):
                t["ft_slots"] = [s for s in t.get("ft_slots", []) if s["name"] != bn[:-2]]
raw["ports"] = list(ports.values())
raw["lanes"] = [l for l in raw["lanes"] if l["id"] not in kill]
if isinstance(raw.get("latency"), dict) and isinstance(raw["latency"].get("lanes"), dict):
    for l in kill: raw["latency"]["lanes"].pop(l, None)
if isinstance(raw.get("latency_groups"), list):
    raw["latency_groups"] = [g for g in raw["latency_groups"] if not set(g.get("lanes", [])) & kill]
for r in rows:
    x = 0.0
    for n in r:
        if n in FIX: assert abs(parts[n]["origin_um"][0] - x) < 1e-3, (n, x, parts[n]["origin_um"])
        parts[n]["origin_um"][0] = round(x, 4); x += T[parts[n]["type"]]["outline_um"][0]
json.dump(dict(rows=rows, rip=len(rip), keep=len(keep), base_flops=base_flops, demand={f"{a}->{b}": v for (a, b), v in demand.items()}), open(OUT + "/c_setup.json", "w"), indent=0)
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
b = B(raw, first_id=1200, require_cycle_match=False)
# reservations on the new layout: every partition with a face on the same line that covers the window; rows: the y window on every E/W face of that row
nw_parts = [n for n in b.P.parts if n.startswith("NW_") or n == "root"]
nres = stra = 0
for lid, ls in line.items():
    for df, c, win in ls:
        for q in nw_parts:
            x0, y0, x1, y1 = b.P.rect(q)
            for f, cc, lo, hi in (("E", x1, y0, y1), ("W", x0, y0, y1), ("N", y1, x0, x1), ("S", y0, x0, x1)):
                same_axis = (f in "EW") == (df in "EW")
                if not same_axis or win[1] < lo or win[0] > hi: continue
                if abs(cc - c) < 0.5 or (df in "EW" and q in M):        # horizontal hops re-thread through the whole row at this y
                    b.taken[(q, f)].append(win); nres += 1
say(reservations=nres, rip=len(rip), keep=len(keep), base_flops=base_flops, demand_bits=sum(demand.values()), pairs=len(demand))
names = [p["name"] for p in raw["partitions"]]
nodes = [n for n in names if n.startswith("NW_") and n not in hard and n not in b.shared and not SPECIAL(n)]
ns = nodes + ["root"]
EDGES = [(x, y) for x, y in itertools.combinations(ns, 2) if LA.shared_edge(b.P, x, y)]
say(edges=len(EDGES), nodes=len(ns))
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
built = []; left = {k: v for k, v in demand.items() if v > 0}
def dist(k):
    ca, cb = LA.centre(b.P, k[0]), LA.centre(b.P, k[1])
    return abs(ca[0] - cb[0]) + abs(ca[1] - cb[1])
def save(tag, full=False):
    json.dump(dict(tag=tag, built=len(built), bits=sum(x["bits"] for x in built), flops=sum(x["bits"] * x["stations"] for x in built),
                   maxcyc=max([x["cycles"] for x in built] or [0]), left={f"{k[0]}->{k[1]}": v for k, v in left.items() if v}, base_flops=base_flops),
              open(OUT + "/progress.json", "w"), indent=0)
    json.dump(built, open(OUT + "/built.json", "w"), indent=0)
    if full: json.dump(b.raw, open(OUT + "/die_plan.json", "w"), indent=1)
    say(saved=tag)
order = sorted(left, key=dist)
for D in (8.0, 12.0, 16.0):
    b.D = D
    for n, (a, z) in enumerate(order):
        penal = {}; fails = 0; part = 0
        while left[(a, z)] > 0 and fails < 3:
            c = caps(); need = left[(a, z)]
            chain = route(a, z, c, penal, min(need, 256)) or route(a, z, c, penal, min(need, 16))
            if not chain:
                say(pair=f"{a}->{z}", D=D, need=need, why="no chain"); break
            w = min(need, min(c[(u, v)] for u, v in zip(chain, chain[1:])))
            t0 = time.time()
            got = b.build_one(a, z, w, chain, "path", None, record=False, part=int(D) * 100 + part)
            if got is None:
                fails += 1
                for e in zip(chain, chain[1:]):
                    penal[e] = penal.get(e, 0) + 4000; penal[e[::-1]] = penal.get(e[::-1], 0) + 4000
                say(pair=f"{a}->{z}", D=D, w=w, chain=chain, why=b._why, s=round(time.time() - t0)); continue
            left[(a, z)] -= w; part += 1
            got["density"] = D; built.append(got)
            say(pair=f"{a}->{z}", D=D, w=w, lane=got["lane"], cycles=got["cycles"], stations=got["stations"], chain=chain, s=round(time.time() - t0))
        if n % 5 == 4: save(f"{D}:{n}")
    save(f"D{D}", full=True)
    if not any(left.values()): break
json.dump(dict(left={f"{k[0]}->{k[1]}": v for k, v in left.items() if v}), open(OUT + "/left.json", "w"))
save("final", full=True); say(done=True)
