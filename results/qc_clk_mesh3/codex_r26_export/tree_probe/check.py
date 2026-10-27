import odb,json
D=odb.dbDatabase.create();odb.read_db(D,'/w/encoded.odb');b=D.getChip().getBlock();u=b.getDbUnitsPerMicron()
n=b.findNet('ckm_w_ckt_0_0');w=n.getWire();assert w is not None
pins=sorted(it.getInst().getName()+'/'+it.getMTerm().getName() for it in n.getITerms())
assert pins==['ckt_0_0/Y','ckt_0_1/Y','ckt_1_0/A','ckt_1_1/A','ckt_3_0/A'],pins
itr=odb.dbWirePathItr();itr.begin(w);pa=odb.dbWirePath();ps=odb.dbWirePathShape();widths=set();shapes=0
while itr.getNextPath(pa):
    while itr.getNextShape(ps):
        sh=ps.shape;shapes+=1
        if not sh.isVia() and sh.getTechLayer().getName() in ('M8','M9'):
            widths.add(round(min(sh.getDX(),sh.getDY())/u,4))
assert 0.16 in widths and 0.32 in widths,widths
r=dict(verdict='PASS',pins=pins,widths=sorted(widths),shapes=shapes)
open('/w/result.json','w').write(json.dumps(r,indent=1));print('V2_ODB_READBACK',json.dumps(r))
