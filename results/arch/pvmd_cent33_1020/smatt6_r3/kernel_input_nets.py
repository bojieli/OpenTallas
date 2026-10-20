import odb,re,json,collections
from pathlib import Path
db=odb.dbDatabase.create();odb.read_db(db,'/work/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base/3_2_place_iop.odb');b=db.getChip().getBlock()
lane=lambda n:(re.search(r'g_madd\\?\[(\d+)\\?\]\.g_fan32\.u_m\.genblk1\.g_native7\.u_native\.',n) or [None,None])[1]
rows=[]
for n in b.getNets():
 if str(n.getSigType())!='SIGNAL':continue
 ks=collections.Counter();drv=None;outside=0
 for t in n.getITerms():
  i=t.getInst();l=lane(i.getName())
  if t.isOutputSignal():drv=(i.getName(),i.getMaster().getName(),l)
  elif l is not None:ks[l]+=1
  else:outside+=1
 if ks and (drv is None or drv[2] is None):
  rows.append(dict(net=n.getName(),driver=drv,lanes=len(ks),kernel_loads=sum(ks.values()),outside_loads=outside,dnt=n.isDoNotTouch()))
multi=[r for r in rows if r['lanes']>1]
out=dict(kernel_input_nets=len(rows),multi_lane=len(multi),max_lanes=max([r['lanes'] for r in rows] or [0]),max_kernel_loads=max([r['kernel_loads'] for r in rows] or [0]),multi_examples=sorted(multi,key=lambda r:-r['lanes'])[:15],by_driver_master=collections.Counter((r['driver'] or ['','PORT'])[1] for r in rows).most_common(10))
Path('/work/kernel_input_nets.json').write_text(json.dumps(out,indent=1));print(json.dumps(out)[:3000])
