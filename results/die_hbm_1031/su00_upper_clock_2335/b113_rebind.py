import sys,json
from pathlib import Path
import numpy as np
D=Path('.');sys.path[:0]=[str(Path('tools/die_plan').resolve())];import schema as S,taps as T,gen_phys as G
from fast_assign import assign
r=json.load(open(D/'candidate.json'));led={}
for tn in ['q_b113','q_b113__physical_v1']:
 t=r['partition_types'][tn];ck=t['clock'];oldcore=[p for p in ck['taps']if p.get('kind')=='core'];ck.update(tap_mode='density',tap_max_sinks=1500,tap_target_sinks=1200,tap_radius_um=220,control_sinks=True);dt=T.density_taps(S.Plan(r),tn,control=False);ck['tap_mode']='explicit';ck['taps']=[dict(name=n,xy=[x,y],kind='glue')for n,x,y,load,rad in dt]+oldcore;print(tn,'density_seed',len(dt),flush=True);table=[p for p in t['clock']['taps']if p.get('kind')!='core'];core=[p for p in t['clock']['taps']if p.get('kind')=='core'];P=S.Plan(r);ss=T.sink_sites(P,tn);sa=np.array(ss);early=[(x,y)for _,x,y,_ in S.core_taps(P,tn)];axes=G.clock_legal_axes(P,tn);moves=[]
 while len(table)<20:
  ts=[(p['name'],*p['xy'])for p in table];load,far,asg=assign(ts,ss,1500,220,220);xy=np.array([p['xy']for p in table]);dist=np.abs(sa[:,:2]-xy[np.array(asg)]).sum(1);found=False;seen=set()
  for i in np.argsort(-dist):
   if load[asg[i]]<20:continue
   p=ss[i];bucket=(round(p[0]/8.64),round(p[1]/8.64))
   if bucket in seen:continue
   seen.add(bucket)
   if len(seen)>1000:break
   try:q=S.tap_clear(t,p[0],p[1],early+[tuple(p['xy'])for p in table],strict=True,pin_snap=lambda x,y:G._snap_tap(P,x,y,pg_legal=True),legal_axes=axes)
   except ValueError:continue
   n='clk_t'+str(len(table));nl,nf,na=assign(ts+[(n,*q)],ss,1500,220,220)
   if min(nl)<=0 or max(nl)>1500 or max(nf)>220+1e-6:continue
   table.append(dict(name=n,xy=list(q),kind='glue'));moves.append(dict(name=n,xy=list(q),load=nl[-1]));found=True;break
  assert found,(tn,'no realcluster split',len(table))
 t['clock']['taps']=table+core
 final=T.explicit_taps(S.Plan(r),tn)
 led[tn]=dict(old_count=20,new_count=len(final),max_load=max(p[3]for p in final),max_radius=max(p[4]for p in final),new_density_splits=moves,verdict='PASS')
 print(tn,led[tn],flush=True)
json.dump(r,open(D/'b113_fixed_candidate.json','w'));json.dump(led,open(D/'b113_fixed_audit.json','w'),indent=2)
