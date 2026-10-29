#!/usr/bin/env python3
"""Opt-in two-variant outline feasibility; does not adopt or route a plan."""
import json,math,sys
from pathlib import Path
base,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
d=json.load(open(base/'die_plan.json'));cm=json.load(open(base/'core_macros.json'))['cores']
variants={
'ot_hbm_su_static_qcore_r13':[[293.76,207.36],[224.64,276.48]],
'ot_hbm_su_static_cxport_ij_q':[[362.88,388.8],[380.16,362.88]],
'ot_hbm_su_static_sfustore_hw':[[345.6,354.24],[449.28,259.2]]}
def ov(a,b):return min(a[2],b[2])-max(a[0],b[0])>1e-6 and min(a[3],b[3])-max(a[1],b[1])>1e-6
def rect(c):x,y=c['origin_um'];w,h=c['outline_um'];return [x,y,x+w,y+h]
rows=[]
for m,vs in variants.items():
 for vn,sz in enumerate(vs,1):
  r={'module':m,'variant':vn,'size_um':sz,'instances':[],'added_cycles':0,'needs_new_clock_slice':True}
  for tn,t in d['partition_types'].items():
   for c in t.get('hard_cores',[]):
    if c['module']!=m:continue
    x,y=c['origin_um'];w,h=c['outline_um'];nw,nh=sz;obs=[rect(z) for z in t['hard_cores'] if z is not c];tw,th=t['outline_um'];fits=[]
    for xx in [x,x+w-nw]:
     for yy in [y,y+h-nh]:
      b=[xx,yy,xx+nw,yy+nh]
      if xx>=0 and yy>=0 and b[2]<=tw+1e-6 and b[3]<=th+1e-6 and not any(ov(b,z) for z in obs):fits.append([round(xx,4),round(yy,4)])
    r['instances'].append({'type':tn,'inst':c['inst'],'fits':fits,'old_origin':c['origin_um'],'old_size':c['outline_um']})
  r['all_instances_fit']=all(i['fits'] for i in r['instances']);r['status']='PARENT_SLOT_FEASIBLE' if r['all_instances_fit'] else 'PARENT_RELOT_REQUIRED'
  if 'sfustore' in m:
   nc,nr=(3,6) if vn==1 else (4,4);mac=cm[m]['macros'];w0=mac[0]['rect_um'][2]-mac[0]['rect_um'][0];h0=mac[0]['rect_um'][3]-mac[0]['rect_um'][1]
   x0=y0=15.12;gap=10.8;boxes=[]
   for k,q in enumerate(mac):
    x=x0+(k%nc)*(w0+gap);y=y0+(k//nc)*(h0+gap);boxes.append({'name':q['name'],'rect_um':[round(x,4),round(y,4),round(x+w0,4),round(y+h0,4)]})
   r['macro_grid']={'columns':nc,'rows':nr,'raw_gap_um':gap,'macros':boxes,'fits':max(b['rect_um'][2] for b in boxes)<=sz[0]-15.12 and max(b['rect_um'][3] for b in boxes)<=sz[1]-15.12,'macro_fill':len(mac)*w0*h0/((sz[0]-8.64)*(sz[1]-8.64))}
  rows.append(r)
prog=cm['ot_hbm_su_programme_pslice_c5']['macros'];area=sum((m['rect_um'][2]-m['rect_um'][0])*(m['rect_um'][3]-m['rect_um'][1]) for m in prog)
report={'schema':'opentallas.hbm.outline_variant_estimates.v1','basis':'Existing source/shape, parent-body non-overlap only. Unrouted estimates; no timing or cut-budget claim.','rows':rows,'programme_split_estimate':{'macro_count':len(prog),'macro_area_um2':area,'current_outline_um':cm['ot_hbm_su_programme_pslice_c5']['outline_um'],'macro_only_area_at_60percent':area/.6,'proposal':'Five physical column slices plus control; price/register all column-to-control cuts before RTL split. Existing single parent is not routed.'}}
(out/'outline_estimates.json').write_text(json.dumps(report,indent=1))
for r in rows:print(r['module'],r['variant'],r['status'],r.get('macro_grid',{}).get('fits'))
