import os,odb
def shapes(p,name):
    db=odb.dbDatabase.create();odb.read_db(db,p);b=db.getChip().getBlock();n=b.findNet(name);out=set()
    w=n.getWire();it=odb.dbWirePathItr();it.begin(w);pp=odb.dbWirePath();s=odb.dbWirePathShape()
    while it.getNextPath(pp):
        while it.getNextShape(s):
            sh=s.shape;L=sh.getTechLayer().getName() if not sh.isVia() else ('VIA:'+(sh.getTechVia().getName() if sh.getTechVia() else 'blk'))
            out.add((L,sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax()))
    return out
a=shapes(os.environ['SRC'],os.environ['NET']);b=shapes(os.environ['ODB'],os.environ['NET'])
print('only_src',sorted(a-b));print('only_new',sorted(b-a));print('common',len(a&b))
