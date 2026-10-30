# DIE-QC-44: leaf-rule census of the 6,532 provider leaf-driver output nets in GRT TRIAL0 (read-only)
import json,sys,collections
from pathlib import Path
import odb
src,out=sys.argv[1],sys.argv[2]
d=odb.dbDatabase.create();odb.read_db(d,src);b=d.getChip().getBlock();dbu=b.getDbUnitsPerMicron()
LEAF={'CKINVDCx16_ASAP7_75t_R':'x16','CKINVDCx5p33_ASAP7_75t_R':'x5p33'}
st=collections.defaultdict(lambda: collections.Counter());rows=[];hp=collections.defaultdict(list)
for n in b.getNets():
    nm=n.getName()
    if not nm.startswith('start_provider'): continue
    drv=[t for t in n.getITerms() if t.isOutputSignal()]
    if len(drv)!=1: continue
    m=drv[0].getInst().getMaster().getName()
    if m not in LEAF: continue
    k=LEAF[m]; c=st[k]; c['nets']+=1; c['sig_'+str(n.getSigType())]+=1
    sinks=collections.Counter(t.getInst().getMaster().getName() for t in n.getITerms() if not t.isOutputSignal())
    c['sinks']+=sum(sinks.values())
    for s in sinks: c['sinkm_'+s]+=sinks[s]
    xs=[];ys=[]
    for t in n.getITerms():
        bb=t.getBBox(); xs.append((bb.xMin()+bb.xMax())/2); ys.append((bb.yMin()+bb.yMax())/2)
    h=(max(xs)-min(xs)+max(ys)-min(ys))/dbu; hp[k].append(h)
    L=sorted({g.getLayer().getName() for g in n.getGuides()})
    c['layers_'+'/'.join(L)]+=1
    hi=[l for l in L if l in ('M8','M9')]
    if hi: c['has_M8M9']+=1
    if len(rows)<20 and hi: rows.append([nm,k,round(h,2),L])
r={k:dict(v) for k,v in st.items()}
for k,v in hp.items():
    v.sort(); r[k]['hpwl_um']=dict(p50=v[len(v)//2],p90=v[int(len(v)*.9)],max=v[-1])
r['examples_M8M9']=rows
Path(out).write_text(json.dumps(r,indent=1));print(json.dumps(r,indent=1))
