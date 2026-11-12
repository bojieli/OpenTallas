"""SC-REFLOOR-1 N-growth die step: every partition with origin y >= YROW moves up DY, die outline H += DY, and the die
y-coordinates at/above YROW in die-level lists (lanes waypoints, pg/clock rects, bumps) move with it.  Prints what moved.
usage: die_shift.py IN OUT DY YROW"""
import json, sys, collections
P = json.load(open(sys.argv[1])); DY = float(sys.argv[3]); Y = float(sys.argv[4])
mv = collections.Counter()
for q in P["partitions"]:
    if q["origin_um"][1] >= Y - 0.01:
        q["origin_um"][1] += DY; mv[q["type"].split("__")[0]] += 1
d = P["die"]; d["outline_um"][1] += DY
print("die outline", d["outline_um"], "moved partitions", sum(mv.values()), dict(mv))
print("die keys", sorted(d.keys())[:40]); print("top keys", sorted(P.keys()))
json.dump(P, open(sys.argv[2], "w"))
