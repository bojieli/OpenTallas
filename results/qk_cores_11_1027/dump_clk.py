"""QK-CORES-11: dump clock-net sinks (+ macros, M4/M5 PG rects) of a placed core ODB. ODB=<odb> OUT=<json> CLK=<port>"""
import json, os
import odb
db = odb.dbDatabase.create(); db = odb.read_db(db, os.environ["ODB"])
b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
bt = b.findBTerm(os.environ["CLK"]); n = bt.getNet()
sinks = []
for it in n.getITerms():
    i = it.getInst(); m = i.getMaster()
    if not (it.isInputSignal() or it.getMTerm().getSigType() == "CLOCK"):
        continue
    ok, x, y = it.getAvgXY()
    if not ok:
        bb = i.getBBox(); x, y = (bb.xMin() + bb.xMax()) / 2, (bb.yMin() + bb.yMax()) / 2
    sinks.append(dict(path=f"{i.getName()}/{it.getMTerm().getName()}", master=m.getName(), macro=bool(m.isBlock()),
                      x=round(x / u, 3), y=round(y / u, 3), status=i.getPlacementStatus()))
macros = []
for i in b.getInsts():
    if i.getMaster().isBlock():
        bb = i.getBBox(); macros.append(dict(name=i.getName(), rect=[bb.xMin()/u, bb.yMin()/u, bb.xMax()/u, bb.yMax()/u]))
pg = {"M4": [], "M5": []}
for net in b.getNets():
    if not net.isSpecial() or net.getSigType() not in ("POWER", "GROUND"):
        continue
    for sw in net.getSWires():
        for w in sw.getWires():
            if w.isVia():
                continue
            l = w.getTechLayer().getName()
            if l in pg:
                pg[l].append([w.xMin()/u, w.yMin()/u, w.xMax()/u, w.yMax()/u])
pb = bt.getBBox()
json.dump(dict(clock_port=os.environ["CLK"], port_xy=[(pb.xMin()+pb.xMax())/2/u, (pb.yMin()+pb.yMax())/2/u],
               sinks=sinks, macros=macros, pg=pg, other_nets_on_port=0), open(os.environ["OUT"], "w"))
print("DUMP", len(sinks), "sinks", sum(s["macro"] for s in sinks), "macro;", {k: len(v) for k, v in pg.items()})
