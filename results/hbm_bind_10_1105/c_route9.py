#!/usr/bin/env python3
"""HBM-BIND-7 c4: c_route3 + chained per-partition station solve (entry = previous station, exact hop; last slot to the end face).
HBM-BIND-5 option C router test, candidate only: reorder the NW partitions in the two SU/SFU rows (widths, row heights, spine x unchanged),
rip every buildable lane touching them, route as-built demand + U on the new floorplan with hb3_route3's builder.  Lanes that end on shared or
hard types, or cross NE/io, are kept as reservations: their windows stay occupied, their flops are carried unchanged (limit of this test).
usage: c_route.py PLAN LAT_JSON REPORT_JSON OUT ROW_A ROW_B   (rows comma-separated, without NW_)"""
import heapq, json, os, sys, time, itertools, collections
W4 = "/srv/opentallas-scratch2/claude/hbm-bind-5/tools/die_plan"
sys.path.insert(0, W4)
import lane_add as LA, schema as S
# HBM-BIND-8 c_route6 (MODE=M47 default layers, HALF=ALL, endpoints may be hard/shared/special; pass-through only via plain nodes) from c_route5: die-top M8/M9 leftover route per METHODOLOGY 12.1c/e (COORD 11:3x YES). Starts from a finished C plan
# (c4 or ne4: die_plan.json + left.json), routes ONLY the leftover pairs, every hop on M8 (E/W faces) / M9 (N/S faces) with
# its own window occupancy (M4-M7 windows and reservations do not block M8/M9), stations at <=405 um in partition bays.
# usage: c_route5.py FROM_DIR OUT_DIR HALF(NW|NE)
FROM, OUT, HALF = sys.argv[1:4]; os.makedirs(OUT, exist_ok=True)
log = open(OUT + "/route_log.jsonl", "a")
def say(**k):
    k["t"] = time.strftime("%H:%M:%S"); log.write(json.dumps(k) + "\n"); log.flush()
M89 = ("M8", "M9")
_fi = LA.face_intervals
def face_layers(P, part, df): return ["M8"] if df in "EW" else ["M9"]
def face_intervals(P, part, df):
    out = []
    for pid, pr in P.ports.items():
        lay = set(pr.get("layers") or []) | set(pr.get("in_layers") or []) | set(pr.get("out_layers") or [])
        for w in pr.get("windows") or []: lay |= set(w.get("layers") or [])
        if lay and lay <= set(M89): out.append(pid)
    keep = set(out)
    sub = type("PP", (), {})(); sub.ports = {k: P.ports[k] for k in keep}
    return _fi(sub, part, df)
MODE = os.environ.get("MODE", "M89")
if MODE == "M89": LA.face_layers = face_layers; LA.face_intervals = face_intervals
CHAIN7 = True
raw = json.load(open(FROM + "/die_plan.json")); T = raw["partition_types"]; parts = {p["name"]: p for p in raw["partitions"]}
cnt = collections.Counter(p["type"] for p in raw["partitions"])
hard = {p["name"] for p in raw["partitions"] if T[p["type"]].get("hard")}
SPECIAL = lambda n: n.endswith(("_io", "_mca", "_mcb"))
base_flops = None
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
        return self.per_part(slots, start, end)
    def per_part(self, slots, start=None, end=None):
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
            if CHAIN7 and out: A = out[-1][-1]
            elif CHAIN7 and start is not None and not out: A = start
            last = sl is slots[-1]
            if CHAIN7 and last and end is not None: Z = end
            a = (A[0] - x0, A[1] - y0); z = (Z[0] - x0, Z[1] - y0)
            regs = None; fb = None
            for n in range(sl[8], sl[8] + 13):
                regs = SR.route(m, a, z, n, self.reach)
                if regs is None or sl[10] / n > self.smax + 1e-6:
                    regs = None; continue
                h = self.reach / 2
                dz = abs(regs[-1][0] - z[0]) + abs(regs[-1][1] - z[1])
                if CHAIN7:
                    if last or dz <= h: break
                    if fb is None: fb = regs
                    regs = None; continue
                if abs(regs[0][0] - a[0]) + abs(regs[0][1] - a[1]) <= h and dz <= h: break
                regs = None
            if regs is None: regs = fb
            if regs is None:
                say(dbg="slot_fail", part=p, n0=sl[8], L=round(sl[10]), entry=[round(a[0]), round(a[1])], exit=[round(z[0]), round(z[1])])
                return None
            out.append([(round(r[0] + x0, 4), round(r[1] + y0, 4)) for r in regs])
        return out
# ---- HBM-BIND-9 c_route8: hub<->sm re-route with endpoint-bus reuse (COORD 12:06 ruling). Restores every p7 hub<->sm lane
# missing in FROM: the sm-side bus (shared 2x type) and the hub-side bus stay unchanged at their p7 die windows; only the
# interior row chain is re-routed (one lane per old bus, full width). usage: P7=<p7 die_plan.json> c_route8.py FROM OUT ALL
P7 = S.Plan(json.load(open(os.environ["P7"])))
b = B(raw, first_id=int(os.environ.get("FIRST", 8300)), require_cycle_match=False)
FORCE = {}
def ovl(iv, win, g):
    return [x for x in iv if min(x) < max(win) + g and max(x) > min(win) - g]
class B8(B): pass
def alloc8(self, a, z, width, prefer=None):
    f = FORCE.get((a, z))
    if f is None: return LA.Builder.alloc(self, a, z, width, prefer)
    df, win, layers, endp = f
    if endp is None:                                   # kept prefix hop (unchanged partitions, old slot windows)
        self.taken[(a, df)].append(tuple(win)); self.taken[(z, LA.OPP[df])].append(tuple(win)); return df, list(win), layers
    nb = z if endp == a else a
    ndf = df if nb == a else LA.OPP[df]
    occ = LA.face_intervals(self.P, nb, ndf) + self.taken[(a, df)] + self.taken[(z, LA.OPP[df])]
    bad = ovl(occ, win, float(os.environ.get('FGUARD', '0.05')))  # p7 windows were legal side by side
    if bad: self._why_force = f"forced window {a}|{z} {win} overlaps {bad[:3]}"; return None
    self.taken[(a, df)].append(tuple(win)); self.taken[(z, LA.OPP[df])].append(tuple(win))
    return df, list(win), layers
b.alloc = alloc8.__get__(b)
def chain_of(P, lid):
    hp = [P.ports[q] for q in P.lanes[lid]["ports"]]
    return hp, [hp[0]["src"]["part"]] + [x["dst"]["part"] for x in hp]
def neighbour(P, endp, df_n, win):
    """partition whose die face df_n abuts endp and covers win"""
    for n in P.parts:
        if n in (endp, S.DIE_PART): continue
        e = LA.shared_edge(P, n, endp)
        if e and e[0] == df_n and e[1] <= min(win) + 1e-3 and e[2] >= max(win) - 1e-3: return n
    return None
names = [p["name"] for p in raw["partitions"]]
nodes0 = [n for n in names if n not in hard and n not in b.shared and not SPECIAL(n)]
ns = nodes0 + (["root"] if os.environ.get("ROOT_PASS") == "1" else [])
EDGES = [(x, y) for x, y in itertools.combinations(ns, 2) if LA.shared_edge(b.P, x, y)]
ends = set(); BLOCK = set()
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
            if y == "root" and z != "root" and os.environ.get("ROOT_PASS") != "1": continue
            if y in ends and y != z and y not in nodes0: continue
            if y in BLOCK and y != z: continue
            cu, cv = ctr(u), ctr(y)
            nd = d + abs(cu[0] - cv[0]) + abs(cu[1] - cv[1]) + 300 + penal.get((x, y), 0)
            if nd < dist.get(y, 1e18):
                dist[y], prev[y] = nd, u; heapq.heappush(hq, (nd, y))
    if z not in prev: return None
    p = [z]
    while p[-1] != a: p.append(prev[p[-1]])
    return p[::-1]

# ---- c_route9: shared-prefix reuse (spb0->root): keep the p7 lane's ports through the shared/unchanged prefix (old bus + old
# ft slots on shared types, same windows), re-route only from the first plain partition after the last shared one.
# usage: P7=.. ONLY=L117,L117m,L138,L138m c_route9.py FROM OUT ALL
built = []; failed = []
for lid in os.environ["ONLY"].split(","):
    hp, ch = chain_of(P7, lid); a, z = ch[0], ch[-1]; w = hp[0]["width"]
    k = max(i for i, n in enumerate(ch) if n in b.shared or n == a)      # last shared index in the chain
    FORCE.clear(); BLOCK.clear(); BLOCK.update({a, z} | {n for n in names if n.endswith("_hub")} | set(ch[:k + 1]))
    for i in range(k + 1):                                               # hops ch[i]->ch[i+1], i <= k
        pr = hp[i]; FORCE[(ch[i], ch[i + 1])] = (pr["face"], tuple(sorted(pr["window_um"])), list(pr.get("layers") or LA.face_layers(b.P, ch[i], pr["face"])), None)
    start = ch[k + 1]
    mid = [start] if start == z else route(start, z, caps(), {}, w)
    if mid is None: failed.append(dict(lane=lid, why=f"no chain {start}->{z}")); say(lane=lid, why="no chain", start=start); continue
    chain = ch[:k + 1] + mid
    sv = b.shared; b.shared = set(); b._why_force = None
    try: got = b.build_one(a, z, w, chain, "path", None, record=False, part=0)
    finally: b.shared = sv
    if got is None: failed.append(dict(lane=lid, chain=chain, why=b._why_force or b._why)); say(lane=lid, chain=chain, why=b._why_force or b._why); continue
    nl = got["lane"]
    pid = sorted([p for p in b.raw["ports"] if p["id"].startswith(nl + "_")], key=lambda p: int(p["id"].rsplit("_", 1)[1]))
    # rename: hop i src bus / dst bus to the old names for every reused part (a and shared prefix parts)
    for i in range(k + 1):
        old = hp[i]; new = pid[i]
        for side in ("src", "dst"):
            part = new[side]["part"]
            if part not in b.shared and part != a: continue
            nbn, obn = new[side]["bus"], old[side]["bus"]; new[side]["bus"] = obn
            t = b.P.ptype(part)
            if nbn.endswith(("_i", "_o")) and nbn[:-2] != nl:      # slot side: drop the new slot (old one kept on the type)
                t["ft_slots"] = [x for x in t.get("ft_slots", []) if x["name"] != nbn[:-2]]
            else:
                t["buses"] = [x for x in t.get("buses", []) if x["name"] != nbn]
    b.P = S.Plan(b.raw); nat = b.P.lane_natural(nl)
    b.raw["latency"]["lanes"][nl] = dict(nat, natural=nat["cycles"], pad=0, param="LAT_" + nl.upper())
    got.update(cycles=nat["cycles"], stations=nat["stations"], replaces=lid, kept_prefix=ch[:k + 1])
    built.append(got); say(lane=lid, new=nl, w=w, chain=chain, cycles=nat["cycles"], stations=nat["stations"], kept=ch[:k + 1])
json.dump(dict(built=len(built), bits=sum(x["bits"] for x in built), flops=sum(x["bits"] * x["stations"] for x in built),
               maxcyc=max([x["cycles"] for x in built] or [0]), failed=failed), open(OUT + "/progress.tmp", "w"), indent=1)
json.dump(built, open(OUT + "/built.json", "w"), indent=0)
json.dump(b.raw, open(OUT + "/die_plan.json", "w"), indent=1)
os.replace(OUT + "/progress.tmp", OUT + "/progress.json"); say(done=True)
