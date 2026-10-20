import odb, re
from openroad import Design, Tech
import sys
db=odb.dbDatabase.create(); odb.read_db(db,'/work/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base/3_5_place_dp-failed.odb')
b=db.getChip().getBlock(); u=b.getDbUnitsPerMicron()
names=open('/work/viol.txt').read().split()
regs=[(r.getName(),[ (bx.xMin(),bx.yMin(),bx.xMax(),bx.yMax()) for bx in r.getBoundaries()]) for r in b.getRegions()]
macros=[(i.getName(),i.getBBox()) for i in b.getInsts() if i.getMaster().isBlock()]
print('macros',[(n,bb.xMin()/u,bb.yMin()/u,bb.xMax()/u,bb.yMax()/u) for n,bb in macros])
print('regions',len(regs))
of=set(open('/work/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base/ot_out_flop_at_pins.txt').read().split())
rows=b.getRows(); r0=rows[0]; print('row0',r0.getOrigin(), r0.getSite().getWidth(), r0.getSite().getHeight())
tall=[i.getName() for i in b.getInsts() if i.getMaster().getHeight()>2000 and not i.getMaster().isBlock()]
print('tall non-block',tall[:5])
for n in names:
  i=b.findInst(n)
  if not i: print('NF',n); continue
  bb=i.getBBox(); x,y=bb.xMin(),bb.yMin()
  inr=[rn for rn,bs in regs for (a,c,d,e) in bs if a<=x<d and c<=y<e]
  near=[mn for mn,mb in macros if mb.xMin()-2000<=x<=mb.xMax()+2000 and mb.yMin()-2000<=y<=mb.yMax()+2000]
  print('%-50s %-22s %8.3f %8.3f st=%s reg=%s grp=%s of=%d near=%s'%(n,i.getMaster().getName(),x/u,y/u,i.getPlacementStatus(),inr, i.getGroup().getName() if i.getGroup() else None, n in of, near))
