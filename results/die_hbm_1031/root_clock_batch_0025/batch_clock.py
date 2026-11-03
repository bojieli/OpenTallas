import sys,json,time,traceback
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('tools/die_plan').resolve()))
import schema as S,taps as T,gen_phys as G
from placement_obstacles import probe_blockages
from spatial_assign import assign
r=json.load(open('input.json'));tn='root';t=r['partition_types'][tn];ck=t['clock'];ck['control_sinks']=True
boxes=S.placed_macro_boxes(t);extra=[]
for c in probe_blockages(t):
 if c['inst']not in boxes:
  x,y=c['origin_um'];w,h=c['outline_um'];extra.append([x,y,x+w,y+h])
ck['keepouts_um']=[list(q)for q in sorted(set(tuple(q)for q in ck.get('keepouts_um',[])+extra))]
core=[q for q in ck['taps']if q.get('kind')=='core'];table=[q for q in ck['taps']if q.get('kind')!='core'];assert len(table)==788
P=S.Plan(r);ss=T.sink_sites(P,tn);sa=np.asarray(ss);early=[(x,y)for _,x,y,_ in S.core_taps(P,tn)];axes=G.clock_legal_axes(P,tn);cap=int(ck.get('tap_max_sinks',1500));rad=float(ck.get('tap_radius_um',220));ledger=[]
def evaluate():return assign([(q['name'],*q['xy'])for q in table],ss,cap,rad,rad)
def metrics(load,far,asg):
 xy=np.array([q['xy']for q in table]);dist=np.abs(sa[:,:2]-xy[asg]).sum(1);bad=dist>rad+1e-6
 return (int(bad.sum()),float(np.maximum(dist-rad,0).sum()),int((load==0).sum())),dist
load,far,asg=evaluate();metric,dist=metrics(load,far,asg);print('INITIAL',len(ss),'sinks',metric,'over',int((load>cap).sum()),flush=True)
initial=dict(sink_count=len(ss),metric=metric,max_load=float(load.max()),max_radius=float(far.max()))
try:
 while metric[0]or metric[2]or np.any(load>cap):
  empty=np.where(load==0)[0]
  if not len(empty):raise RuntimeError('No dead endpoint available for uncovered demand; preserve candidate for explicit active rehome')
  j=int(empty[0]);old=list(table[j]['xy']);active=[tuple(q['xy'])for k,q in enumerate(table)if load[k]>0 and k!=j];taken=early+active
  if metric[0]:order=np.where(dist>rad+1e-6)[0][np.argsort(-dist[dist>rad+1e-6])]
  else:order=np.lexsort((-dist,-load[asg]))
  seen=set();found=False;fail=[]
  for ii in order:
   ii=int(ii)
   if not metric[0]and load[asg[ii]]<3:continue
   x,y=sa[ii,:2];bucket=(round(x/8.64),round(y/8.64))
   if bucket in seen:continue
   seen.add(bucket)
   try:q=S.tap_clear(t,x,y,taken,strict=True,pin_snap=lambda a,b:G._snap_tap(P,a,b,pg_legal=True),legal_axes=axes)
   except ValueError as e:
    if len(fail)<3:fail.append(str(e))
    continue
   if q==tuple(old):continue
   table[j]['xy']=list(q);nl,nf,na=evaluate();nm,nd=metrics(nl,nf,na)
   good=(not np.any(nl>cap))and(nl[j]>0)and(nm<metric)
   if not good:table[j]['xy']=old;continue
   ledger.append(dict(index=j,name=table[j]['name'],old=old,new=list(q),old_metric=metric,new_metric=nm,load=float(nl[j]),radius=float(nf[j]),buckets_tried=len(seen)))
   load,far,asg,metric,dist=nl,nf,na,nm,nd;found=True
   print('MOVE',len(ledger),ledger[-1],flush=True)
   ck['taps']=table+core
   if len(ledger)%16==0:
    json.dump(r,open('checkpoint_HELD.json','w'));json.dump(dict(status='HELD_INCOMPLETE',initial=initial,current_metric=metric,moves=ledger),open('checkpoint_HELD.audit.json','w'),indent=2)
   break
  if not found:raise RuntimeError(str(dict(cause='No legal improving placement from all actual occupied candidate buckets',endpoint=table[j]['name'],metric=metric,buckets=len(seen),clearance_examples=fail)))
 ck['taps']=table+core;json.dump(r,open('candidate_planning.json','w'))
 print('FROZEN_PLANNING',metric,float(load.max()),float(far.max()),flush=True)
 # Final native assignment is authoritative, independent of the planning index.
 P2=S.Plan(r);final=T.explicit_taps(P2,tn);actual=G.clock_pins(P2,tn);assert actual==[(n,x,y)for n,x,y,_,_ in final]
 union=dict(S.placed_macro_boxes(t))
 for c in probe_blockages(t):
  x,y=c['origin_um'];w,h=c['outline_um'];union.setdefault(c['inst'],(x,y,x+w,y+h))
 hits=[]
 for n,x,y in actual:
  for cn,(a,b,c,d)in union.items():
   if a-8.64+1e-8<x<c+8.64-1e-8 and b-8.64+1e-8<y<d+8.64-1e-8:hits.append([n,cn,x,y])
 assert not hits,hits[:5]
 result=dict(status='PASS_SOURCE_PLAN_CONTACT_PREP',local_count=len(final),early_count=len(core),max_load=max(z[3]for z in final),max_radius=max(z[4]for z in final),native_pin_identity=True,canonical_union_clock_halo_hits=hits,canonical_obstacles=len(union),initial=initial,moves=ledger,control_sites=T.control_pin_sinks(P2,tn),native_built_PG_CTS_START_source_views='HELD')
 json.dump(r,open('candidate_PASS.json','w'));json.dump(result,open('audit_PASS.json','w'),indent=2);print('FINAL_PASS',result['local_count'],result['max_load'],result['max_radius'],flush=True)
except Exception as e:
 ck['taps']=table+core;json.dump(r,open('candidate_FAIL.json','w'));json.dump(dict(status='FAIL_PRESERVED',cause=str(e),initial=initial,current_metric=metric,moves=ledger,traceback=traceback.format_exc()),open('audit_FAIL.json','w'),indent=2);raise
