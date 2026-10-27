"""INFRA-FIRST-QC-R15 PLAN-DELTA (COORD ruling R13 ASK-1): 17.28-um die-level centre clock channel at the y = YC seam.
Rule: die height + 17.28 (3042 x 8.64, keeps the VSS phase and the mirror: new centre YC + 8.64 = 1521 x 8.64);
every partition / channel whose origin y >= YC moves up 17.28; a channel straddling YC grows by 17.28; coll_f5 (west
strip, straddles YC, x < 1563.84) stays (17.28-um strip gap above it -> decap); new channel [1563.84, YC, W, YC + 17.28]
holds the centre x-tree (131 groups) with NO partition host.  UNCHECKED."""
import json, sys, copy
src, out = sys.argv[1], sys.argv[2]
p = json.load(open(src)); q = copy.deepcopy(p)
D = 17.28; W, H = p["die"]["outline_um"]; YC = H / 2
q["die"]["outline_um"] = [W, round(H + D, 4)]
moved, grown, kept = [], [], []
for r in q["partitions"]:
    if r["origin_um"][1] >= YC - 1e-6:
        r["origin_um"] = [r["origin_um"][0], round(r["origin_um"][1] + D, 4)]; moved.append(r["name"])
    elif r["origin_um"][1] + q["partition_types"][r["type"]]["outline_um"][1] > YC + 1e-6:
        kept.append(r["name"])
for c in q["die"]["channels"]:
    x0, y0, x1, y1 = c["rect_um"]
    if y0 >= YC - 1e-6:
        c["rect_um"] = [x0, round(y0 + D, 4), x1, round(y1 + D, 4)]
    elif y1 > YC + 1e-6:
        c["rect_um"] = [x0, y0, x1, round(y1 + D, 4)]; grown.append(c["rect_um"])
q["die"]["channels"].append(dict(rect_um=[1563.84, round(YC, 4), W, round(YC + D, 4)],
    reason="INFRA-FIRST-QC-R15 centre clock channel (COORD R13 ASK-1): die-level centre x-tree of the periodic QC top tree (one non-periodic part), no partition host; VSS lanes YC, YC+8.64, YC+17.28"))
# ports across the YC seam no longer abut: one declared channel crossing per partition pair (width 17.28, pin layers
# kept, <= M7), the 12.2a landed-crossing form (check.py abutment: faces one channel width apart)
rect = {r["name"]: r for r in q["partitions"]}
def ry(n):
    r = rect[n]; h = q["partition_types"][r["type"]]["outline_um"][1]; return r["origin_um"][1], r["origin_um"][1] + h
pairs = {}
for pr in q["ports"]:
    a, b = pr["src"].get("part"), pr["dst"].get("part")
    if a not in rect or b not in rect:
        continue
    (a0, a1), (b0, b1) = ry(a), ry(b)
    if abs(b0 - a1 - D) < 1e-6 or abs(a0 - b1 - D) < 1e-6:   # faces opened by the delta (YC seam + strip gap above coll_f5)
        k = tuple(sorted((a, b)))
        e = pairs.setdefault(k, dict(name=f"qc_r15_cc_{k[0]}__{k[1]}", between=list(k), width_um=D, layers=set(), ports=[],
                                     reason="INFRA-FIRST-QC-R15 centre clock channel crossing (seam ports, landed)"))
        e["ports"].append(pr["id"]); e["layers"] |= set(pr.get("layers", []))
for e in pairs.values():
    e["layers"] = sorted(e["layers"]) or ["M4", "M5", "M6", "M7"]   # ports carry no layer field: signal layers <= M7
    q["die"]["channels"].append(e)
q.setdefault("note", "")
if len(sys.argv) > 4:      # die_io sidecar: windows over moved partitions move with them
    io = json.load(open(sys.argv[3]))
    mv = set(moved)
    for w in io:
        if w.get("part") in mv:
            x0, y0, x1, y1 = w["rect_um"]; w["rect_um"] = [x0, round(y0 + D, 4), x1, round(y1 + D, 4)]
    json.dump(io, open(sys.argv[4], "w"), indent=1)
json.dump(q, open(out, "w"), indent=1)
json.dump(dict(delta="QC-R15-CENTRE-CHANNEL", dy_um=D, die_old=[W, H], die_new=q["die"]["outline_um"], partitions_moved=len(moved),
               straddling_kept=kept, channels_grown=grown, new_channel=[1563.84, round(YC, 4), W, round(YC + D, 4)], crossing_pairs=len(pairs), crossing_ports=sum(len(e["ports"]) for e in pairs.values()), label="UNCHECKED"),
          open(out.replace(".json", "_summary.json"), "w"), indent=1)
print(open(out.replace(".json", "_summary.json")).read())
