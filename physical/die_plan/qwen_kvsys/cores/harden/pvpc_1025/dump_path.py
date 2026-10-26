# openroad -python: dump placement + path cells + net fanouts of named insts. env ODB OUT NAMES(comma)
import os, odb, json
db = odb.dbDatabase.create(); db = odb.read_db(db, os.environ["ODB"]); blk = db.getChip().getBlock(); u = blk.getDbUnitsPerMicron()
rows = []
for i in blk.getInsts():
    m = i.getMaster(); x, y = i.getLocation()
    n = m.getName()
    k = "macro" if m.isBlock() else ("ff" if "DFF" in n else ("buf" if n.startswith(("BUF","INV","HB","CKINV")) else ("tap" if n.startswith(("TAP","FILL","DECAP")) else "std")))
    if k == "tap": continue
    rows.append((k, i.getName(), x/u, y/u, m.getWidth()/u, m.getHeight()/u))
pins = []
for bt in blk.getBTerms():
    for bp in bt.getBPins():
        b = bp.getBBox(); pins.append((bt.getName(), (b.xMin()+b.xMax())/2/u, (b.yMin()+b.yMax())/2/u)); break
path = {}
for nm in os.environ["NAMES"].split(","):
    i = blk.findInst(nm)
    if not i: path[nm] = None; continue
    x, y = i.getLocation(); fo = {}
    for it in i.getITerms():
        if it.isOutputSignal() and it.getNet():
            n = it.getNet(); fo[it.getMTerm().getName()] = [n.getName(), len(n.getITerms())-1,
                [(t.getInst().getLocation()[0]/u, t.getInst().getLocation()[1]/u) for t in n.getITerms() if t.getInst() != i][:400]]
    path[nm] = dict(x=x/u, y=y/u, master=i.getMaster().getName(), fo=fo)
json.dump(dict(insts=rows, pins=pins, path=path), open(os.environ["OUT"], "w"))
print("dumped", len(rows), len(pins))
