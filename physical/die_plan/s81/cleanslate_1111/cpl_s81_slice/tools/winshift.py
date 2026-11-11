#!/usr/bin/env python3
"""CPL-S81-SLICE LP-W REDESIGN candidate: move the lepk_i0/lepk_o0 face windows (2 x 1104 b; the 1-2 b lepf/flt/lpc control windows stay beside the lnl rs_k/flt pins) of the lepw_mus pair up by DY (default
622.08 = 144 x 4.32, a multiple of every M4/M6 track pitch): dsdv_slice_lepw_mus_LP__t2 E face and its abutting
partner dsdv_slice_lepw_mus_C__t1 W face (same y ranges, so the abutment stays coincident).
usage: winshift.py PLAN_IN PLAN_OUT [DY]"""
import json
import sys

P = json.load(open(sys.argv[1]))
dy = float(sys.argv[3]) if len(sys.argv) > 3 else 622.08
moved = []
for tn, face in (("dsdv_slice_lepw_mus_LP__t2", "E"), ("dsdv_slice_lepw_mus_C__t1", "W")):
    t = P["partition_types"][tn]
    H = t["outline_um"][1]
    for b in t["buses"]:
        if b.get("face") == face and b["name"].startswith("lepk_"):
            w = b["window_um"]
            nw = [round(w[0] + dy, 3), round(w[1] + dy, 3)]
            assert nw[1] <= H - 17.28, (tn, b["name"], nw)
            b["window_um"] = nw
            moved.append((tn, face, b["name"], w, nw))
# the die-level ports between the two partitions carry the same window in the die frame
names = {(tn, m[2]) for m in moved for tn in (m[0],)}
parts = {p["name"]: p["type"] for p in (P["partitions"] if isinstance(P["partitions"], list) else P["partitions"].values())}
ports = P["ports"] if isinstance(P["ports"], list) else list(P["ports"].values())
for p in ports:
    s, d = p.get("src", {}), p.get("dst", {})
    if (parts.get(s.get("part")), s.get("bus")) in names or (parts.get(d.get("part")), d.get("bus")) in names:
        w = p["window_um"]
        p["window_um"] = [round(w[0] + dy, 3), round(w[1] + dy, 3)]
        moved.append(("port", p["id"], w, p["window_um"]))
json.dump(P, open(sys.argv[2], "w"), indent=1)
for m in moved:
    print(*m)
