#!/usr/bin/env python3
"""DIE-HBM-5: hubsplit.py (DIE-HBM-4) with partition ORIENT applied.  hubsplit.py scans the cut in TYPE-local x and then
adds the partition origin (cut_abs_x = x0 + xc), which is right for R0/MX only.  NE_hub is MY: its local x runs die
E->W, so the reported NE cut (die 18973.44) was really at die 19327.68 and its W/E port sides were mirrored.  Fix: mirror
the hub type's x (hard_cores, contents, internal_stations, face W<->E) into the die-relative frame for MY/R180, then run
the unchanged hubsplit.py on that frame.  usage: hubsplit_o.py HUBSPLIT_PY PLAN MAP OUTDIR"""
import copy, json, runpy, sys, tempfile
hs, plan, mp, out = sys.argv[1:5]
P = json.load(open(plan)); fixed = []
for p in P["partitions"]:
    t = P["partition_types"][p["type"]]
    if not (p["name"].endswith("_hub") and not t.get("hard") and p.get("orient", "R0") in ("MY", "R180")):
        continue
    assert sum(1 for q in P["partitions"] if q["type"] == p["type"]) == 1, "mirrored type shared by several partitions"
    W = t["outline_um"][0]
    for c in t.get("hard_cores", []) + [c for c in t.get("contents", []) if c.get("origin_um") and c.get("outline_um")]:
        c["origin_um"] = [round(W - c["origin_um"][0] - c["outline_um"][0], 4), c["origin_um"][1]]
    for s in t["internal_stations"]:
        s["from_um"] = [round(W - s["from_um"][0], 4), s["from_um"][1]]
        s["to_um"] = [round(W - s["to_um"][0], 4), s["to_um"][1]]
    for q in P["ports"]:
        for e in ("src", "dst"):
            if q[e]["part"] == p["name"] and q.get("face") in ("W", "E"):
                q["face"] = {"W": "E", "E": "W"}[q["face"]]
    fixed.append(p["name"])
tf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump(P, tf); tf.close()
print("hubsplit_o: mirrored to die frame:", fixed, flush=True)
sys.argv = [hs, tf.name, mp, out]
runpy.run_path(hs, run_name="__main__")
