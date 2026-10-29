#!/usr/bin/env python3
"""DIE-KV-31-SRC: prove the rebuilt source's actual top PG grid equals the grid exported by codex-kv-pg-0834
(grid3_bbox/pg_rects.json, M8/M9 VDD/VSS special wires), so that export is reusable under export_overlay.py.
Also reports supply ITerms per net and VDDPHY wire census. OpenROAD python; read-only."""
import argparse,json,collections
import odb
p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--pg-rects',required=True);p.add_argument('--out',required=True);a=p.parse_args()
d=odb.dbDatabase.create();odb.read_db(d,a.odb);b=d.getChip().getBlock();D=b.getDbUnitsPerMicron()
old=collections.Counter((n,ly,*[round(v*D) for v in r]) for n,ly,*r in json.load(open(a.pg_rects)))
new=collections.Counter();phy=collections.Counter();it={}
for n in ('VDD','VSS','VDDPHY'):
 net=b.findNet(n)
 if net is None:it[n]=None;continue
 mac=[(i.getInst().getName(),i.getMTerm().getName()) for i in net.getITerms() if not i.getInst().getMaster().getName().endswith('_ASAP7_75t_R')]
 it[n]=dict(total=len(net.getITerms()),macro_iterms=len(mac),macro_examples=mac[:4])
 for sw in net.getSWires():
  for s in sw.getWires():
   if s.isVia():continue
   ly=s.getTechLayer().getName()
   if ly not in('M8','M9'):continue
   if n=='VDDPHY':phy[ly]+=1
   else:new[(n,ly,s.xMin(),s.yMin(),s.xMax(),s.yMax())]+=1
r=dict(odb=a.odb,old_grid_rects=sum(old.values()),new_grid_rects=sum(new.values()),only_old=sum((old-new).values()),only_new=sum((new-old).values()),identical=old==new,vddphy_m8_m9_wires=dict(phy),supply_iterms=it)
json.dump(r,open(a.out,'w'),indent=1);print(json.dumps(r))
