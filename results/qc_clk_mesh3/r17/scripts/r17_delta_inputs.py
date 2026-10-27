#!/usr/bin/env python3
"""INFRA-FIRST-QC-R17: solver inputs for the 43.2-um centre-channel PLAN-DELTA die (COORD ruling R15 ASK (a)).
Applies the R16 delta rule (scripts/r16_plan_delta.py: every partition / channel with origin y >= YC moves up D, the
straddling channel grows, new channel [1563.84, YC, W, YC + D], 49 declared seam crossings) to the SOLVER plan
(inputs/candidate_oneqc0733.json: partition geometry, outlines and hard cores identical to the repo plan 54a1aeb5, only
the pad-only declared type splits differ), and maps the r2 fine-mesh record onto it:
  y < YC          unchanged
  y > YC          + D                      (top half: exact mirror about the new centre YC' = YC + D/2 kept)
  y == YC         driver / tree node -> YC' (the centre gap row; the solver splits it to YC' -/+ (8.64 + D/2), i.e. the
                  R15 YC -/+ 8.64 rows of each half, with --centre-split 8.64 + D/2)
                  fine M8 strap at YC -> REMOVED (the channel holds the 5 x-tree lanes; the two mesh halves stay one
                  continuous mesh through every M9 fine strap, which spans the channel)
die_tree_plan.json is not read by qc_clk_mesh3 beyond its plan hash (copied with the delta plan hash; INFO).
Usage: r17_delta_inputs.py PLAN R2 TREEPLAN OUTDIR [D]   UNCHECKED"""
import copy
import hashlib
import json
import sys
from pathlib import Path

plan_p, r2_p, tp_p, out = sys.argv[1:5]
D = float(sys.argv[5]) if len(sys.argv) > 5 else 43.2
out = Path(out)
out.mkdir(parents=True, exist_ok=True)
p = json.loads(Path(plan_p).read_text())
W, H = p["die"]["outline_um"]
YC = H / 2
q = copy.deepcopy(p)
q["die"]["outline_um"] = [W, round(H + D, 4)]
moved = kept = 0
for r in q["partitions"]:
    if r["origin_um"][1] >= YC - 1e-6:
        r["origin_um"] = [r["origin_um"][0], round(r["origin_um"][1] + D, 4)]
        moved += 1
    elif r["origin_um"][1] + q["partition_types"][r["type"]]["outline_um"][1] > YC + 1e-6:
        kept += 1
for c in q["die"]["channels"]:
    x0, y0, x1, y1 = c["rect_um"]
    if y0 >= YC - 1e-6:
        c["rect_um"] = [x0, round(y0 + D, 4), x1, round(y1 + D, 4)]
    elif y1 > YC + 1e-6:
        c["rect_um"] = [x0, y0, x1, round(y1 + D, 4)]
q["die"]["channels"].append(dict(rect_um=[1563.84, round(YC, 4), W, round(YC + D, 4)], clock_channel=True,
    reason="INFRA-FIRST-QC-R16/R17 centre clock channel (COORD R13 ASK-1, R15 (a) 43.2 um = 5 VSS lanes YC + 8.64k, k = 0..4): "
           "die-level centre x-tree of the periodic QC top tree, no partition host"))
rect = {r["name"]: r for r in q["partitions"]}


def ry(n):
    r = rect[n]
    h = q["partition_types"][r["type"]]["outline_um"][1]
    return r["origin_um"][1], r["origin_um"][1] + h


pairs = {}
for pr in q["ports"]:
    a, b = pr["src"].get("part"), pr["dst"].get("part")
    if a not in rect or b not in rect:
        continue
    (a0, a1), (b0, b1) = ry(a), ry(b)
    if abs(b0 - a1 - D) < 1e-6 or abs(a0 - b1 - D) < 1e-6:
        k = tuple(sorted((a, b)))
        e = pairs.setdefault(k, dict(name=f"qc_r16_cc_{k[0]}__{k[1]}", between=list(k), width_um=D, layers=set(), ports=[],
                                     reason="INFRA-FIRST-QC-R16 centre clock channel crossing (seam ports, landed)"))
        e["ports"].append(pr["id"])
        e["layers"] |= set(pr.get("layers", []))
for e in pairs.values():
    e["layers"] = sorted(e["layers"]) or ["M4", "M5", "M6", "M7"]
    q["die"]["channels"].append(e)
pp = out / "plan_d43.json"
pp.write_text(json.dumps(q, indent=1))
sha = hashlib.sha256(pp.read_bytes()).hexdigest()
tp = json.loads(Path(tp_p).read_text())
tp["plan_sha256"] = sha
tp["r17_note"] = "plan hash re-pointed to the 43.2 delta plan; contents NOT re-cut (qc_clk_mesh3 reads only the hash)"
(out / "tree_plan_d43.json").write_text(json.dumps(tp))


def T(y, centre):
    if y > YC + 1e-6:
        return round(y + D, 4)
    if abs(y - YC) <= 1e-6:
        return centre
    return y


r2 = json.loads(Path(r2_p).read_text())
YCn = round(YC + D / 2, 4)
s = copy.deepcopy(r2)
s["plan"] = "/w/" + str(pp)
s["tree_plan"] = "/w/" + str(out / "tree_plan_d43.json")
s["plan_sha256"] = sha
s["H"] = round(H + D, 4)
s["ys"] = [T(y, None) for y in r2["ys"] if abs(y - YC) > 1e-6]
for n in s["nodes"]:
    n["site"] = [n["site"][0], T(n["site"][1], YCn)]
for n in s.get("reps", []):
    n["site"] = [n["site"][0], T(n["site"][1], YCn)]
for t in s["taps"]:
    for k in ("tap", "entry"):
        if t.get(k):
            assert abs(t[k][1] - YC) > 1e-6, t
            t[k] = [t[k][0], T(t[k][1], None)]
s["r17_delta"] = dict(D_um=D, YC_old=YC, YC_new=YCn, H_new=s["H"], centre_strap_removed=YC, partitions_moved=moved,
                      straddling_kept=kept, crossing_pairs=len(pairs), crossing_ports=sum(len(e["ports"]) for e in pairs.values()),
                      label="UNCHECKED")
(out / "r2_plan_d43.json").write_text(json.dumps(s))
print(json.dumps(s["r17_delta"]))
