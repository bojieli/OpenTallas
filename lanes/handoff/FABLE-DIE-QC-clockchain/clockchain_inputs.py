#!/usr/bin/env python3
"""FABLE-DIE-QC 11-17: QC die clock-chain inputs for a plan (region map + comb feed + DME region lists).
The die clock of record is the M4 tree (comb feed, 313 regions).  A later plan event keeps regions and feed; only the
partition -> region map can need new rows (a partition split adds partition names).  This tool
  (1) checks the base map / feed / region lists against the plan (every clocked partition mapped, every region in the feed,
      DME lists inside the region set),
  (2) maps a partition missing from the map to the region whose box (union of its mapped partitions) holds the
      partition centre; none or more than one -> error unless --assign PART=REGION is given,
  (3) writes OUT/maps/regions_s3d.json and copies feed + lists so the chain script runs unchanged with MB=OUT.
usage: clockchain_inputs.py PLAN.json BASE_DIR OUT_DIR [--assign PART=REGION ...]   (BASE_DIR has maps/ and m/)"""
import json, sys, shutil, os, argparse
ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("base"); ap.add_argument("out"); ap.add_argument("--assign", action="append", default=[])
a = ap.parse_args()
P = json.load(open(a.plan)); T = P["partition_types"]
M = json.load(open(a.base + "/maps/regions_s3d.json"))["part_region"]; F = json.load(open(a.base + "/m/feed_comb_fw_3.json"))
rd = lambda n: open(f"{a.base}/maps/{n}").read().strip().split(",")
C, SU, OTH = rd("c_regions.txt"), rd("su_regions.txt"), rd("early_other_regions.txt")
parts = {p["name"]: p for p in P["partitions"]}
def bx(p):
    w, h = T[p["type"]]["outline_um"]; x, y = p["origin_um"]; return (x, y, x + w, y + h)
box = {}
for n, r in M.items():
    if n in parts:
        b = bx(parts[n]); o = box.get(r); box[r] = b if o is None else (min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3]))
force = dict(x.split("=") for x in a.assign); new = {}; err = []
for n, p in parts.items():
    if n in M: continue
    if n in force: new[n] = force[n]; continue
    b = bx(p); c = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    hit = [r for r, q in box.items() if q[0] <= c[0] <= q[2] and q[1] <= c[1] <= q[3]]
    if len(hit) == 1: new[n] = hit[0]
    else: err.append((n, p["type"], hit))
gone = sorted(set(M) - set(parts)); M2 = {n: r for n, r in M.items() if n in parts}; M2.update(new)
regs = set(M2.values()); e2 = []
if regs != set(F["parent"]): e2.append(("map regions != feed regions", sorted(regs ^ set(F["parent"]))[:8]))
if not set(C + SU + OTH) <= regs: e2.append(("DME list region not in map", sorted(set(C + SU + OTH) - regs)[:8]))
print(json.dumps(dict(plan_parts=len(parts), base_map=len(M), new=new, dropped=gone, unresolved=err, errors=e2, regions=len(regs)), indent=1))
if err or e2: sys.exit(2)
os.makedirs(a.out + "/maps", exist_ok=True); os.makedirs(a.out + "/m", exist_ok=True)
for n in os.listdir(a.base + "/maps"):
    if n != "regions_s3d.json": shutil.copy2(f"{a.base}/maps/{n}", f"{a.out}/maps/{n}")
shutil.copy2(a.base + "/m/feed_comb_fw_3.json", a.out + "/m/feed_comb_fw_3.json")
json.dump({"part_region": M2}, open(a.out + "/maps/regions_s3d.json", "w"), indent=0)
