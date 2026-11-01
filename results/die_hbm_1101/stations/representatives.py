import json,sys,numpy as np
from pathlib import Path
W=Path('/srv/opentallas-scratch2/claude/wt/codex-hbm-stations-1101')
sys.path.insert(0,str(W/'tools/die_plan'))
import schema as S
from gen_phys import type_pins
for root in sys.argv[1:]:
 r=Path(root);small=(r/'SMALL_DONE').exists() and not (r/'DONE').exists()
 src='small_repaired.json' if small else 'repaired.json';lf='small_ledger.json' if small else 'ledger.json';dest='small_representative_plan.json' if small else 'representative_plan.json'
 raw=json.load(open(r/src));p=S.Plan(raw,None);records=json.load(open(r/lf));done=[];before_inside=0
 for tn in sorted({x['type'] for x in records if x.get('status','PASS')=='PASS'}):
  t=p.types[tn];pins={(bn,i):(x,y) for bn,i,l,x,y,f in type_pins(p,tn)};boxes=list(S.placed_macro_boxes(t).values())
  for row in [x for x in records if x['type']==tn and x.get('status','PASS')=='PASS']:
   s=next(x for x in t['ft_slots'] if x['name']==row['slot']);n=s['width']+1;a=np.array([pins[(s['name']+'_i',i)] for i in range(n)]);b=np.array([pins[(s['name']+'_o',i)] for i in range(n)]);ss=np.array(s['bit_sites_um'])+np.array(s['bit_site_cell_um'])/2;old=s['regs_um']
   cost=np.maximum(abs(ss[0]-a.mean(0)).sum(1),abs(ss[-1]-b.mean(0)).sum(1))
   for q,z in zip(ss,ss[1:]):cost=np.maximum(cost,abs(q-z).sum(1))
   idx=n//2
   if cost[idx]>405+1e-6:idx=int(cost.argmin())
   assert cost[idx]<=405+1e-6,(tn,s['name'],cost.min())
   reps=[a.mean(0).round(6).tolist()]+[q[idx].round(6).tolist() for q in ss]
   bad=[j for j,q in enumerate(old) if any(x0<q[0]<x1 and y0<q[1]<y1 for x0,y0,x1,y1 in boxes)];before_inside+=len(bad)
   assert not any(any(x0<q[0]<x1 and y0<q[1]<y1 for x0,y0,x1,y1 in boxes) for q in reps)
   s['regs_um']=reps;done.append(dict(type=tn,slot=s['name'],chosen_bit=idx,old_reps_in_core=bad,representative_max_hop_um=float(cost[idx]),old_regs_um=old,new_regs_um=reps))
 with open(r/(dest+'.tmp'),'w') as f:json.dump(raw,f,separators=(',',':'))
 (r/(dest+'.tmp')).replace(r/dest);json.dump(done,open(r/'representative_ledger.json','w'),indent=2)
 print(r.name,'slots',len(done),'oldinside',before_inside,'newinside0','maxrep',max(x['representative_max_hop_um'] for x in done),flush=True)
