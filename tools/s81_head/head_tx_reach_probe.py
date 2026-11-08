"""Read a placed TX DB: classify wire reach and retained regional capture hops.

ODB=... OUT=... openroad -python -exit head_tx_reach_probe.py
Advisory geometry, never a timing/signoff verdict.
"""
import os,json,re,collections
import csv
from pathlib import Path
import odb

db=odb.dbDatabase.create();odb.read_db(db,os.environ['ODB']);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
rows=[];pairs=[];classes=collections.Counter();sinks=collections.Counter()
regional={'mid':{},'cq':{}}
for inst in b.getInsts():
    nm=inst.getName().replace('\\','')
    m=re.match(r'^u_enc\.(g_ch_region\.mid|g_ff\.cq)\[([0-3])\]\[([0-9]+)\]',nm)
    if m:
        q=inst.getBBox();xy=((q.xMin()+q.xMax())/2/u,(q.yMin()+q.yMax())/2/u)
        regional['mid' if m[1]=='g_ch_region.mid' else 'cq'][(int(m[2]),int(m[3]))]=xy
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
distances=[abs(x-regional['cq'][key][0])+abs(y-regional['cq'][key][1]) for key,(x,y) in regional['mid'].items() if key in regional['cq']]
r=dict(advisory_only=True,odb=os.environ['ODB'],weak_driver_nets_gt100um=len(rows),by_driver=classes,by_sink=sinks,regional_mid_drivers=len(pairs),regional_max_driver_net_hpwl_um=max((x['hpwl_um'] for x in pairs),default=None),regional_driver_nets_gt20um=sum(x['hpwl_um']>20 for x in pairs),regional_paired_registers=len(distances),regional_max_pair_distance_um=round(max(distances,default=0),3),regional_pairs_gt20um=sum(x>20 for x in distances),regional_missing_pairs=len(set(regional['mid'])^set(regional['cq'])),worst=rows[:20])
Path(os.environ['OUT']).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1))
if os.environ.get('CSV'):
    with open(os.environ['CSV'],'w') as f:
        w=csv.writer(f);w.writerow(['name','master','x','y','w','h'])
        for inst in b.getInsts():
            q=inst.getBBox()
            w.writerow([inst.getName(),inst.getMaster().getName(),q.xMin()/u,q.yMin()/u,(q.xMax()-q.xMin())/u,(q.yMax()-q.yMin())/u])
        for term in b.getBTerms():
            q=term.getBBox()
            w.writerow([term.getName(),'PIN',q.xMin()/u,q.yMin()/u,(q.xMax()-q.xMin())/u,(q.yMax()-q.yMin())/u])
