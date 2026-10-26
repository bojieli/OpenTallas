# HEAD-CORE-LAT-R2/LEF die-level proof that the island holes of ot_s81hd_elem{A,B}_cvi are legal top-level sites.
# SUPERSEDED 2026-10-26 06:39 (OWNER, METHODOLOGY 12.2a1): in-core islands = PUSHDOWN (driver cells in the core netlist); cut-out macros are not used. Record only, NOT for merge.
# inside ORFS docker: VIEWS=<views dir> SPEC=<island_spec.json> OUT=<dir> openroad -python -exit island_lef_proof.py
# Die = 8 cores (elemA_cvi + elemB_cvi in R0/MX/MY/R180) on the 8.64 lattice.  Die flow emulated:
#   rows over the die -> rows cut under every macro (die flow cut_rows) -> DIE-SIDE ISLAND ROW RESTORE: rows recreated
#   inside each hole (from the abstract's hole rect transformed by the instance orientation) -> the island demand
#   (island_spec: 2+1 BUFx24, 8 BUFx4f, 2 DFFHQNx2, 2 BUFx12f) dropped at each hole centre -> detailed_placement ->
#   check_placement -> every cell must still lie inside its own hole -> die PDN (M1/M2 followpins on the rows, M8/M9
#   grid as die_plan, M2->M8 stacks) + macro M5 PG pins -> check_power_grid VDD/VSS (every island cell on the grid).
import odb, os, json
MODE = os.environ.get("MODE", "fixed")
from openroad import Design, Tech
P = "/OpenROAD-flow-scripts/flow/platforms/asap7"
V, OUT = os.environ["VIEWS"], os.environ["OUT"]
S = json.load(open(os.environ["SPEC"]))
t = Tech()
t.readLef(P + "/lef/asap7_tech_1x_201209.lef")
t.readLef(P + "/lef/asap7sc7p5t_28_R_1x_220121a.lef")
for m in ("ot_s81hd_elemA_cvi", "ot_s81hd_elemB_cvi"):
    t.readLef("%s/%s/%s.lef" % (V, m, m))
db = t.getDB()
def findm(n):
    return [m for L in db.getLibs() for m in L.getMasters() if m.getName() == n][0]
chip = odb.dbChip_create(db, db.getTech())
b = odb.dbBlock_create(chip, "island_proof")
u = b.getDbUnitsPerMicron()
D = lambda v: int(round(v * u))
def bb(i):
    z = i.getBBox()
    return odb.Rect(z.xMin(), z.yMin(), z.xMax(), z.yMax())
W, H = 1399.68, 682.56
b.setDieArea(odb.Rect(0, 0, D(W), D(H)))
b.setCoreArea(odb.Rect(0, 0, D(W), D(H)))
site = [x for L in db.getLibs() for x in L.getSites() if x.getName() == "asap7sc7p5t"][0]
sw, sh = site.getWidth(), site.getHeight()
nrow = int(D(H) // sh)
for r in range(nrow):
    odb.dbRow_create(b, "ROW_%d" % r, site, 0, r * sh, "R0" if r % 2 == 0 else "MX", "HORIZONTAL", int(D(W) // sw), sw)
vdd = odb.dbNet_create(b, "VDD"); vdd.setSpecial(); vdd.setSigType("POWER")
vss = odb.dbNet_create(b, "VSS"); vss.setSpecial(); vss.setSigType("GROUND")
orients = ["R0", "MX", "MY", "R180"]
macros = []
for k, (m, x0, pitch, y) in enumerate([("ot_s81hd_elemA_cvi", 17.28, 345.6, 17.28), ("ot_s81hd_elemB_cvi", 17.28, 302.4, 362.88)]):
    M = findm(m)
    for i, o in enumerate(orients):
        inst = odb.dbInst_create(b, M, "u_%s_%s" % (m.split("_")[2], o))
        inst.setOrient(o)
        inst.setLocation(D(x0 + i * pitch), D(y))
        inst.setPlacementStatus("FIRM")
        macros.append((inst, S["types"][m[:-1]]["hole_um"]))
# die cut_rows: remove rows under macros (bbox), then restore rows inside each hole
def cut(b, box):
    for r in list(b.getRows()):
        z = r.getBBox()
        if z.yMax() <= box.yMin() or z.yMin() >= box.yMax() or z.xMax() <= box.xMin() or z.xMin() >= box.xMax():
            continue
        nm, o, y = r.getName(), r.getOrient(), z.yMin()
        x0, x1 = z.xMin(), z.xMax()
        odb.dbRow_destroy(r)
        nl = (box.xMin() - x0) // sw
        if nl > 0:
            odb.dbRow_create(b, nm + "_L", site, x0, y, o, "HORIZONTAL", nl, sw)
        xr = x0 + -(-(box.xMax() - x0) // sw) * sw
        nr = (x1 - xr) // sw
        if nr > 0:
            odb.dbRow_create(b, nm + "_R", site, xr, y, o, "HORIZONTAL", nr, sw)
for inst, _ in macros:
    cut(b, bb(inst))
holes = []
for inst, h in macros:
    z = bb(inst); Wm, Hm = z.xMax() - z.xMin(), z.yMax() - z.yMin(); o = inst.getOrient()
    x0, y0, x1, y1 = D(h[0]), D(h[1]), D(h[2]), D(h[3])
    if o in ("MY", "R180"): x0, x1 = Wm - x1, Wm - x0
    if o in ("MX", "R180"): y0, y1 = Hm - y1, Hm - y0
    r = odb.Rect(z.xMin() + x0, z.yMin() + y0, z.xMin() + x1, z.yMin() + y1)
    holes.append((inst, r))
    n = 0
    for y in range(r.yMin(), r.yMax(), sh):
        ri = y // sh
        odb.dbRow_create(b, "ISL_%s_%d" % (inst.getName(), ri), site, r.xMin(), y, "R0" if ri % 2 == 0 else "MX", "HORIZONTAL",
                         (r.xMax() - r.xMin()) // sw, sw)
        n += 1
demand = [(d["cell"], d["n"]) for d in S["demand"]]
cells = {}
for inst, r in holes:
    cx, cy = (r.xMin() + r.xMax()) // 2, (r.yMin() + r.yMax()) // 2
    lst = []
    px, py = r.xMin(), r.yMin()
    for c, n in demand:
        for j in range(n):
            M = findm(c)
            ci = odb.dbInst_create(b, M, "isl_%s_%s_%d" % (inst.getName(), c.split("_")[0], len(lst)))
            if MODE == "dpl":
                ci.setLocation(cx, cy); ci.setPlacementStatus("PLACED")
            else:
                if px + M.getWidth() > r.xMax():
                    px, py = r.xMin(), py + 2 * sh   # every other row: keep R0 parity for the R0-only packing
                ci.setOrient("R0" if (py // sh) % 2 == 0 else "MX")
                ci.setLocation(px, py); ci.setPlacementStatus("FIRM")
                px += M.getWidth()
            lst.append(ci)
    cells[inst.getName()] = (r, lst)
d = Design(t)
log = []
ev = lambda s: log.append((s, d.evalTclString(s)))
ev("detailed_placement") if MODE == "dpl" else None
ev("check_placement -verbose")
res = {"per_instance": {}, "orients": {}}
def island_legal(r, lst):
    """site-on-row inside the hole, row orient parity, no mutual overlap."""
    rows = {row.getBBox().yMin(): row for row in b.getRows() if row.getName().startswith("ISL_")
            and r.xMin() <= row.getBBox().xMin() and row.getBBox().xMax() <= r.xMax() and r.yMin() <= row.getBBox().yMin() < r.yMax()}
    bad = []
    boxes = []
    for c in lst:
        z = bb(c); row = rows.get(z.yMin())
        if row is None or (z.xMin() - row.getBBox().xMin()) % sw or c.getOrient() != row.getOrient() or z.xMax() > r.xMax() or z.yMax() > r.yMax():
            bad.append(c.getName())
        for q in boxes:
            if z.xMin() < q.xMax() and q.xMin() < z.xMax() and z.yMin() < q.yMax() and q.yMin() < z.yMax():
                bad.append(c.getName() + "/overlap")
        boxes.append(z)
    return bad
for nm, (r, lst) in cells.items():
    ins = sum(1 for c in lst if r.xMin() <= bb(c).xMin() and bb(c).xMax() <= r.xMax() and r.yMin() <= bb(c).yMin() and bb(c).yMax() <= r.yMax())
    o = nm.split("_")[-1]
    res["per_instance"][nm] = {"hole_die_um": [r.xMin() / u, r.yMin() / u, r.xMax() / u, r.yMax() / u], "cells": len(lst), "inside_hole": ins,
                               "island_check_bad": island_legal(r, lst), "rows_in_hole": sum(1 for row in b.getRows() if row.getName().startswith("ISL_" + nm))}
for nm, v in res["per_instance"].items():
    o = nm.split("_")[-1]
    res["orients"].setdefault(o, [0, 0])
    res["orients"][o][0] += 1
    res["orients"][o][1] += int(v["inside_hole"] == v["cells"] and not v["island_check_bad"])
# PDN: die-owned island rails + die grid; macro PG pins on the same nets
pdn = """
add_global_connection -net VDD -pin_pattern {^VDD$} -power
add_global_connection -net VSS -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name top -voltage_domains CORE -pins {M9}
add_pdn_stripe -grid top -layer M1 -width 0.018 -pitch 0.54 -offset 0 -followpins
add_pdn_stripe -grid top -layer M2 -width 0.018 -pitch 0.54 -offset 0 -followpins
add_pdn_stripe -grid top -layer M8 -width 0.48 -spacing 3.84 -pitch 8.64 -offset 1.92 -extend_to_boundary
add_pdn_stripe -grid top -layer M9 -width 0.48 -spacing 3.84 -pitch 8.64 -offset 1.92 -extend_to_boundary
add_pdn_connect -grid top -layers {M1 M2}
add_pdn_connect -grid top -layers {M2 M9}
add_pdn_connect -grid top -layers {M8 M9}
define_pdn_grid -macro -default -name macro -voltage_domains CORE -halo {0 0} -grid_over_boundary
add_pdn_connect -grid macro -layers {M5 M8}
pdngen -skip_trim
"""
for ln in pdn.strip().splitlines():
    ev(ln)
for net in ("VDD", "VSS"):
    ev("check_power_grid -net %s -error_file %s/pg_%s.rpt" % (net, OUT, net))
# island rail + via stack count per hole
for nm, (r, lst) in cells.items():
    rails, vias = 0, 0
    for net in (vdd, vss):
        for swr in net.getSWires():
            for s in swr.getWires():
                z = s.getBox()
                if z.xMin() < r.xMax() and z.xMax() > r.xMin() and z.yMin() < r.yMax() and z.yMax() > r.yMin():
                    if s.isVia(): vias += 1
                    elif s.getTechLayer().getName() in ("M1", "M2"): rails += 1
    res["per_instance"][nm]["m1m2_rails_in_hole"] = rails
    res["per_instance"][nm]["pg_vias_in_hole"] = vias
odb.write_def(b, OUT + "/island_proof.def")
d.evalTclString("write_db %s/island_proof.odb" % OUT)
res["log"] = [[a, str(c)[:300]] for a, c in log]
json.dump(res, open(OUT + "/proof.json", "w"), indent=1)
print(json.dumps({k: res[k] for k in ("orients",)}))
for nm, v in res["per_instance"].items():
    print(nm, v)
