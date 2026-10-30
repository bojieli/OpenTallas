import json,re,sys
from pathlib import Path
p=Path(sys.argv[1]);x=json.load(p.open());changes=[]
# Current plan models1866.24um, actual staged physicalW522LEF is1848.96um.
for tn in ('kv3_sys_SD','kv3_sys_SD_v1'):
 for c in x['partition_types'][tn]['contents']:
  if c['inst']=='serdes':
   assert c['outline_um']==[1866.24,972.0]
   c['outline_um']=[1848.96,972.0]
   changes.append({'type':tn,'old_phy_width':1866.24,'actual_lef_width':1848.96,'local_macro_box':[17.28,54,1866.24,1026],'new_supply_box':[17.28,54,1870.56,1026]})
# SWR0 and SE mirror: remove only stale extra margin, retain4.32um beyond actualmacro.
for d in x['die']['pg']['domains']:
 if d['name']=='phy_sys_SW_serdes':
  assert abs(d['rect_um'][2]-1883.52)<1e-6
  d['rect_um'][2]=1870.56
  d['bumps']['rect_um'][2]=min(d['bumps']['rect_um'][2],1870.56)
 elif d['name']=='phy_sys_SE_serdes':
  d['rect_um'][0]+=12.96;d['bumps']['rect_um'][0]+=12.96
p.with_name('plan_sd_actual_phy.json').write_text(json.dumps(x))
p.with_name('plan_delta.json').write_text(json.dumps({'changes':changes,'logic_cycles_added':0,'new_ring_width_um':25.92,'physical_phy_pg_contacts_removed':0,'reason':'New supply box still strictly contains the actual entire PHY LEF; bump generator already retains in-leaf legal sites only','status':'PREP not adopted'},indent=2)+'\n')
