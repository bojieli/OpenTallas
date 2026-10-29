import sys, odb
db = odb.dbDatabase.create(); odb.read_db(db, sys.argv[1])
blk = db.getChip().getBlock(); dbu = blk.getDbUnitsPerMicron(); tech=db.getTech()
die=blk.getDieArea(); print("die um", die.dx()/dbu, die.dy()/dbu)
for ln in ["M2","M3","M4","M5"]:
    L=tech.findLayer(ln); print(ln, "dir", L.getDirection(), "w", L.getWidth()/dbu, "pitch", L.getPitch()/dbu)
for r in tech.getNonDefaultRules() if hasattr(tech,"getNonDefaultRules") else []:
    print("techNDR", r.getName())
for r in blk.getNonDefaultRules():
    print("NDR", r.getName())
area={}
for n in blk.getNets():
    if n.getSigType() not in ("POWER","GROUND"): continue
    for sw in n.getSWires():
        for b in sw.getWires():
            if b.isVia(): continue
            ln=b.getTechLayer().getName(); area[ln]=area.get(ln,0)+b.getDX()*b.getDY()/dbu/dbu
A=die.dx()*die.dy()/dbu/dbu
print({k:round(v/A*100,1) for k,v in sorted(area.items())}, "% of die area covered by PG")
for i in blk.getInsts():
    if i.getMaster().isBlock():
        b=i.getBBox(); print("macro", i.getName(), b.xMin()/dbu, b.yMin()/dbu, b.xMax()/dbu, b.yMax()/dbu, [o.getTechLayer().getName() for o in i.getMaster().getObstructions()][:8])
