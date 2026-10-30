#!/usr/bin/env python3
"""KV HR fixed-slot repair: fit actual SRAM; compact three underfilled cores. No RTL/cycle change."""
import argparse,copy,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('out');a=p.parse_args()
HERE=Path(__file__).resolve().parent;out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
x=json.load(open(a.plan));t=x['partition_types']['kv3_hub_Wi'];cs=t['hard_cores']
new={'qkd_hr_phy_adp':(207.36,86.4),'qkd_hr_cdc_ch':(198.72,198.72),'qkd_hr_cdc_pc':(259.2,259.2),'qkd_hr_core_guard':(155.52,155.52)}
PITCH=dict(M3=.036,M4=.048,M5=.048,M6=.064,M7=.064);OFF=dict(M3=.009,M4=.024,M5=.024,M6=.032,M7=.032)
def snap(v,l):return round(OFF[l]+round((v-OFF[l])/PITCH[l])*PITCH[l],6)
report={'scope':'PREP; not adopted until parent plan/source/clock gates','added_data_cycles':0,'changes':[],'fill_estimate':{}}
for mod,(nw,nh) in new.items():
 old=next(c for c in cs if c['module']==mod);ow,oh=old['outline_um'];d=json.load(open(HERE/'input'/f'{mod}_pins.json'))
 for q in d['pins']:
  ox,oy=q['x'],q['y'];q['x']=round(ox*nw/ow,6);q['y']=round(oy*nh/oh,6)
  # Move boundary points exactly with the face; retain all same-layer ordering.
  if ox<.5:q['x']=ox
  elif ow-ox<.5:q['x']=round(nw-(ow-ox),6)
  if oy<.5:q['y']=oy
  elif oh-oy<.5:q['y']=round(nh-(oh-oy),6)
  if q['layer'] in ('M3','M5','M7'):q['x']=snap(q['x'],q['layer'])
  else:q['y']=snap(q['y'],q['layer'])
  if q['name']=='ck[0]':q.update(x=snap(nw/2,q['layer']),y=25.92 if mod=='qkd_hr_phy_adp' else nh/2)
 d['frame']=f'core R0, origin (0,0), outline {nw} x {nh}'
 d['source']=str(d.get('source',''))+' | CODEX KV-HR 2249 physical recut only'
 pf=out/f'{mod}_pins_2249.json';pf.write_text(json.dumps(d,indent=2)+'\n')
 for c in cs:
  if c['module']!=mod:continue
  before=copy.deepcopy(c)
  c['outline_um']=[nw,nh];c['pins_file']=str(pf)
  if mod=='qkd_hr_phy_adp':
   i=int(c['inst'].rsplit('_',1)[1]);c['origin_um']=[round(25.92+(i%4)*224.64,6),round(120.96+(i//4)*103.68,6)]
  c['note']+=' | CODEX KV-HR 2249 local physical closure recut (unadopted)'
  report['changes'].append({'inst':c['inst'],'old_origin':before['origin_um'],'new_origin':c['origin_um'],'old_outline':before['outline_um'],'new_outline':c['outline_um']})
  cp=next(q for q in d['pins'] if q['name']=='ck[0]')
  for tp in t['clock']['taps']:
   if tp['name']==c['inst']+'.ck[0]':tp['xy']=[round(c['origin_um'][0]+cp['x'],6),round(c['origin_um'][1]+cp['y'],6)]
 # keep full no-halo area for SRAM fill estimate; final place measures the standard-cell band.
 area={'qkd_hr_phy_adp':6245.5,'qkd_hr_cdc_ch':6481.6,'qkd_hr_cdc_pc':11228.8,'qkd_hr_core_guard':4150.5}[mod]
 report['fill_estimate'][mod]=round(area/(nw*nh-(174.12*29.736 if mod=='qkd_hr_phy_adp' else 0)),4)
# Unsigned neighbouring cores move inside the same parent outline; no parent pin changes.
moves={'host__qkd_hr_phy_pad':[1019.52,120.96],'host__qkd_hr_cdc_ci':[25.92,622.08],'host__qkd_hr_cdc_hi':[267.84,622.08]}
for c in cs:
 if c['inst'] not in moves:continue
 ox,oy=c['origin_um'];nx,ny=moves[c['inst']];c['origin_um']=[nx,ny]
 report['changes'].append({'inst':c['inst'],'old_origin':[ox,oy],'new_origin':[nx,ny],'old_outline':c['outline_um'],'new_outline':c['outline_um']})
 for tp in t['clock']['taps']:
  if tp['name'].startswith(c['inst']+'.'):tp['xy']=[round(tp['xy'][0]+nx-ox,6),round(tp['xy'][1]+ny-oy,6)]
# Check hard-core halos against all other hard cores, not just the moved subset.
err=[]
for i,c in enumerate(cs):
 ax,ay=c['origin_um'];w,h=c['outline_um'];bx,by=ax+w,ay+h
 if min(ax,ay)<0 or bx>t['outline_um'][0] or by>t['outline_um'][1]:err.append(f"outside {c['inst']}")
 for d in cs[i+1:]:
  dx,dy=d['origin_um'];dw,dh=d['outline_um']
  if max(ax-4.32,dx-4.32)<min(bx+4.32,dx+dw+4.32)-1e-6 and max(ay-4.32,dy-4.32)<min(by+4.32,dy+dh+4.32)-1e-6:err.append(f"halo overlap {c['inst']} / {d['inst']}")
report['halo_errors']=err
(out/'plan_hr_2249.json').write_text(json.dumps(x,indent=2)+'\n');(out/'recut_report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
