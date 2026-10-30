from pathlib import Path
import json,copy
base=Path('/srv/opentallas-scratch/claude/codex-kv-hr-2249');r=base/'mux2';r.mkdir(exist_ok=True)
x=json.load(open(base/'plan.json'));t=x['partition_types']['kv3_hub_Wi']
oldpins=json.load(open('/srv/opentallas-scratch/claude/wt/codex-kv-hr-2249/results/codex_kv_hr_2249/input/qkd_hr_phy_adp_pins.json'));p=copy.deepcopy(oldpins);w,h=129.6,69.12
snap=lambda a:round(.024+round((a-.024)/.048)*.048,6)
for q in p['pins']:
 ox,oy=q['x'],q['y'];q['x']=snap(ox*w/103.68);q['y']=round(oy*h/95.04,6)
 if ox<.5:q['x']=0.
 if 103.68-ox<.5:q['x']=w
 if oy<.5:q['y']=0.
 if 95.04-oy<.5:q['y']=h
 if q['layer']=='M4':q['y']=snap(q['y'])
# Preserve ordering at a healthy original 0.192-um pitch rather than shrinking edge pitch.
for face in ['W','E']:
 rows=sorted([q for q in p['pins'] if abs(q['x']-(0 if face=='W' else w))<.5],key=lambda q:q['y'])
 start=snap((h-(len(rows)-1)*.192)/2)
 for i,q in enumerate(rows):q['y']=round(start+i*.192,6)
for q in p['pins']:
 if q['name']=='ck[0]':q.update(x=64.824,y=8.64)
p['frame']='core R0 origin(0,0), outline129.6x69.12; mux2 SRAM view';pf=r/'qkd_hr_phy_adp_pins_mux2.json';pf.write_text(json.dumps(p,indent=2)+'\n')
for c in t['hard_cores']:
 if c['module']=='qkd_hr_phy_adp':
  i=int(c['inst'].rsplit('_',1)[1]);c['origin_um']=[round(181.44+(i%4)*146.88,6),round(120.96+(i//4)*86.4,6)];c['outline_um']=[w,h];c['pins_file']=str(pf)
  for tap in t['clock']['taps']:
   if tap['name']==c['inst']+'.ck[0]':tap['xy']=[round(c['origin_um'][0]+64.824,6),round(c['origin_um'][1]+8.64,6)]
 if c['inst']=='host__qkd_hr_cdc_ci':
  ox,oy=c['origin_um'];c['origin_um']=[25.92,622.08]
  for tap in t['clock']['taps']:
   if tap['name'].startswith(c['inst']+'.'):tap['xy']=[round(tap['xy'][0]+25.92-ox,6),round(tap['xy'][1]+622.08-oy,6)]
(r/'plan_mux2.json').write_text(json.dumps(x,indent=2)+'\n')
