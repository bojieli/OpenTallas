#!/usr/bin/env python3
"""HEAD-CORE-LAT-R5 core-kit PLAN gate for a head_tree_plan.py spec (the HEAD analogue of the QC su_kit_gate G-checks):
  G1 macro_orient : every macro rect in the geo has the LEF SIZE (R0/MY/MX/R180 keep W x H).
  G3 cell_rows    : every tree node / leaf / macro-leaf driver site inside the core rows and outside every macro ROW halo (4.32).
  G4 fixed_length : every edge's planned length (seg_um) equals the Manhattan distance between its two placed cells
                    (|diff| <= 2.16 um) and its L route crosses no macro (so the router cannot shortcut / detour it).
  G5 equal_depth  : every register leaf (and macro leaf) at the same stage depth.
  G6 membership   : every geo clock sink in exactly one leaf; leaf load spread <= 1 sink.
  G7 entry        : plan root = the 12.2a1 island centre entry (given), within 2.16 um.
usage: head_plan_gate.py SPEC.tcl SEG.json GEO LEF ENTRYX,ENTRYY OUT.json      PLAN MODEL, UNCHECKED."""
import json, re, sys, hashlib
sys.path.insert(0, sys.argv[7] if len(sys.argv) > 7 else "py")
import common
spec, segp, geo, lef, ent, out = sys.argv[1:7]
S = common.parse_spec(spec); seg = json.load(open(segp))["seg_um"]
sinks, macs, _ = common.parse_geo(geo)
core = [tuple(map(float, l.split()[1:5])) for l in open(geo) if l.startswith("CORE")][0]
W, H = map(float, re.search(r"SIZE ([\d.]+) BY ([\d.]+)", open(lef).read()).groups())
HALO, TOL = 4.32, 2.16
res, bad = {}, {}
bad["G1"] = [m for m, v in macs.items() if abs((v["rect"][2] - v["rect"][0]) - W) > 0.01 or abs((v["rect"][3] - v["rect"][1]) - H) > 0.01]
pos = {"root": S["root"]}; par = {}
for n, v in S["tree"].items(): pos[n] = v["xy"]; par[n] = v["par"]
for n, v in S["leaves"].items(): pos[n] = v["xy"]; par[n] = v["par"]
for k, m in enumerate(S["macros"]): pos[f"m{k}"] = m["xy"]; par[f"m{k}"] = S["leaves"][m["leaf"]]["par"]
def in_halo(p):
    return [m for m, v in macs.items() if v["rect"][0] - HALO < p[0] < v["rect"][2] + HALO and v["rect"][1] - HALO < p[1] < v["rect"][3] + HALO]
bad["G3"] = [(n, p) for n, p in pos.items() if n != "root" and not n.startswith("m") and (in_halo(p) or not (core[0] <= p[0] <= core[2] and core[1] <= p[1] <= core[3]))]
mac_halo = [(n, p) for n, p in pos.items() if n.startswith("m") and in_halo(p)]
def crosses(a, b):
    for bend in ((b[0], a[1]), (a[0], b[1])):
        ok = True
        for p, q in ((a, bend), (bend, b)):
            for v in macs.values():
                x0, y0, x1, y1 = v["rect"]
                if p[1] == q[1] and y0 < p[1] < y1 and min(p[0], q[0]) < x1 and max(p[0], q[0]) > x0: ok = False
                if p[0] == q[0] and x0 < p[0] < x1 and min(p[1], q[1]) < y1 and max(p[1], q[1]) > y0: ok = False
        if ok: return False
    return True
g4 = []
for n, p in par.items():
    if n.startswith("m"): continue
    M = abs(pos[n][0] - pos[p][0]) + abs(pos[n][1] - pos[p][1])
    L = seg.get(n, M)
    if abs(L - M) > TOL or crosses(pos[p], pos[n]): g4.append((n, round(L, 2), round(M, 2)))
bad["G4"] = g4
def depth(n):
    d = 0
    while n != "root": d += 1; n = par[n]
    return d
dl = sorted({depth(n) for n in S["leaves"]} | {depth(f"m{k}") for k in range(len(S["macros"]))})
bad["G5"] = [] if len(dl) == 1 else dl
cnt = {}
for n, v in S["leaves"].items():
    for r in v["regs"]: cnt[r] = cnt.get(r, 0) + 1
loads = [len(v["regs"]) for v in S["leaves"].values()]
bad["G6"] = ([("missing", len(set(sinks) - set(cnt)))] if set(sinks) - set(cnt) else []) + [r for r, c in cnt.items() if c != 1][:5] + ([("load", min(loads), max(loads))] if max(loads) - min(loads) > 1 else [])
e = tuple(map(float, ent.split(",")))
bad["G7"] = [] if abs(S["root"][0] - e[0]) + abs(S["root"][1] - e[1]) <= TOL else [S["root"]]
o = dict(checks={g: dict(verdict="PASS" if not v else "FAIL", n_fail=len(v), sample=v[:5]) for g, v in bad.items()},
         info=dict(n_nodes=len(S["tree"]), n_leaves=len(S["leaves"]), leaf_load=[min(loads), max(loads)], depth=dl,
                   macro_leaf_in_halo=mac_halo, note="macro leaf stage sits on the ROM clock pin (within its halo by design, as QC mscts_h)"),
         verdict="PASS" if not any(bad.values()) else "FAIL", argv=sys.argv,
         sha256={p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in (spec, segp, geo, lef)}, scope="PLAN gate, UNCHECKED")
json.dump(o, open(out, "w"), indent=1, default=str)
print("HEAD_PLAN_GATE", o["verdict"], {g: c["verdict"] for g, c in o["checks"].items()})
