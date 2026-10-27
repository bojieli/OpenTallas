#!/usr/bin/env python3
"""CLOCK-KV-R25: qkd_kvs_pc island set made MX-symmetric so the fMX view is the exact MX image of R0 (one GDS).

    kvs_pc_sym.py PLAN_DIR(pd25) PLAN(hm_r25.json) MESH_IN(m24c) MESH_OUT(m25c) TOOLS

The two mesh-driver ideal points of every kvs_pc instance sit at v = 86.4 and v = 276.48 = H - 86.4 (core frame,
exactly symmetric).  canon_pushdown.py put both groups on the row ABOVE the point; the rule here is 'the row on the
core-centre side of the ideal point' (symmetric by construction): lower group stays [86.4, 86.67], upper group moves
one row down to [276.21, 276.48] (both touch their ideal point).  Moves: 248 cells x 0.27 um in y, inside the core
(no partition hole, no halo outside the core changes).  Updates: plan clock.mesh.core_islands.qkd_kvs_pc, the sites
file (die xy of the moved cells) + its sha, place.json of the mesh build, the kvs_pc pin views (R0 ports k1 row,
fMX = exact MX image of R0 incl. island_ft arcs).
"""
import json, sys, hashlib, copy
from pathlib import Path
sys.path.insert(0, sys.argv[5])
import schema as S
import die_clock_mesh as DCM

pd, plan, mi, mo = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
MOD, H, ROW = "qkd_kvs_pc", 362.88, 0.27
raw = json.loads(plan.read_text())
r2 = copy.deepcopy(raw); r2.pop("plan_deltas", None)
P = S.Plan(r2)
M = json.loads((mi / "mesh.json").read_text()); C = json.loads((mi / "place.json").read_text())
moved = {}
for r in M["pushdown"]:
    part, inst = r["core"].split("/", 1)
    core = next(c for c in P.ptype(part)["hard_cores"] if c["inst"] == inst)
    if core["module"] != MOD:
        continue
    names = [k for k in C if k.startswith(r["name"] + "_") and k[len(r["name"]) + 1:].isdigit()]
    for n in names:
        c = C[n]; w = DCM.cell_width(c)
        a = DCM.core_frame(P, part, core, (c["x"], c["y"])); b = DCM.core_frame(P, part, core, (c["x"] + w, c["y"] + ROW))
        u0, v0 = min(a[0], b[0]), min(a[1], b[1])
        if abs(v0 - 276.48) < 1e-3:
            p = DCM.core_frame(P, part, core, (u0, 276.21), inverse=True)
            q = DCM.core_frame(P, part, core, (u0 + w, 276.48), inverse=True)
            nx, ny = round(min(p[0], q[0]), 4), round(min(p[1], q[1]), 4)
            moved[n] = (c["x"], c["y"], nx, ny)
            c["x"], c["y"] = nx, ny
print("moved", len(moved), "max |dx|", max(abs(v[2] - v[0]) for v in moved.values()), "dy set", sorted({round(v[3] - v[1], 4) for v in moved.values()}))
ov = DCM.placement_overlaps(C)
assert not ov, ov[:3]
mo.mkdir(exist_ok=True)
for f in mi.iterdir():
    if f.name not in ("place.json", "mesh.json"):
        (mo / f.name).write_bytes(f.read_bytes())
for w_ in M.get("island_windows", []):
    pass
M["island_windows"] = [w_ for w_ in M["island_windows"]]
# rewrite windows of moved groups: shift each window that contains a moved cell's old body
for i, w_ in enumerate(M["island_windows"]):
    for n, (x0, y0, x1, y1) in moved.items():
        if w_[0] <= x0 <= w_[2] and w_[1] <= y0 <= w_[3]:
            dy = y1 - y0
            M["island_windows"][i] = [w_[0], round(w_[1] + dy, 4), w_[2], round(w_[3] + dy, 4), w_[4]]
            break
M["meta"]["kvs_pc_sym_r25"] = dict(cells=len(moved), rule="row on the core-centre side of the ideal point (MX-symmetric)")
(mo / "place.json").write_text(json.dumps(C) + "\n"); (mo / "mesh.json").write_text(json.dumps(M) + "\n")
# sites file
sf = pd / raw["clock"]["mesh"]["sites_file"]
SF = json.loads(sf.read_text())
k = 0
for s in SF["sites"]:
    if s[0] in moved:
        s[2], s[3] = moved[s[0]][2], moved[s[0]][3]; k += 1
assert k == len(moved), (k, len(moved))
nsf = sf.with_name("clock_mesh_sites_r25.json")
nsf.write_text(json.dumps(SF) + "\n")
ci = raw["clock"]["mesh"]["core_islands"][MOD]
ci["rects_um"] = sorted([[a, 276.21, c, 276.48] if abs(b - 276.48) < 1e-6 else [a, b, c, d] for a, b, c, d in ci["rects_um"]])
raw["clock"]["mesh"].update(sites_file=nsf.name, sites_sha256=hashlib.sha256(nsf.read_bytes()).hexdigest())
# pin views
R0f = pd / "cores/qkd_kvs_pc_pins_r25.json"; MXf = pd / "cores/qkd_kvs_pc_pins_fMX_r25.json"
R0 = json.loads(R0f.read_text())
for p in R0["pins"]:
    if p["name"] in ("ft_ck_i_1", "ft_ck_o_1"):
        p["y"] = round(276.21 + ROW / 2, 4)
for a in R0["island_ft"]["arcs"]:
    if abs(a["rect_um"][1] - 276.48) < 1e-6:
        a["rect_um"] = [a["rect_um"][0], 276.21, a["rect_um"][2], 276.48]
R0["island_ft"]["symmetry"] = "MX-symmetric island set (CLOCK-KV-R25 kvs_pc_sym): fMX view = exact MX image"
MX = json.loads(MXf.read_text())
MX["pins"] = [dict(p, y=round(H - p["y"], 4)) for p in R0["pins"]]
MX["island_ft"] = copy.deepcopy(R0["island_ft"])
for a in MX["island_ft"]["arcs"]:
    r = a["rect_um"]; a["rect_um"] = [r[0], round(H - r[3], 4), r[2], round(H - r[1], 4)]
MX["source"] += " | CLOCK-KV-R25 kvs_pc_sym: exact MX image of qkd_kvs_pc_pins_r25.json (incl. island ft ports)"
R0f.write_text(json.dumps(R0, indent=1) + "\n"); MXf.write_text(json.dumps(MX, indent=1) + "\n")
plan.write_text(json.dumps(raw, indent=1) + "\n")
print("plan", hashlib.sha256(plan.read_bytes()).hexdigest(), "sites", raw["clock"]["mesh"]["sites_sha256"])
