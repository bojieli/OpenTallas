"""LAND-KV-2 locality study (analysis only): KV landed plan + 128-group region map vs connectivity.
regroup_lk2.py PLAN REGIONS LPO_JSON OUT_JSON
(1) baseline: cross-region ports/bits, bit-mm across; (2) horizontal top-cut scan (crossings straddling y);
(3) greedy connectivity merge of ADJACENT regions (heaviest bits first) under a region bbox span cap -> crossings vs cap."""
import json, sys, collections
plan, regf, lpof, outf = sys.argv[1:5]
P = json.load(open(plan)); pr = json.load(open(regf))["part_region"]
T = P["partition_types"]; parts = {p["name"]: p for p in P["partitions"]}
def box(n):
    p = parts[n]; w, h = T[p["type"]]["outline_um"]; x, y = p["origin_um"]
    return (x, y, x + w, y + h)
W = max(box(n)[2] for n in parts); H = max(box(n)[3] for n in parts)
ports = [(q["src"]["part"], q["dst"]["part"], q["width"], q["id"]) for q in P["ports"]]
def cen(b): return ((b[0]+b[2])/2, (b[1]+b[3])/2)
def rbox(members):
    bs = [box(n) for n in members]; return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))
def stats(reg):
    mem = collections.defaultdict(list)
    for n, r in reg.items(): mem[r].append(n)
    cr = [(a, b, w) for a, b, w, _ in ports if reg[a] != reg[b]]
    bitmm = sum(w * (abs(cen(box(a))[0]-cen(box(b))[0]) + abs(cen(box(a))[1]-cen(box(b))[1])) / 1000 for a, b, w in cr)
    allbitmm = sum(w * (abs(cen(box(a))[0]-cen(box(b))[0]) + abs(cen(box(a))[1]-cen(box(b))[1])) / 1000 for a, b, w, _ in ports)
    spans = [max(r[2]-r[0], r[3]-r[1]) for r in (rbox(m) for m in mem.values())]
    pairs = len({tuple(sorted((reg[a], reg[b]))) for a, b, _ in cr})
    return dict(regions=len(mem), cross_ports=len(cr), cross_bits=sum(w for *_, w in cr), region_pairs=pairs,
                bitmm_across=round(bitmm), bitmm_all=round(allbitmm), locality_inside=round(1 - bitmm / allbitmm, 3),
                span_max_um=round(max(spans)), span_med_um=round(sorted(spans)[len(spans)//2]))
out = dict(die_um=[W, H], baseline=stats(pr))
# (2) top-cut scan: region centre side
mem = collections.defaultdict(list)
for n, r in pr.items(): mem[r].append(n)
rc = {r: cen(rbox(m)) for r, m in mem.items()}
scan = []
for k in range(30, 71):
    y = H * k / 100
    c = [(a, b, w) for a, b, w, _ in ports if pr[a] != pr[b] and (rc[pr[a]][1] < y) != (rc[pr[b]][1] < y)]
    scan.append((round(y), len(c), sum(w for *_, w in c)))
out["hcut_scan"] = dict(at_mid=[s for s in scan if s[0] == round(H*0.5)], min=min(scan, key=lambda s: s[1]),
                        rows=scan[::2])
lp = json.load(open(lpof))["corners"]["TT_droop-regions_corelat250"]["all"]
root = [r for r in lp if r["lca"] == "b0"]
out["root_lca"] = dict(n=len(root), region_pairs=collections.Counter(
    "|".join(sorted((pr[r["src"]], pr[r["dst"]]))) for r in root).most_common(12),
    worst=min(r["margin_ps"] for r in root))
# (3) greedy adjacent merge by bits under span cap
def adjacent(r1, r2, reg):
    return True  # merges are proposed only between regions that exchange ports (link graph edges)
for cap in (2000, 2500, 3000, 3500, 4000):
    reg = dict(pr)
    while True:
        mem = collections.defaultdict(list)
        for n, r in reg.items(): mem[r].append(n)
        bw = collections.Counter()
        for a, b, w, _ in ports:
            if reg[a] != reg[b]: bw[tuple(sorted((reg[a], reg[b])))] += w
        done = False
        for (r1, r2), w in bw.most_common():
            bb = rbox(mem[r1] + mem[r2])
            if max(bb[2]-bb[0], bb[3]-bb[1]) <= cap:
                for n in mem[r2]: reg[n] = r1
                done = True; break
        if not done: break
    out[f"merge_cap{cap}"] = stats(reg)
json.dump(out, open(outf, "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "hcut_scan"}, indent=1))
print("hcut mid", out["hcut_scan"]["at_mid"], "min", out["hcut_scan"]["min"])
