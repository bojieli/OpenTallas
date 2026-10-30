import json,copy
from pathlib import Path
r=Path(__file__).resolve().parent
p=json.load(open(r/'plan_of_record/plan_c_sd_r6w7_reset_reduced_inventory.json'));oldio=copy.deepcopy(p['die']['io'])
lat=json.load(open(r/'sd_original_bump_lattice.json'));result={}
for d in p['die']['pg']['domains']:
 if d['name'] not in lat:continue
 part='sys_SW' if '_SW_' in d['name'] else 'sys_SE';width=522 if part=='sys_SW' else 521
 d['phy_macro_binding']={'part':part,'inst':'u_bound.u_core.u_phy.g_native.u_macro','module':'ot_qfd_serdes_112g_x6_phy_w'+str(width)}
 d['bumps']['rect_um']=list(d['rect_um'])
 d['bumps']['origin_um']=[round(x,3) for x in lat[d['name']]['origin_world_um']]
 d['bumps']['counts']=lat[d['name']]['count_xy']
 d['bumps']['note']+=' | CODEX PGtrim: explicit same old861worldsites+parity; newenvelope clips only unused tail, no re-centering.'
 pts=lat[d['name']]['sites']
 assert len(pts)==861 and all(d['rect_um'][0]<=v['xy_world_um'][0]<=d['rect_um'][2] and d['rect_um'][1]<=v['xy_world_um'][1]<=d['rect_um'][3] for v in pts)
 result[d['name']]={'binding':d['phy_macro_binding'],'origin_world_um':d['bumps']['origin_um'],'counts':d['bumps']['counts'],'sites_unchanged':len(pts),'functional_io_window_changed':False}
assert oldio==p['die']['io']
(r/'plan_of_record/plan_c_sd_r6w7_pg_bound.json').write_text(json.dumps(p,indent=1))
(r/'sd_pg_bound_receipt.json').write_text(json.dumps(result,indent=1))
print(json.dumps(result,indent=1))
