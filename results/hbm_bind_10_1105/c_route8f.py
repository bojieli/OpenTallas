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
todo = []
for lid in P7.lanes:
    hp, ch = chain_of(P7, lid)
    a, z = ch[0], ch[-1]
    if not ((a.endswith("_hub") and z[-4:-1] == "_sm") or (z.endswith("_hub") and a[-4:-1] == "_sm")): continue
    if lid in b.P.lanes: say(skip=lid, why="present in FROM"); continue
    if os.environ.get('ONLY') and lid not in os.environ['ONLY'].split(','): continue
    todo.append((lid, a, z, hp))
say(todo=len(todo), bits=sum(x[3][0]["width"] for x in todo), edges=len(EDGES))
built = []; failed = []
for lid, a, z, hp in sorted(todo, key=lambda x: -x[3][0]["width"]):
    w = hp[0]["width"]; FORCE.clear(); reuse = {}; MOVE_NOW = set(); BLOCK.clear(); BLOCK.update({a, z} | {n for n in names if n.endswith('_hub')})
    p0, pl = hp[0], hp[-1]
    for endp, port, first in ((a, p0, True), (z, pl, False)):
        bus = port["src" if first else "dst"]["bus"]
        if not any(x["name"] == bus for x in b.P.ptype(endp).get("buses", [])):
            if endp in b.shared: failed.append(dict(lane=lid, why=f"sm bus {bus} missing")); break
            continue                                    # hub bus gone: allocate fresh on the (unique) hub type
        win = tuple(sorted(port["window_um"])); df_src = port["face"]
        if os.environ.get("BUSWIN") and endp in b.shared:      # sm window from the FROM plan's bus (candidate pin move)
            bb = [x for x in b.P.ptype(endp)["buses"] if x["name"] == bus][0]
            for ddf in "NSEW":
                tf, tw, fl = LA.to_type_window(b.P, endp, ddf, (0.0, 1.0))
                if tf == bb["face"]:
                    pp = b.P.parts[endp]; o = pp.get("orient", "R0"); w_, h_ = b.P.ptype(endp)["outline_um"]
                    base, ext = (pp["origin_um"][1], h_) if ddf in "EW" else (pp["origin_um"][0], w_)
                    lo, hi = bb["window_um"]
                    win = (round(base + ext - hi, 4), round(base + ext - lo, 4)) if fl else (round(base + lo, 4), round(base + hi, 4))
                    break
            say(buswin=endp, bus=bus, win=win)
        df_n = LA.OPP[df_src] if first else df_src     # face of the neighbour toward endp
        nb = neighbour(b.P, endp, df_n, win)
        if nb is None and endp not in b.shared:          # hub window straddles two C-row partitions: move it (bus name kept)
            ov = []
            for n in b.P.parts:
                if n in (endp, S.DIE_PART) or n in hard or n in b.shared or SPECIAL(n): continue
                e = LA.shared_edge(b.P, n, endp)
                if e and e[0] == df_n: ov.append((min(e[2], max(win)) - max(e[1], min(win)), n))
            if ov and max(ov)[0] > 0:
                reuse[endp] = (bus, max(ov)[1], first); MOVE_NOW.add(endp); continue
        if nb is None: failed.append(dict(lane=lid, why=f"no partition covers {endp} window {win}")); break
        lay = list(port.get("layers") or LA.face_layers(b.P, endp, LA.OPP[df_n]))
        if first: FORCE[(endp, nb)] = (df_src, win, lay, endp)
        else: FORCE[(nb, endp)] = (df_src, win, lay, endp)
        reuse[endp] = (bus, nb, first)
    else:
        got = None; chain = None; moved = next(iter(MOVE_NOW), None)
        hubs = [e for e in (a, z) if e not in b.shared]
        for attempt in (0, 1):
            if attempt == 1:
                why0 = b._why_force or ""
                hub = hubs[0] if hubs and hubs[0] in reuse else None
                if hub is None or f"{hub}|" not in why0 and f"|{hub}" not in why0: break
                bus, nbh, firsth = reuse[hub]
                FORCE.pop((hub, nbh) if firsth else (nbh, hub)); moved = hub     # hub window moves, bus name kept
            na = reuse[a][1] if a in reuse else None; nz = reuse[z][1] if z in reuse else None
            c = caps()
            mid = [na] if na == nz else route(na, nz, c, {}, w)
            chain = None if mid is None else [a] + mid + [z]
            if not chain: b._why_force = None; b._why = f"no chain {na}->{nz} cap>={w}"; break
            sv = b.shared; b.shared = b.shared - {a, z}; b._why_force = None
            try: got = b.build_one(a, z, w, chain, "path", None, record=False, part=0)
            finally: b.shared = sv
            if got is not None: break
        if got is None and moved:                         # moved hub window: try the hub's other plain neighbours
            bus, nb0, firsth = reuse[moved]; other = a if moved == z else z; nzz = reuse[other][1]
            cz = LA.centre(b.P, nzz)
            alts = sorted((n for n in nodes0 if n != nb0 and LA.shared_edge(b.P, n, moved)),
                          key=lambda n: abs(LA.centre(b.P, n)[0] - cz[0]) + abs(LA.centre(b.P, n)[1] - cz[1]))
            for n in alts[:8]:
                reuse[moved] = (bus, n, firsth)
                mid = [n] if n == nzz else route(n, nzz, caps(), {}, w)
                if mid is None: continue
                chain = ([a] + mid + [z]) if firsth else ([a] + mid[::-1] + [z])
                sv = b.shared; b.shared = b.shared - {a, z}; b._why_force = None
                try: got = b.build_one(a, z, w, chain, "path", None, record=False, part=0)
                finally: b.shared = sv
                say(alt=lid, chain=chain, ok=got is not None, why=None if got else (b._why_force or b._why))
                if got is not None: break
        if got is None:
            failed.append(dict(lane=lid, chain=chain, why=b._why_force or b._why)); say(lane=lid, chain=chain, why=b._why_force or b._why); continue
        nl = got["lane"]; prs = {p["id"]: p for p in b.raw["ports"]}
        pid = [p["id"] for p in b.raw["ports"] if p["id"].startswith(nl + "_")]
        pid.sort(key=lambda s: int(s.rsplit("_", 1)[1]))
        for endp, (bus, nb, first) in reuse.items():
            pr = prs[pid[0] if first else pid[-1]]; side = "src" if first else "dst"
            newb = pr[side]["bus"]; pr[side]["bus"] = bus
            t = b.P.ptype(endp)
            if endp == moved:
                nbus = [x for x in t["buses"] if x["name"] == newb][0]
                old = [x for x in t["buses"] if x["name"] == bus][0]
                nbus["name"] = bus; nbus["dir"] = old.get("dir", nbus["dir"])
                t["buses"] = [x for x in t["buses"] if x is not old]
            else:
                t["buses"] = [x for x in t["buses"] if x["name"] != newb]
        b.P = S.Plan(b.raw); nat = b.P.lane_natural(nl)
        b.raw["latency"]["lanes"][nl] = dict(nat, natural=nat["cycles"], pad=0, param="LAT_" + nl.upper())
        got.update(cycles=nat["cycles"], stations=nat["stations"], replaces=lid, reused={k: v[0] for k, v in reuse.items()}, hub_window_moved=moved)
        built.append(got); say(lane=lid, new=nl, w=w, chain=chain, cycles=nat["cycles"], stations=nat["stations"], moved=moved)
json.dump(dict(built=len(built), bits=sum(x["bits"] for x in built), flops=sum(x["bits"] * x["stations"] for x in built),
               maxcyc=max([x["cycles"] for x in built] or [0]), hub_moved=[x["replaces"] for x in built if x.get("hub_window_moved")], failed=failed), open(OUT + "/progress.json", "w"), indent=1)
json.dump(built, open(OUT + "/built.json", "w"), indent=0)
json.dump(b.raw, open(OUT + "/die_plan.json", "w"), indent=1)
say(done=True)
