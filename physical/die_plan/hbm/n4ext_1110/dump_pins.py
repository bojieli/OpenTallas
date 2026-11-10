import odb,json,sys
db=odb.dbDatabase.create(); odb.read_db(db,sys.argv[1]); b=db.getChip().getBlock(); u=b.getDefUnits()
die=b.getDieArea(); out=[]
for t in b.getBTerms():
    for p in t.getBPins():
        for bx in p.getBoxes():
            out.append({"name":t.getName(),"layer":bx.getTechLayer().getName(),"xl":bx.xMin()/u,"yl":bx.yMin()/u,"xh":bx.xMax()/u,"yh":bx.yMax()/u,"dir":t.getIoType()})
json.dump({"die":[die.xMin()/u,die.yMin()/u,die.xMax()/u,die.yMax()/u],"pins":out},open(sys.argv[2],"w"))
print("pins",len(out))
