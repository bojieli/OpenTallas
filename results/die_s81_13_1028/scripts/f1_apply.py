"""DIE-S81-13: F1 joint4 apply overlay under GEOM-44 (a)/(b)/(c) (ESTIMATE on the proposal; kit regen + CTS still owed).
(a) reset: every reset net that loads relay FFs gets its driver placed at the load median; up-chain drivers follow if a hop > 405.
(b) tie: each SETN TIEHI is placed at its FF (unfixed, legaliser target), tie net ~ FF pin offset.
(c) clock: the u_y_x2 group FFs re-tap to the nearest of clk_t11 / clk_t10 (others keep their tap).
Writes overlay JSON (cell -> origin/fixed + per-FF tap) and prints the GEOM-44 metrics after apply.
usage: f1_apply.py JOINT4_DIR OUT.json"""
import json, sys, collections, re, statistics
J, OUT = sys.argv[1], sys.argv[2]
a = json.load(open(J + "/allocated_sites.json"))
G = json.load(open(J + "/endpoint_net_graph_v2.json")); C = G["cells"]; N = G["nets"]
d = json.load(open(J + "/dump.json"))
bt = {b[0]: (b[2], b[3]) for b in d["bterms"]}
mac = d["macros"]
new = {}
def loc(c): return new[c] if c in new else (a[c]["origin_um"] if c in a else C[c]["origin_um"])
def L1(p, q): return abs(p[0] - q[0]) + abs(p[1] - q[1])
def drv(net):
    for p in N[net]["pins"]:
        if p["direction"] == "OUTPUT": return p["pin"].rsplit("/", 1)[0], p["master"]
    return None, None
def innet(c):
    pins = C[c]["pins"]; ins = [p for p, v in pins.items() if v["direction"] == "INPUT"]
    return pins[ins[0]]["net"] if ins else None
def loads(net): return [p["pin"].rsplit("/", 1)[0] for p in N[net]["pins"] if p["direction"] == "INPUT"]
def inmac(p): return any(m[2] <= p[0] <= m[4] and m[3] <= p[1] <= m[5] for m in mac)
ffs = [c for c in a if C.get(c, {}).get("master", "").startswith("DFF")]
# (a) reset fanout follows the FFs: bottom-up, each buffer/inverter on a relay reset chain goes to the median of its loads
rnets = {C[f]["pins"]["RESETN"]["net"] for f in ffs}
lvl = collections.OrderedDict(); frontier = set(rnets); seen = set()
while frontier:
    nxt = set()
    for net in frontier:
        c, m = drv(net)
        if c is None or c in seen or m.startswith("DFF") or not (m.startswith("BUF") or m.startswith("INV")): continue
        seen.add(c); lvl[c] = m
        nn = innet(c)
        if nn: nxt.add(nn)
    frontier = nxt
moved_rst = 0
for c in lvl:   # first level = drivers of FF reset nets, then upward
    out = [p for p, v in C[c]["pins"].items() if v["direction"] == "OUTPUT"][0]
    ld = loads(C[c]["pins"][out]["net"])
    pts = [loc(x) for x in ld]
    med = [statistics.median(p[0] for p in pts), statistics.median(p[1] for p in pts)]
    if L1(med, loc(c)) > 1.0 and not inmac(med):
        new[c] = [round(med[0], 3), round(med[1], 3)]; moved_rst += 1
# upstream hops > 405 after the move: one planned repeater per such net at a macro-free point on the L path (either corner)
reps = {}
for c in lvl:
    nn = innet(c)
    if not nn: continue
    up, um = drv(nn)
    if up is None: continue
    p, q = loc(up), loc(c)
    if L1(p, q) <= 405 or nn in reps: continue
    best = None
    for corner in ((q[0], p[1]), (p[0], q[1])):
        for f in [i / 20 for i in range(1, 20)]:
            # point at fraction f along p -> corner -> q
            tot = L1(p, corner) + L1(corner, q); s_ = f * tot
            if s_ <= L1(p, corner):
                r = s_ / max(L1(p, corner), 1e-9); pt = [p[0] + (corner[0] - p[0]) * r, p[1] + (corner[1] - p[1]) * r]
            else:
                r = (s_ - L1(p, corner)) / max(L1(corner, q), 1e-9); pt = [corner[0] + (q[0] - corner[0]) * r, corner[1] + (q[1] - corner[1]) * r]
            if inmac(pt): continue
            h = max(L1(p, pt), L1(pt, q))
            if best is None or h < best[0]: best = (h, pt)
    reps[nn] = dict(net=nn, from_cell=up, to_cell=c, at=[round(v, 3) for v in best[1]] if best else None,
                    max_hop_um=round(best[0], 1) if best else None)
# (b) ties next to their FF
ties = 0; tie_len = []
for f in ffs:
    c, m = drv(C[f]["pins"]["SETN"]["net"])
    if c and m.startswith("TIEHI"):
        p = loc(f); new[c] = [round(p[0] + 1.08, 3), round(p[1], 3)]; ties += 1; tie_len.append(L1(new[c], p))
# (c) re-tap x2
retap = {}; td = []
for f in ffs:
    c, m = drv(C[f]["pins"]["CLK"]["net"])
    t = "clk_" + re.search(r"clk_(t\d+|c\d+)", c).group(1)
    if "u_y_x2" in f:
        t = min(("clk_t11", "clk_t10"), key=lambda n: L1(loc(f), bt[n]))
        retap[f] = t
    td.append((L1(loc(f), bt[t]), t, f))
# metrics after apply
hop1 = []; anyhop = []
for f in ffs:
    net = C[f]["pins"]["RESETN"]["net"]; pts = [loc(f)]
    for _ in range(30):
        c, m = drv(net)
        if c is None: break
        if pts and reps.get(net) and reps[net]["at"]: pts.append(reps[net]["at"])
        pts.append(loc(c))
        if m.startswith("DFF") or not (m.startswith("BUF") or m.startswith("INV")): break
        net = innet(c)
    hops = [L1(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    hop1.append(hops[0]); anyhop.append(max(hops))
td.sort()
rep = dict(relay_ffs=len(ffs), reset_chain_cells=len(lvl), reset_cells_moved=moved_rst,
           reset_first_hop_max=round(max(hop1), 1), reset_first_hop_gt405=sum(h > 405 for h in hop1),
           reset_any_hop_max=round(max(anyhop), 1), reset_any_hop_gt405=sum(h > 405 for h in anyhop),
           upstream_repeaters=len(reps), repeater_max_hop=max([r["max_hop_um"] or 1e9 for r in reps.values()], default=None),
           ties_moved=ties, tie_net_max_um=round(max(tie_len), 2) if tie_len else None,
           retap=collections.Counter(retap.values()), ff_to_tap_max=round(td[-1][0], 1), ff_to_tap_gt220=sum(t[0] > 220 for t in td),
           moved_into_macro=sum(inmac(p) for p in new.values()))
print(json.dumps(rep, default=dict))
json.dump(dict(note="DIE-S81-13 F1 joint4 apply overlay (GEOM-44 a/b/c); origins = targets for the kit legaliser; ties unfixed",
               report=rep, cells={c: dict(origin_um=p, fixed=not C[c]["master"].startswith("TIEHI")) for c, p in new.items()},
               retap=retap, reset_repeaters=list(reps.values())), open(OUT, "w"), indent=0)
