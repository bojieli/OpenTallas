import json,re,collections
from pathlib import Path
m=json.loads(Path('out/netlist.json').read_text())['modules']['hidx_coupon1'];lef=Path('canonical/cells.lef').read_text();used=collections.Counter(c['type'] for c in m['cells'].values() if c['type']!='$scopeinfo');refs={}
for name,body in re.findall(r'MACRO\s+(\S+)\s+(.*?)END\s+\1\s',lef,re.S):
 if name not in used:continue
 pins={n:b for n,b in re.findall(r'PIN\s+(\S+)\s+(.*?)END\s+\1\s',body,re.S)}
 pg={}
 for n,b in pins.items():
  use=re.search(r'USE\s+(\w+)',b)
  if use and use.group(1) in ['POWER','GROUND']:
   layer=None;rect=[]
   for line in b.splitlines():
    if z:=re.search(r'LAYER\s+(\S+)',line):layer=z[1]
    if z:=re.search(r'RECT\s+([0-9. -]+);',line):rect.append(dict(layer=layer,rect_um=list(map(float,z[1].split()))))
   pg[n]=dict(role=use.group(1),shapes=rect)
 assert set(pg)=={'VDD','VSS'},(name,pg)
 assert all(x['layer']=='M1' for v in pg.values() for x in v['shapes'])
 assert all(x['rect_um'][1]<=.270<=x['rect_um'][3] for x in pg['VDD']['shapes'])
 assert all(x['rect_um'][1]<=0<=x['rect_um'][3] for x in pg['VSS']['shapes'])
 refs[name]=dict(instance_count=used[name],pg_mterms=pg)
assert set(refs)==set(used)
rails=[dict(index=i,y_um=2.16+i*.270,role='GROUND' if i%2==0 else 'POWER') for i in range(505)]
jsonout=dict(scope='LEF/legal-row PG CONTACT MODEL ONLY; no placement or connectivity claim',actual_odb=None,terminals=2*sum(used.values()),masters=refs,row_orientation='alternate R0/MX, VSS first bottom; actual legal row engine result OPEN',model_rails=rails,m1_rail_width_um=.018,whole_core_model_m1_rail_area_um2=505*136.08*.018,band_model_m1_rail_area_um2=105*136.08*.018,m1_rail_metal_fraction=505*136.08*.018/(136.08**2),upper_metal_straps_and_vias=None,clock_pg_signal_routing_capacity_qualification=False,birth_policy='a92 full-native-MTerm role binding before protection for all new cells; kit activation NONE',actual_binding_coverage=None,via_cut_enclosure=None,shorts=None)
Path('out/pg_model.json').write_text(json.dumps(jsonout,indent=2)+'\n')
