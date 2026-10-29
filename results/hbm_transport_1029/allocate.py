#!/usr/bin/env python3
"""Allocate actual FF sites after transport.py; preserve and report failed plans.
No physical route/STA. Every new site is a complete 1.404x.27um legal footprint.
"""
import argparse,collections,copy,hashlib,json,math,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('geometry');ap.add_argument('out');ap.add_argument('--tools',required=True);ap.add_argument('--keep-going',action='store_true',help='retain completed parts and diagnose independent failures');ap.add_argument('--parts',help='comma-separated independent instance subset');ap.add_argument('--max-extra-stations',type=int,default=8);a=ap.parse_args();sys.path.insert(0,a.tools);sys.path.insert(0,str(Path(a.tools).parents[1]))
import schema as S
import ft_corridor as F
import hub_repack as HR
import geometry_identity
import turn_corridor
turn_corridor.install(F)
from tools.die_trial.legal_sites import RowAllocator
src=Path(a.geometry);out=Path(a.out);out.mkdir(parents=True,exist_ok=False);P=json.loads((src/'die_plan.json').read_text());report=json.loads((src/'report.json').read_text());report['status']='ALLOCATING';report['allocation_failures']=[];report['clock_ff_load']={};model=S.Plan(P);parts=model.parts;selected=set(a.parts.split(',')) if a.parts else set(report['changed_types']);report['completed_parts']=[];report['wrapper_transport_ff']={};report['part_failures']=[];report['geometry_sha256']={pn:geometry_identity.identity(P,pn) for pn in selected}
# All PHY supply domains are physical keepouts, including digital-core side strips.
extra=collections.defaultdict(list)
for dom in P['die'].get('pg',{}).get('domains',[]):
 rr=dom.get('rect_um')
 if not rr:continue
 for pn,pr in parts.items():
  A=model.rect(pn);x0,y0,x1,y1=max(A[0],rr[0]),max(A[1],rr[1]),min(A[2],rr[2]),min(A[3],rr[3])
  if x1>x0 and y1>y0:
   xy=[model.to_type(pn,q) for q in ((x0,y0),(x1,y1))];extra[pr['type']].append((min(q[0] for q in xy),min(q[1] for q in xy),max(q[0] for q in xy),max(q[1] for q in xy)))
orig_boxes=S.placed_macro_boxes
def boxes(t,halo=0):
 d=dict(orig_boxes(t,halo=halo));tn=next((n for n,ty in P['partition_types'].items() if ty is t),None)
 for i,r in enumerate(extra.get(tn,[])):d['PHYPG'+str(i)]=r
 return d
S.placed_macro_boxes=boxes
orig_build=F.build_path
def sameface(fin,fout,ca,cb,w,h,jog=None):
 if fin!=fout:return orig_build(fin,fout,ca,cb,w,h,jog)
 import numpy as np
 ca,cb=np.asarray(ca,float),np.asarray(cb,float)
 if fin in 'EW':x=w/2 if jog is None else jog;return [ca,np.array([x,ca[1]]),np.array([x,cb[1]]),cb]
 y=h/2 if jog is None else jog;return [ca,np.array([ca[0],y]),np.array([cb[0],y]),cb]
F.build_path=sameface
try:
 for pn,info in sorted(report['changed_types'].items()):
  if pn not in selected:continue
  original_type=copy.deepcopy(P['partition_types'][parts[pn]['type']])
  try:
   tn=parts[pn]['type'];t=P['partition_types'][tn];W,H=t['outline_um'];fixed=[]
   # Moving a face window moves an existing core/face chain endpoint. Retain all
   # original registers when a legal same-depth chain exists; price every increase.
   hc=boxes(t,halo=0);R=HR.Raster(W,H,list(hc.values()));mm=S.Plan(P)
   for st in t.get('internal_stations',[]):
    bn=st.get('conn','')[4:] if st.get('conn','').startswith('bus:') else None
    if bn not in info['buses']:continue
    geom=mm._type_geom(pn,bn)
    if not geom:raise RuntimeError(f'no face geometry {pn}/{bn}')
    face,win,_,_=geom;q=sum(win)/2;pt={'W':[0,q],'E':[W,q],'S':[q,0],'N':[q,H]}[face];oldpt=st['from_um'];st['from_um']=pt;nold=len(st.get('regs_um',[]));rch=HR.route_station(R,pt,st['to_um'],nold,405.)
    if rch is None:raise RuntimeError(f'no internal endpoint route {pn}/{st["conn"]}')
    st['regs_um']=[list(q) for q in rch['regs']];report['internal'].append(dict(part=pn,conn=st['conn'],old_endpoint=oldpt,new_endpoint=pt,old_regs=nold,new_regs=len(st['regs_um']),added=len(st['regs_um'])-nold))
   for c in t.get('channels',[]):
    if 'boot' in c.get('reason','').lower():fixed.append(c['rect_um'])
   # Existing internal pipeline banks lack actual bit sites in this plan. Reserve
   # conservative <=60%-fill bank envelopes, rather than silently overlap them.
   for st in t.get('internal_stations',[]):
    side=max(2.16,math.sqrt((st.get('bits',1)+1)*1.404*.27/.6))
    for x,y in st.get('regs_um',[]):fixed.append([x-side/2,y-side/2,x+side/2,y+side/2])
   for tp in t.get('clock',{}).get('taps',[]):
    if tp.get('kind')!='core' and 'xy' in tp:
     x,y=tp['xy'];fixed.append([x-4.32,y-4.32,x+4.32,y+4.32])
   if 'tap_um' in t.get('clock',{}):
    x,y=t['clock']['tap_um'];fixed.append([x-4.32,y-4.32,x+4.32,y+4.32])
   class ReservedRows(RowAllocator):
    def __init__(self,*args,**kwargs):
     super().__init__(*args,**kwargs)
     for r in fixed:self.reserve_rectangle(r)
   F.RowAllocator=ReservedRows
   slots=t.get('ft_slots',[]);completed=False
   for attempt in range(a.max_extra_stations+1):
    before=copy.deepcopy(slots)
    try:
     ledger=F._place_type(model,tn,405.,1.0,{},{});report['ft']+=ledger;completed=True;break
    except ValueError as err:
     t['ft_slots']=before;slots=t['ft_slots'];text=str(err);name=text.split(':',1)[0]
     bad=next((s for s in slots if s['name']==name),None)
     report['allocation_failures'].append(dict(part=pn,attempt=attempt,error=text))
     if bad is None or attempt==a.max_extra_stations:break
     bad['stations']+=1
   if not completed:raise RuntimeError(f'{pn}: actual-site allocation failed; see allocation_failures')
   report['clock_ff_load'][pn]=sum((s['width']+1)*max(0,s['stations']-1) for s in slots)
   report['completed_parts'].append(pn)
   report['wrapper_transport_ff'][pn]=dict(old=info.get('old_wrapper_transport_ff'),new=sum(b['width']+1 for b in t.get('buses',[]))+sum((s['width']+1)*s['stations'] for s in slots))
   (out/'progress.json').write_text(json.dumps({'completed_parts':report['completed_parts'],'ft':report['ft'],'internal':report['internal'],'clock_ff_load':report['clock_ff_load']},indent=1)+'\n')
   (out/'parts').mkdir(exist_ok=True)
   (out/'parts'/(pn+'.json')).write_text(json.dumps(dict(part=pn,type=tn,template=t,info=info),separators=(',',':'))+'\n')
   print('PART_COMPLETE',pn,len(ledger),report['clock_ff_load'][pn],flush=True)
  except Exception as err:
   P['partition_types'][parts[pn]['type']]=original_type
   report['part_failures'].append(dict(part=pn,error=f'{type(err).__name__}: {err}'))
   print('PART_FAIL',pn,str(err),flush=True)
   if not a.keep_going:raise
 # New module/view identity follows the full physical interface. Existing source
 # and core-conns templates are identified explicitly for the parent's overlay.
 rename={}
 for pn,info in report['changed_types'].items():
  if pn not in set(report['completed_parts']):continue
  tmp=parts[pn]['type'];t=P['partition_types'][tmp];identity=copy.deepcopy(t);identity.pop('module',None);identity.pop('note',None);digest=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:10];nn=info['old']+'__tr_'+digest;t['module']='hbm_arch_'+nn
  if nn in P['partition_types'] and P['partition_types'][nn]!=t:raise RuntimeError('physical interface hash collision')
  P['partition_types'][nn]=t;parts[pn]['type']=nn;rename[tmp]=nn;info['new']=nn
 for tmp in rename:P['partition_types'].pop(tmp)
 mm=S.Plan(P)
 for l in P['lanes']:
  lid=l['id'];oldrow=P['latency']['lanes'].get(lid,{});row=mm.lane_latency(lid);row['param']=oldrow.get('param','LAT_'+lid.upper());P['latency']['lanes'][lid]=row
  if row['cycles']!=oldrow.get('cycles'):report['latency'].append(dict(lane=lid,old=oldrow.get('cycles'),new=row['cycles'],added=row['cycles']-oldrow.get('cycles',0),reason='actual FT row-site allocation'))
 report['status']='PARTIAL_FT_SITES_ALLOCATED_WITH_FAILURES' if report['part_failures'] else ('ACTUAL_FT_SITES_ALLOCATED_PENDING_G0_G1' if selected==set(report['changed_types']) else 'PARTIAL_FT_SITES_ALLOCATED')
 (out/'die_plan.json').write_text(json.dumps(P,separators=(',',':'))+'\n')
 if report['part_failures']:sys.exit(1)
except Exception as err:
 report['status']='FAIL';report['failures'].append(f'{type(err).__name__}: {err}');raise
finally:(out/'report.json').write_text(json.dumps(report,indent=1)+'\n')
