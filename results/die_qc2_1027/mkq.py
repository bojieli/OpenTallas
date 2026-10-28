"""DIE-QC-2: quarter re-cut regions.json from the slice map: every std slice (and the W5 PHY band) splits at the
partition-row boundaries into bf / bn / centre(sl_*) / tn / tf groups (y cuts 5227, 10454, 15811, 21038 um)."""
import json, sys
p = json.load(open(sys.argv[1])); r = json.load(open(sys.argv[2]))
T = p["partition_types"]; PB = {}
for q in p["partitions"]:
    w, h = T[q["type"]]["outline_um"]; x, y = q["origin_um"]; PB[q["name"]] = (x, y, x + w, y + h)
G = ["q0bf", "q1bn", "q2c", "q3tn", "q4tf"]
pr = {}
for n, s in r["part_region"].items():
    if s.startswith("std_bg") or s == "hard_io_serdes_2":
        if not (n.startswith("c_") or n.startswith("sl_")):
            pr[n] = s; continue
        yc = (PB[n][1] + PB[n][3]) / 2
        g = 0 if yc < 5227 else 1 if yc < 10454 else 2 if yc < 15811 else 3 if yc < 21038 else 4
        pr[n] = s + "_" + G[g]
    else:
        pr[n] = s
cls = {}
for n, c in r["part_class"].items():
    cls[n] = c
rp = {}
for n, s in pr.items():
    rp[s] = rp.get(s, 0) + 1
json.dump(dict(part_region=pr, part_class=cls, region_parts=rp, note="DIE-QC-2 quarter re-cut of " + sys.argv[2]),
          open(sys.argv[3], "w"), indent=0)
print(len(rp), "regions", sorted(rp.items())[:8])
