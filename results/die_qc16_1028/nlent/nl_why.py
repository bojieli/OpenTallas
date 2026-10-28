"""why nl needs 2x elongation: per sink, the trunk delay it must absorb = target - downstream; geometric delay at the
trunk rate from the entry; residual = what elongation must add.  nl vs nk on their q0 plans."""
import json, sys, statistics as st
RATE = 0.274   # ps/um TT die tree rate (est_early.py); the trunk stage table is similar
for tag, tj, cl in (("nl", sys.argv[1], sys.argv[2]), ("nk", sys.argv[3], sys.argv[4])):
    t = json.load(open(tj)); s = t["summary"]; ex, ey = s["entry"]
    c = json.load(open(cl))
    ncl = {k["name"]: k["n"] for k in c["clusters"]}
    rows = []
    for k in t["sinks"]:
        d = abs(k["p"][0] - ex) + abs(k["p"][1] - ey)
        rows.append((k["kind"], d, ncl.get(k["name"], 0), k["name"]))
    ch = [r[1] for r in rows if r[0] == "child"]; clu = [r[1] for r in rows if r[0] == "cluster"]
    print(tag, "entry", (ex, ey), "sinks", len(rows), "children", len(ch), "clusters", len(clu),
          "elong %.0f legs %d wire %.0f" % (s["elongation_um"], s["elongated_legs"], s["trunk_wire_um"]))
    print("  child dist from entry min/med/max %.0f/%.0f/%.0f" % (min(ch), st.median(ch), max(ch)) if ch else "")
    print("  cluster dist min/med/max %.0f/%.0f/%.0f" % (min(clu), st.median(clu), max(clu)))
    small = [r for r in rows if r[0] == "cluster" and r[2] <= 3]
    print("  clusters with <=3 regs:", len(small), "dist", sorted(round(r[1]) for r in small))
    # child 250 vs cluster local ~110 TT: the cluster legs must be ~140 ps longer than child legs at equal distance
    near_cl = sum(1 for d in clu if d < (max(ch) if ch else 0))
    print("  clusters nearer than the farthest child:", near_cl)
