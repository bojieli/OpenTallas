"""Read a placed TX DB: classify wire reach and retained regional capture hops.

ODB=... OUT=... openroad -python -exit head_tx_reach_probe.py
Advisory geometry, never a timing/signoff verdict.
"""
import os,json,re,collections
from pathlib import Path
import odb

db=odb.dbDatabase.create();odb.read_db(db,os.environ['ODB']);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
rows=[];pairs=[];classes=collections.Counter();sinks=collections.Counter()
weak=re.compile(r'^(BUF[x]?([123])(?:_|f_)|INVx[12]_|OR5x1_|DFFHQN.*x[12]_)')
for n in b.getNets():
    if n.getSigType()!='SIGNAL':continue
    ds=[t for t in n.getITerms() if t.isOutputSignal()]
    if len(ds)!=1:continue
    d=ds[0];di=d.getInst();master=di.getMaster().getName()
    ps=[];names=[]
    for t in n.getITerms():
        q=t.getBBox();ps.append(((q.xMin()+q.xMax())/2/u,(q.yMin()+q.yMax())/2/u));names.append(t.getInst().getName().replace('\\',''))
    for t in n.getBTerms():
        q=t.getBBox();ps.append(((q.xMin()+q.xMax())/2/u,(q.yMin()+q.yMax())/2/u))
    if len(ps)<2:continue
    hp=max(x for x,y in ps)-min(x for x,y in ps)+max(y for x,y in ps)-min(y for x,y in ps)
    dn=di.getName().replace('\\','')
    if 'g_ch_region.mid[' in dn:
        pairs.append(dict(driver=dn,hpwl_um=round(hp,3),loads=len(ps)-1))
    if hp>100 and weak.match(master):
        classes[master]+=1
        kind='cq' if any('g_ff.cq[' in x for x in names) else 'mid' if any('g_ch_region.mid[' in x for x in names) else 'p_d' if any('u_enc.p_d[' in x for x in names) else 'data' if any(re.search(r'u_enc.d[0-8]\[',x) for x in names) else 'comb'
        sinks[kind]+=1
        rows.append(dict(net=n.getName(),driver=dn,master=master,hpwl_um=round(hp,3),loads=len(ps)-1,kind=kind))
rows.sort(key=lambda x:x['hpwl_um'],reverse=True)
r=dict(advisory_only=True,odb=os.environ['ODB'],weak_driver_nets_gt100um=len(rows),by_driver=classes,by_sink=sinks,regional_mid_drivers=len(pairs),regional_max_hop_um=max((x['hpwl_um'] for x in pairs),default=None),regional_hops_gt20um=sum(x['hpwl_um']>20 for x in pairs),worst=rows[:20])
Path(os.environ['OUT']).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1))
