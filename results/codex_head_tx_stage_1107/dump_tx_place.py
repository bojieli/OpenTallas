"""Read-only OpenROAD Python dump of a completed TX PLACE database."""
import csv
import json
import os
from pathlib import Path
import re
import odb

db=odb.dbDatabase.create()
db=odb.read_db(db,os.environ['ODB'])
b=db.getChip().getBlock()
u=b.getDbUnitsPerMicron()
out=Path(os.environ['OUTDIR'])
out.mkdir(parents=True,exist_ok=True)
targets={}
def xy(i):
    p=i.getLocation()
    return [p[0]/u,p[1]/u]
def isbuf(i):
    return bool(re.match(r'^(BUF|INV|HB)',i.getMaster().getName()))
def root_of(net):
    seen=set();chain=[]
    while net and net.getName() not in seen:
        seen.add(net.getName())
        dr=[x for x in net.getITerms() if str(x.getMTerm().getIoType())=='OUTPUT']
        if len(dr)!=1:return dict(chain=chain,terminal='port_or_multiple_driver')
        i=dr[0].getInst()
        row=dict(net=net.getName(),driver=i.getName(),master=i.getMaster().getName(),xy=xy(i),
                 direct_loads=sum(str(x.getMTerm().getIoType())=='INPUT' for x in net.getITerms()))
        chain.append(row)
        if not isbuf(i):return dict(chain=chain,terminal='native_cell')
        ins=[x for x in i.getITerms() if str(x.getMTerm().getIoType())=='INPUT']
        if len(ins)!=1:return dict(chain=chain,terminal='nonunary_buffer')
        net=ins[0].getNet()
    return dict(chain=chain,terminal='end_or_cycle')
pat=re.compile(r'u_enc\.(?:g_ch_stage\.mid\[(?:98|113|128)\]|g_la2\.g_ch_flags\.f0_mid\[[0-3]\]|g_la2\.f0v\[[0-3]\]|g_ff\.cq\[[0-3]\]\[(?:98|113|128)\]|f0\[4\])')
with (out/'placed.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['kind','name','master','x','y','w','h'])
    for i in b.getInsts():
        m=i.getMaster();n=i.getName();p=xy(i)
        kind='macro' if m.isBlock() else ('ff' if 'DFF' in m.getName() else ('buf' if isbuf(i) else 'std'))
        w.writerow([kind,n,m.getName(),*p,m.getWidth()/u,m.getHeight()/u])
        if kind=='ff' and pat.search(n.replace('\\','')):
            ds=[t for t in i.getITerms() if t.getMTerm().getName()=='D']
            row=dict(xy=p,master=m.getName())
            if len(ds)==1:
                r=root_of(ds[0].getNet());row.update(r)
                if r['chain']:
                    q=r['chain'][-1]['xy'];row['origin_manhattan_um']=abs(q[0]-p[0])+abs(q[1]-p[1])
            targets[n]=row
    for bt in b.getBTerms():
        if str(bt.getSigType())!='SIGNAL':continue
        bb=bt.getBBox()
        w.writerow(['pin',bt.getName(),'',(bb.xMin()+bb.xMax())/2/u,(bb.yMin()+bb.yMax())/2/u,0,0])
core=b.getDieArea()
(out/'targets.json').write_text(json.dumps(dict(outline_um=[core.xMin()/u,core.yMin()/u,core.xMax()/u,core.yMax()/u],targets=targets),indent=2)+'\n')
print('TX_PLACE_DUMP targets',len(targets),'out',out)
