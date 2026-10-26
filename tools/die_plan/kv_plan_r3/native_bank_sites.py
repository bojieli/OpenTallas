#!/usr/bin/env python3
"""Resolve and allocate actual kept landing banks on one combined KV plan.

Only authoritative native->plan->hard-core pin mappings are accepted. A soft
consumer without a fixed physical point remains UNRESOLVED. Allocated stage
IDs preserve the actual emitted bank depth and bit; no hidden register/cycle.
"""
import argparse,ast,copy,importlib.util,json,math,re,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tools/die_plan'),str(ROOT/'tools/die_trial'),str(ROOT/'physical/die_plan/qwen_kvsys')]
import schema as S,gen_phys as GP,plan_v31
from legal_sites import RowAllocator

def load_core_helpers():
 f=ROOT/'physical/die_plan/qwen_kvsys/cores/harden/kv_core_rtl.py';spec=importlib.util.spec_from_file_location('bank_core_rtl',f);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 source=ROOT/'physical/die_plan/qwen_kvsys/l1_cores_v31.py';tree=ast.parse(source.read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='core_of');ns={'re':re};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),ns)
 return m,ns['core_of']
K,core_of=load_core_helpers()

def md(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])

def resolve_consumer(tn,t,consumer,part,names,pins_cache,base,explicit_map):
 actual=consumer.get('actual_leaf') or names.get(part+'.'+consumer['instance'])
 if not actual:raise ValueError('missing actual bound leaf identity')
 where=explicit_map.get(actual)
 if where is None:
  where=plan_v31.assign_blocks({actual:{}}).get(actual)
 if not where:raise ValueError('canonical native-to-plan mapping absent: '+actual)
 pn,local=where
 if pn!=part:raise ValueError(f'canonical part mismatch {actual}: {pn} != {part}')
 hc_name=core_of(local);matches=[]
 for hc in t.get('hard_cores',[]):
  members,prefixes=K.members(t,hc)
  if local in members:
   rn=K.rel(local,prefixes,hc);matches.append((hc,(rn+'__' if rn else '')+consumer['port']))
  elif hc['inst']==local and hc['module']==consumer.get('module'):
   matches.append((hc,consumer['port']))
 if len(matches)!=1:raise ValueError(f'fixed hard-core member mapping count {len(matches)}: {local}')
 hc,pinbase=matches[0]
 if hc_name and hc['inst']!=hc_name:raise ValueError('canonical hard-core identity disagrees')
 file=hc.get('pins_file')
 if not file:raise ValueError('hard core has no planned pins_file')
 file=(base/file).resolve()
 if file not in pins_cache:pins_cache[file]=K.load_pins(file)
 pin=pins_cache[file].get((pinbase,int(consumer['bit'])))
 if pin is None:pin=pins_cache[file].get((pinbase,None)) if int(consumer['bit'])==0 else None
 if pin is None:raise ValueError(f'exact planned pin absent: {hc["inst"]}.{pinbase}[{consumer["bit"]}]')
 x,y=pin['x'],pin['y'];w,h=hc['outline_um'];orient=hc.get('orient','R0')
 if orient in ('MY','R180'):x=w-x
 if orient in ('MX','R180'):y=h-y
 return [x+hc['origin_um'][0],y+hc['origin_um'][1]],dict(actual=actual,canonical=local,core=hc['inst'],pin=pinbase,bit=consumer['bit'])

def target_last(source,consumers,budget,al,depth):
 us=[p[0]+p[1] for p in consumers];vs=[p[0]-p[1] for p in consumers]
 ul,uh=max(x-budget for x in us),min(x+budget for x in us);vl,vh=max(x-budget for x in vs),min(x+budget for x in vs)
 if ul>uh or vl>vh:raise ValueError('consumer fanout has no common <=403um landing diamond')
 u=min(uh,max(ul,sum(source)));v=min(vh,max(vl,source[0]-source[1]));candidates=[]
 for a,b in [(u,v),((ul+uh)/2,(vl+vh)/2),(ul,vl),(ul,vh),(uh,vl),(uh,vh)]:
  q=al.project(((a+b)/2,(a-b)/2))
  if all(md(q,p)<=budget+1e-6 for p in consumers):candidates.append(q)
 if not candidates:raise ValueError('no macro-free projected common consumer diamond')
 return min(candidates,key=lambda p:(max([md(p,source)/depth]+[md(p,q) for q in consumers]),md(p,source)))

def stage_road_diagnostic(points,boxes):
 """Necessary HV/VH obstruction check only; native hard-pin access stays separate."""
 def clear(a,b):
  x0,x1=sorted([a[0],b[0]]);y0,y1=sorted([a[1],b[1]])
  for l,bot,r,top in boxes:
   if x0==x1:
    if l<x0<r and max(y0,bot)<min(y1,top):return False
   elif y0==y1:
    if bot<y0<top and max(x0,l)<min(x1,r):return False
   else:raise ValueError('non-Manhattan road segment')
  return True
 blocked=[]
 for i,(a,b) in enumerate(zip(points,points[1:])):
  hv=(b[0],a[1]);vh=(a[0],b[1])
  if not ((clear(a,hv) and clear(hv,b)) or (clear(a,vh) and clear(vh,b))):blocked.append(i)
 return dict(verdict='FAIL' if blocked else 'NOT_RUN',hv_vh_blocked_stage_hops=blocked,scope='necessary source/stage HV/VH obstruction diagnostic only; routedlength, capacity, native HCpinaccess and833ps NOT_RUN')

def expand_clusters(manifest,proposal,raw):
 """Model-only exact consumer replication: preserve every original bank depth."""
 m=copy.deepcopy(manifest);area={};extra=0
 for r in proposal['rows']:
  info=m['types'][r['type']];bank=info['banks'].pop(r['bank']);assert bank['depth']==r['depth']
  flat=[i for g in r['groups'] for i in g];assert sorted(flat)==list(range(len(bank['consumers'])))
  for j,g in enumerate(r['groups']):
   name=r['bank'] if j==0 else r['bank']+'__rep'+str(j)
   b=copy.deepcopy(bank);b['consumers']=[bank['consumers'][i] for i in g];b['stage_ids']=[f'{name}/g_stage[{i}].u_ff' for i in range(b['depth'])];info['banks'][name]=b
  delta=bank['depth']*(len(r['groups'])-1);extra+=delta*len(info['parts']);area[r['type']]=area.get(r['type'],0)+delta
 m['total_ff']+=extra
 impact={}
 for tn,n in area.items():
  w,h=raw['partition_types'][tn]['outline_um'];impact[tn]=dict(extra_ff_per_instance=n,extra_inv_per_instance=n,mapped_cell_area_um2=n*.3645,allocated_envelope_area_um2=n*1.404*.27,partition_area_um2=w*h,delta_fill=n*.3645/(w*h),parts=m['types'][tn]['parts'])
 m['replication_model']=dict(scope='MODEL_ONLY; no RTL emission or physical qualification',baseline_ff=manifest['total_ff'],extra_ff=extra,types=impact)
 return m

def allocate(raw,manifest,names,plan_path,explicit_map):
 P=S.Plan(raw,plan_path);result=[];pin_cache={};counts={};budget=403.;cell=(1.404,.27)
 for tn,info in manifest['types'].items():
  t=P.types[tn];part=info['parts'][0];assert P.parts[part]['type']==tn
  pinmap={(bus,bit):(x,y,f) for bus,bit,l,x,y,f in GP.type_pins(P,tn)}
  boxes=list(S.placed_macro_boxes(t,halo=4.32).values())
  boxes += [tuple(r) for r in t.get('clock',{}).get('die_islands_um',[])]
  boxes += [tuple(b['rect_um']) for b in t.get('clock',{}).get('landing_contract',{}).get('bands',{}).values() if b.get('rect_um')]
  w,h=t['outline_um'];al=RowAllocator((4.32,4.32,w-4.32,h-4.32),blocked=boxes,cell_size=cell,column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
  for slot in t.get('ft_slots',[]):
   cw,ch=slot.get('bit_site_cell_um',cell)
   for stage in slot.get('bit_sites_um',[]):
    for x,y in stage:al.reserve_rectangle((x,y,x+cw,y+ch))
  for bank,entry in info['banks'].items():
   before=set(al.used);row=dict(type=tn,module=info['module'],parts=info['parts'],bank=bank,depth=entry['depth'],stage_ids=entry['stage_ids'],ff_count=entry['depth'])
   try:
    key=(entry['source_bus'],entry['source_bit'])
    if key not in pinmap:raise ValueError('actual source pin absent in combined geometry: '+str(key))
    x,y,face=pinmap[key];dx,dy={'E':(-1,0),'W':(1,0),'N':(0,-1),'S':(0,1)}[face];source=(x+dx,y+dy);ends=[];mapping=[]
    for consumer in entry['consumers']:
     point,trace=resolve_consumer(tn,t,consumer,part,names,pin_cache,Path(plan_path).parent,explicit_map);ends.append(point);mapping.append(trace)
    if not ends:raise ValueError('bank has no actual consumers')
    depth=int(entry['depth']);final=target_last(source,ends,budget,al,depth)
    if md(source,final)>depth*budget:raise ValueError('priced bank depth cannot span source/consumer reach')
    paths=[[source,(final[0],source[1]),final],[source,(source[0],final[1]),final]]
    for fraction in (.125,.25,.375,.5,.625,.75,.875):
     x=source[0]+fraction*(final[0]-source[0]);y=source[1]+fraction*(final[1]-source[1])
     paths += [[source,(x,source[1]),(x,final[1]),final],[source,(source[0],y),(final[0],y),final]]
    choices=[]
    for seg in paths:
     length=sum(md(a,b) for a,b in zip(seg,seg[1:]));targets=[]
     for j in range(depth):
      dist=length*(j+1)/depth;target=seg[0]
      for a,b in zip(seg,seg[1:]):
       step=md(a,b)
       if dist<=step+1e-8:
        frac=0 if step==0 else dist/step;target=(a[0]+frac*(b[0]-a[0]),a[1]+frac*(b[1]-a[1]));break
       dist-=step
      targets.append(al.project(target))
     estimate=max([md(a,b) for a,b in zip([source]+targets,targets)]+[md(targets[-1],p) for p in ends]);choices.append((estimate,targets))
    initial=set(al.used);failure='no legal existing-depth path'
    for estimate,targets in sorted(choices,key=lambda z:z[0]):
     al.used=set(initial);points=[]
     try:
      for target in targets:
       q,_=al.allocate(target,1,max_radius_um=12.);points.append(tuple(q[0]))
      hops=[md(a,b) for a,b in zip([source]+points,points)]+[md(points[-1],p) for p in ends]
      if max(hops)>budget+1e-6:raise ValueError(f'actual allocated conservative hop {max(hops):.3f}>403')
      break
     except ValueError as ex:failure=str(ex)
    else:raise ValueError(failure)
    row.update(status='ALLOCATED_CANDIDATE',source_xy_um=source,consumer_xy_um=ends,consumer_mapping=mapping,
      sites_ll_um=[[round(x-cell[0]/2,6),round(y-cell[1]/2,6)] for x,y in points],cell_envelope_um=list(cell),max_hop_um=max(hops),
      road_gate=stage_road_diagnostic([source]+points,list(S.placed_macro_boxes(t).values())))
   except (ValueError,KeyError,FileNotFoundError) as ex:
    al.used=before;row.update(status='UNRESOLVED',reason=str(ex))
   result.append(row)
  counts[tn]=dict(banks=len(info['banks']),ff_per_instance=sum(e['depth'] for e in info['banks'].values()))
 return dict(schema='opentallas.native_landing_bank_sites.v1',scope='ONEcombinedKVcandidate; static allocation only, no physical qualification',conservative_endpoint_budget_um=budget,actual_gate_um=405,total_emitted_ff=manifest['total_ff'],
  allocated_ff=sum(r['ff_count']*len(r['parts']) for r in result if r['status']=='ALLOCATED_CANDIDATE'),unresolved_ff=sum(r['ff_count']*len(r['parts']) for r in result if r['status']=='UNRESOLVED'),types=counts,banks=result)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan');p.add_argument('manifest');p.add_argument('names');p.add_argument('recipe');p.add_argument('--out',required=True);p.add_argument('--clusters');a=p.parse_args();r=json.load(open(a.recipe));explicit={}
 if r.get('map_file'):
  mf=(Path(a.recipe).resolve().parent/r['map_file']).resolve();explicit.update(json.load(open(mf)).get('parts',{}))
 explicit.update(r.get('map',{}).get('parts',{}));raw=json.load(open(a.plan));manifest=json.load(open(a.manifest))
 if a.clusters:manifest=expand_clusters(manifest,json.load(open(a.clusters)),raw)
 out=allocate(raw,manifest,json.load(open(a.names)),Path(a.plan),explicit)
 if a.clusters:out['replication_model']=manifest['replication_model']
 with open(a.out,'w') as f:json.dump(out,f,indent=1);f.write('\n')
 print(json.dumps({k:v for k,v in out.items() if k not in ['types','banks']}))
