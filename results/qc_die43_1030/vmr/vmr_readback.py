# DIE-QC-43 VMR readback: (1) non-clock-tree M6 data shapes (layer ceiling M5 for data, M6 = clock tree only);
# (2) clock net wire fingerprint (CLOCK sigtype nets) vs the C1 DRC0 source ODB.
import os,json,hashlib,odb
def load(p):
    db=odb.dbDatabase.create();odb.read_db(db,p);return db,db.getChip().getBlock()
def wire_hash(n):
    w=n.getWire()
    if w is None: return None
    return hashlib.sha256(json.dumps([(w.getOpcode(i),w.getData(i)) for i in range(w.length())]).encode()).hexdigest()
def scan(b):
    clk={};bad=[]
    for n in b.getNets():
        st=str(n.getSigType())
        if st=='CLOCK': clk[n.getName()]=wire_hash(n)
        w=n.getWire()
        if w is None or st=='CLOCK' or n.getName().startswith('ot_ms_'): continue
        it=odb.dbWirePathItr();it.begin(w);p=odb.dbWirePath();s=odb.dbWirePathShape()
        while it.getNextPath(p):
            while it.getNextShape(s):
                sh=s.shape
                if not sh.isVia() and sh.getTechLayer().getName() in ('M6','M7','M8','M9'):
                    bad.append({'net':n.getName(),'layer':sh.getTechLayer().getName(),'rect':[sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax()]})
    return clk,bad
d0,b0=load(os.environ['SRC']);c0,bad0=scan(b0)
d1,b1=load(os.environ['ODB']);c1,bad1=scan(b1)
ch=[k for k in c0 if c1.get(k)!=c0[k]];extra=[k for k in c1 if k not in c0]
r=dict(src=os.environ['SRC'],odb=os.environ['ODB'],src_data_above_M5=len(bad0),data_above_M5=len(bad1),data_above_M5_sample=bad1[:10],
       clock_nets_src=len(c0),clock_nets=len(c1),clock_changed=len(ch),clock_changed_sample=ch[:10],clock_extra=extra[:10],
       clock_unrouted=sum(1 for v in c1.values() if v is None),
       verdict='PASS' if not bad1 and not ch and not extra else 'FAIL')
json.dump(r,open(os.environ['OUT'],'w'),indent=1);print(json.dumps(r,indent=1))
