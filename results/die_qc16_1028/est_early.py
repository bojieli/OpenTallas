"""DIE-QC-16 task 1 ESTIMATE: can the trial11 die tree deliver one A0 core tap per instance early by
(insertion - common) = nk 486/436.5, nl 546/491.5 (TT/FF)?  For each c_* A0 instance: tap node = the grid tap the
A0 ck pin uses now (nearest), walk its ancestors (nodes + repeaters, routed GRT arrivals of trial11), and find the
deepest ancestor whose arrival <= glue_tap_arrival - early (TT and FF).  Report the ancestor's distance to the ck pin
(the new leg must add <= the slack between that ancestor arrival and the target) and whether it is inside the
partition region."""
import json, sys, math, collections
D = "/srv/opentallas-scratch2/claude/die-qc13-1028"
EV = "/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/event/qc_k2b_phase12.json"
INS = {"qfd_tile_nk_a0c": (736.0, 639.0), "qfd_tile_nl_a0c": (796.0, 694.0)}
COM = (250.0, 202.5)
t = json.load(open(f"{D}/trial11/clock/tree.json"))
ev = json.load(open(EV))
T = ev["partition_types"]
arr = {}
for ln in open(f"{D}/c11_TT/arr_TT.txt"):
    f = ln.split()
    if f[0] in ("N", "T"):
        arr[f[1]] = (float(f[2]), float(f[3]))
par = t["parent_of"]; sites = t["sites"]
nodes = t["nodes"]
def xform(p, x, y):
    tt = T[p["type"]]; w, h = tt["outline_um"]; o = p.get("orient", "R0"); ox, oy = p["origin_um"]
    if o in ("MY", "R180"): x = w - x
    if o in ("MX", "R180"): y = h - y
    return ox + x, oy + y
parts = {p["name"]: p for p in ev["partitions"]}
taps_by_part = collections.defaultdict(list)
for tp in t["taps"]:
    taps_by_part[tp["part"]].append(tp)
rows = []
for pn, p in sorted(parts.items()):
    if not pn.startswith("c_"):
        continue
    tl = taps_by_part[pn]
    g = [arr["t_%s__%s" % (pn, x["tap"])] for x in tl if "t_%s__%s" % (pn, x["tap"]) in arr]
    gtt = sum(a for a, _ in g) / len(g); gff = sum(b for _, b in g) / len(g)
    for tp in T[p["type"]]["clock"]["taps"]:
        if tp.get("kind") != "core":
            continue
        inst = tp["name"].split(".")[0]
        mod = [h["module"] for h in T[p["type"]]["hard_cores"] if h["inst"] == inst][0]
        ett, eff = INS[mod][0] - COM[0], INS[mod][1] - COM[1]
        cx, cy = xform(p, *tp["xy"])
        near = min(tl, key=lambda x: abs(x["xy"][0] - cx) + abs(x["xy"][1] - cy))
        s = "b%d" % near["node"]
        best = None
        chain = []
        while s is not None:
            if s in arr:
                chain.append(s)
            s = par.get(s)
        # deepest ancestor meeting both corners incl. leg delay estimate (ps per um at the measured rate below)
        for s in chain:
            a = arr[s]
            x, y = sites[s]
            d = abs(x - cx) + abs(y - cy)
            if a[0] <= gtt - ett and a[1] <= gff - eff:
                best = (s, a, d); break
        rows.append(dict(part=pn, inst=inst, mod=mod[9:11], gtt=gtt, gff=gff, ett=ett, eff=eff,
                         tap_node=chain[0], tap_arr=arr[chain[0]], best=best, nchain=len(chain)))
sl_tt = [r["gtt"] - r["ett"] - r["best"][1][0] for r in rows if r["best"]]
sl_ff = [r["gff"] - r["eff"] - r["best"][1][1] for r in rows if r["best"]]
ds = [r["best"][2] for r in rows if r["best"]]
print("instances", len(rows), "with ancestor", len(ds))
print("ancestor->ck pin manhattan um: min %.0f med %.0f max %.0f" % (min(ds), sorted(ds)[len(ds)//2], max(ds)))
print("slack left for the leg TT: min %.0f med %.0f max %.0f; FF min %.0f med %.0f max %.0f" % (
    min(sl_tt), sorted(sl_tt)[len(sl_tt)//2], max(sl_tt), min(sl_ff), sorted(sl_ff)[len(sl_ff)//2], max(sl_ff)))
# TT/FF mismatch: earliness needed differs by corner; measure the tree TT/FF ratio of the chain
rat = []
for r in rows[:50]:
    a0 = r["tap_arr"]; a1 = r["best"][1]
    rat.append((a0[0] - a1[0]) / max(1e-6, a0[1] - a1[1]))
print("chain TT/FF delay ratio (tap - ancestor): med %.3f; needed ett/eff nk %.3f nl %.3f" % (
    sorted(rat)[len(rat)//2], 486/436.5, 546/491.5))
# where does the ancestor sit: own region?
import collections
own = collections.Counter()
for r in rows:
    s = r["best"][0]; x, y = sites[s]; p = parts[r["part"]]; w, h = T[p["type"]]["outline_um"]; ox, oy = p["origin_um"]
    own["in-part" if ox <= x <= ox + w and oy <= y <= oy + h else "outside"] += 1
print("ancestor location", dict(own))
json.dump(rows, open(sys.argv[1], "w"), indent=0, default=str)
# --- leg-delay calibration from the trial11 chains themselves (routed GRT arrivals, same cell/layers) ---
segs = []
for r in rows:
    s = r["tap_node"]; chain = []
    while s is not None:
        if s in arr: chain.append(s)
        s = par.get(s)
    L = 0.0; 
    for a, b in zip(chain, chain[1:]):
        L += abs(sites[a][0] - sites[b][0]) + abs(sites[a][1] - sites[b][1])
    segs.append((L, arr[chain[0]][0] - arr[chain[-1]][0], arr[chain[0]][1] - arr[chain[-1]][1]))
ktt = sum(b for _, b, _ in segs) / sum(a for a, _, _ in segs); kff = sum(c for _, _, c in segs) / sum(a for a, _, _ in segs)
print("tree ps/um (whole chains, incl. stage delay): TT %.4f FF %.4f" % (ktt, kff))
ok = 0; res = []
for r in rows:
    s = r["tap_node"]; chain = []
    while s is not None:
        if s in arr: chain.append(s)
        s = par.get(s)
    cx, cy = None, None
    p = parts[r["part"]]
    tp = [x for x in T[p["type"]]["clock"]["taps"] if x["name"] == r["inst"] + ".ck"][0]
    cx, cy = xform(p, *tp["xy"])
    pick = None
    for s in chain:
        a = arr[s]; d = abs(sites[s][0] - cx) + abs(sites[s][1] - cy)
        need_tt = r["gtt"] - r["ett"] - a[0]; need_ff = r["gff"] - r["eff"] - a[1]
        if need_tt >= ktt * d and need_ff >= kff * d:
            pick = (s, d, need_tt - ktt * d, need_ff - kff * d, need_tt, need_ff); break
    res.append(pick)
    ok += pick is not None
print("instances with a feasible ancestor (leg at tree rate fits, elongation = rest):", ok, "/", len(rows))
el = [p[2] / ktt for p in res if p]
dd = [p[1] for p in res if p]
print("ancestor->pin um min %.0f med %.0f max %.0f; extra elongation um (TT) min %.0f med %.0f max %.0f" % (
    min(dd), sorted(dd)[len(dd)//2], max(dd), min(el), sorted(el)[len(el)//2], max(el)))
ffm = [p[3] - p[2] * kff / ktt for p in res if p]
print("FF residual after TT-matched leg (ps, + = FF tap late vs target): min %.0f med %.0f max %.0f" % (
    min(ffm), sorted(ffm)[len(ffm)//2], max(ffm)))
