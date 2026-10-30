import os,odb
def shapes(p,net):
    d=odb.dbDatabase.create();odb.read_db(d,p);n=d.getChip().getBlock().findNet(net);w=n.getWire();S=[]
    it=odb.dbWirePathItr();it.begin(w);pp=odb.dbWirePath();s=odb.dbWirePathShape()
    while it.getNextPath(pp):
        while it.getNextShape(s):
            sh=s.shape;L=sh.getTechVia().getName() if sh.isVia() else sh.getTechLayer().getName()
            S.append((L,sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax()))
    return sorted(S)
a=shapes(os.environ['SRC'],os.environ['NET']);
for o in os.environ['ODBS'].split(','):
    b=shapes(o,os.environ['NET']);print(o.split('/')[-7],len(a),len(b),'IDENTICAL_SHAPES' if a==b else 'DIFF %d'%len(set(a)^set(b)))
