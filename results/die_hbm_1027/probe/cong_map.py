#!/usr/bin/env python3
"""DIE-HBM-4 congestion probe reader: grt.log layer table + congestion.rpt gcells -> per layer / partition / region /
class (over a hard core [its obs_max] vs street = soft partition area outside hard cores / inter-partition gap) + top-N
gcells mapped to core or street.  usage: cong_map.py PLAN GRT_LOG CONG_RPT REGION_MAP SLIM_SPLIT_PLAN OUT.json"""
import collections, json, re, sys
P = json.load(open(sys.argv[1])); LOG = open(sys.argv[2]).read(); RPT = sys.argv[3]
MAP = json.load(open(sys.argv[4]))["part_region"]; SP = json.load(open(sys.argv[5])); OUT = sys.argv[6]
T = P["partition_types"]
def xf(o, W, H, x, y):      # partition orient (R0/MX/MY/R180) of a local point
    return {"R0": (x, y), "MX": (x, H - y), "MY": (W - x, y), "R180": (W - x, H - y)}.get(o or "R0", (x, y))
parts, cores = [], []
for p in P["partitions"]:
    t = T[p["type"]]; W, H = t["outline_um"]; ox, oy = p["origin_um"]; o = p.get("orient", "R0")
    parts.append((p["name"], ox, oy, ox + W, oy + H, bool(t.get("hard"))))
    for c in t.get("hard_cores", []):
        (cx, cy), (cw, ch) = c["origin_um"], c["outline_um"]
        a = xf(o, W, H, cx, cy); b = xf(o, W, H, cx + cw, cy + ch)
        cores.append((p["name"], c["inst"], c["module"], ox + min(a[0], b[0]), oy + min(a[1], b[1]),
                      ox + max(a[0], b[0]), oy + max(a[1], b[1]), c.get("obs_max", "?")))
# hub halves from the slim split plan (region of a point in a hub = its W/E half)
halves = []
for p in SP["partitions"]:
    if p["name"].endswith(("_hubW", "_hubE")):
        W, H = SP["partition_types"][p["type"]]["outline_um"]; ox, oy = p["origin_um"]
        halves.append((p["name"], ox, oy, ox + W, oy + H))
def where(x, y):
    pn = next((p for p in parts if p[1] <= x < p[3] and p[2] <= y < p[4]), None)
    if pn is None:
        return "gap", None, "gap"
    c = next((c for c in cores if c[0] == pn[0] and c[3] <= x < c[5] and c[4] <= y < c[6]), None)
    reg = MAP.get(pn[0])
    if reg is None:
        h = next((h for h in halves if h[1] <= x < h[3] and h[2] <= y < h[4]), None)
        reg = MAP.get(h[0]) if h else "?"
    if pn[5]:
        return pn[0], ("(hard partition)", pn[0], "hard_part"), reg
    if c:
        return pn[0], c, reg
    return pn[0], None, reg
# layer table
lay = {}
m = re.findall(r"^(M\d|Total)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", LOG, re.M)
for L, res, dem, use, mh, mv, tot in m:
    lay[L] = dict(resource=int(res), demand=int(dem), usage_pct=float(use), max_h=int(mh), max_v=int(mv), overflow=int(tot))
# gcells
g = []
cur = {}
for line in open(RPT):
    line = line.strip()
    if line.startswith("violation type"):
        cur = dict(dir=line.split(":", 1)[1].strip())
    elif line.startswith("comment"):
        mm = re.search(r"capacity:(\d+) usage:(\d+) congestion:(\d+)", line)
        if mm:
            cur.update(cap=int(mm[1]), use=int(mm[2]), cong=int(mm[3]))
    elif line.startswith("bbox"):
        mm = re.findall(r"-?\d+(?:\.\d+)?", line.split("on Layer")[0])
        x0, y0, x1, y1 = map(float, mm[:4]); cur.update(x=(x0 + x1) / 2, y=(y0 + y1) / 2, layer=line.split("on Layer")[1].strip())
        g.append(cur)
by = {k: collections.Counter() for k in ("part", "region", "class", "core_obs", "dir", "rlayer")}
rows = []
for c in g:
    pn, core, reg = where(c["x"], c["y"])
    cls = "gap" if pn == "gap" else ("hard_partition" if core and core[2] == "hard_part" else ("over_core" if core else "street"))
    v = c.get("cong", 0)
    by["part"][pn] += v; by["region"][reg] += v; by["class"][cls] += v; by["dir"][c["dir"]] += v; by["rlayer"][c["layer"]] += v
    if cls == "over_core":
        by["core_obs"][core[7]] += v
    rows.append(dict(x=round(c["x"], 1), y=round(c["y"], 1), cong=v, cap=c.get("cap"), use=c.get("use"), dir=c["dir"],
                     part=pn, region=reg, cls=cls, core=(core[1] if core else None),
                     module=(core[2] if core and cls == "over_core" else None), obs_max=(core[7] if cls == "over_core" else None)))
rows.sort(key=lambda r: -r["cong"])
tot = sum(r["cong"] for r in rows) or 1
res = dict(layers=lay, gcells=len(rows), congestion_sum=sum(r["cong"] for r in rows),
           by_class={k: dict(sum=v, pct=round(100 * v / tot, 1)) for k, v in by["class"].most_common()},
           over_core_by_obs_max=dict(by["core_obs"]), by_dir=dict(by["dir"]), by_rpt_layer=dict(by["rlayer"]),
           by_partition=by["part"].most_common(25), by_region=by["region"].most_common(25), top20=rows[:20])
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps({k: res[k] for k in ("layers", "gcells", "congestion_sum", "by_class", "over_core_by_obs_max", "by_dir")}, indent=0))
print("by_partition", res["by_partition"][:15]); print("by_region", res["by_region"][:15])
for r in rows[:20]: print(r)
