# HEAD-CORE-LAT-R2/LEF: inside ORFS docker: ODB=... HOLE="x0 y0 x1 y1" OUT=dir openroad -python island_hole_probe.py
# SUPERSEDED 2026-10-26 06:39 (OWNER, METHODOLOGY 12.2a1): in-core islands = PUSHDOWN (driver cells in the core netlist); cut-out macros are not used. Record only, NOT for merge.
# reports what the BUILT core has inside its island hole (rows, insts, PG swires per layer/net, obstructions, pins) and
# writes write_abstract_lef -bloat_occupied_layers for island_lef.py --from-lef.
import odb, os, json
from openroad import Design, Tech
t = Tech(); d = Design(t); d.readDb(os.environ["ODB"])
b = d.getBlock(); u = b.getDbUnitsPerMicron()
h = [float(v) for v in os.environ["HOLE"].split()]
H = [round(v * u) for v in h]
ov = lambda z: z.xMin() < H[2] and z.xMax() > H[0] and z.yMin() < H[3] and z.yMax() > H[1]
R = lambda z: [z.xMin() / u, z.yMin() / u, z.xMax() / u, z.yMax() / u]
rep = {"hole": h, "rows_overlapping": [r.getName() for r in b.getRows() if ov(r.getBBox())][:10],
       "insts_overlapping": [i.getName() for i in b.getInsts() if ov(i.getBBox())][:20],
       "obstructions": [[o.getBBox().getTechLayer().getName()] + R(o.getBBox()) for o in b.getObstructions() if ov(o.getBBox())],
       "blockages": [R(x.getBBox()) for x in b.getBlockages() if ov(x.getBBox())], "swires": {}, "pins": {}}
for n in b.getNets():
    for sw in n.getSWires():
        for s in sw.getWires():
            if s.isVia() or not ov(s):
                continue
            k = "%s/%s" % (n.getName(), s.getTechLayer().getName())
            rep["swires"].setdefault(k, []).append(R(s))
for bt in b.getBTerms():
    for p in bt.getBPins():
        for bx in p.getBoxes():
            if ov(bx):
                rep["pins"][bt.getName()] = [bx.getTechLayer().getName()] + R(bx)
rep["swire_counts"] = {k: len(v) for k, v in rep["swires"].items()}
rep["swires"] = {k: v[:4] for k, v in rep["swires"].items()}
rep["die"] = R(b.getDieArea()); rep["n_bterms"] = len(b.getBTerms())
json.dump(rep, open(os.environ["OUT"] + "/hole_probe.json", "w"), indent=1)
print(json.dumps({k: rep[k] for k in ("die", "n_bterms", "rows_overlapping", "insts_overlapping", "obstructions", "blockages", "swire_counts", "pins")}))
d.evalTclString("write_abstract_lef -bloat_occupied_layers %s/abstract.lef" % os.environ["OUT"])
