"""LAND-KV-2: connectivity regroup of the KV landed region map (12.13a regions from connectivity).
regroup_map_lk2.py PLAN OLD_TABLE CAP_UM OUT_PREFIX
Greedy merge of region pairs that exchange ports, heaviest bits first, accepted only when the merged bbox span
<= CAP_UM and the merged bbox contains no part centre of a third region (convex, non-interleaved regions).
Writes OUT_PREFIX_regions.json (part_region) and OUT_PREFIX_table.json (same schema as the FALLBACK-PLAN-PREP-2
row_groups table: ports re-labelled; ports inside a merged region are dropped from the crossing list)."""
import json, sys, collections
plan, oldt, cap, pre = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
P = json.load(open(plan)); T = json.load(open(oldt))
TY = P["partition_types"]; parts = {p["name"]: p for p in P["partitions"]}
def box(n):
    p = parts[n]; w, h = TY[p["type"]]["outline_um"]; x, y = p["origin_um"]
    if p.get("orient") in ("R90", "R270", "MXR90", "MYR90"): w, h = h, w
    return (x, y, x + w, y + h)
cen = {n: ((box(n)[0] + box(n)[2]) / 2, (box(n)[1] + box(n)[3]) / 2) for n in parts}
reg = {}
for r in T["regions"]:
    for n in r["parts"]: reg[n] = r["tag"]
ports = [(q["src"]["part"], q["dst"]["part"], q["width"]) for q in P["ports"]]
def rbox(ms):
    bs = [box(n) for n in ms]; return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))
merges = []
while True:
    mem = collections.defaultdict(list)
    for n, r in reg.items(): mem[r].append(n)
    bw = collections.Counter()
    for a, b, w in ports:
        if reg[a] != reg[b]: bw[tuple(sorted((reg[a], reg[b])))] += w
    ok = None
    for (r1, r2), w in bw.most_common():
        bb = rbox(mem[r1] + mem[r2])
        if max(bb[2] - bb[0], bb[3] - bb[1]) > cap: continue
        if any(bb[0] < cen[n][0] < bb[2] and bb[1] < cen[n][1] < bb[3] for n in parts if reg[n] not in (r1, r2)): continue
        ok = (r1, r2, w); break
    if not ok: break
    r1, r2, w = ok
    keep, drop = sorted((r1, r2), key=lambda r: (-len(mem[r]), r))
    for n in mem[drop]: reg[n] = keep
    merges.append([keep, drop, w])
mem = collections.defaultdict(list)
for n, r in reg.items(): mem[r].append(n)
json.dump({"part_region": reg, "note": f"LAND-KV-2 connectivity regroup of {oldt} (cap {cap} um, convex), {len(mem)} regions"},
          open(pre + "_regions.json", "w"), indent=0)
NT = {k: v for k, v in T.items() if k not in ("regions", "ports")}
NT["regions"] = []
for k, r in enumerate(T["regions"]):
    NT["regions"].append(dict(r, tag=reg[r["parts"][0]]))
xp = []
for q in T["ports"]:
    sr, dr = reg[q["src"]], reg[q["dst"]]
    if sr != dr: xp.append(dict(q, src_region=sr, dst_region=dr))
NT["ports"] = xp; NT["regions_count"] = len(mem); NT["crossings"] = len(xp); NT["bits"] = sum(q["width"] for q in xp)
NT["note_lk2"] = dict(merges=merges, source=oldt, cap_um=cap)
json.dump(NT, open(pre + "_table.json", "w"))
spans = sorted(max(b[2] - b[0], b[3] - b[1]) for b in (rbox(m) for m in mem.values()))
print(json.dumps(dict(regions=len(mem), merges=len(merges), crossings=len(xp), bits=NT["bits"],
                      old_crossings=len(T["ports"]), span_max=round(spans[-1]), span_med=round(spans[len(spans)//2]))))
