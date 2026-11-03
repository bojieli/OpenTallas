import json,gzip
from pathlib import Path
O=Path(__file__).resolve().parent;m=json.loads(gzip.decompress((O/'comb_road_model.json.gz').read_bytes()));r=m['report'];total=r['functional_cell_area_um2'];lines=['# PREP only: requires ROOT-reviewed same-source233.28x302.4 FP/FF capsule. No CAD permission.','set ::ot_ctl_road_spec {']
for z in r['zones']:
 budget=r['measured_buffer_cell_area_um2']*z['functional_cell_area_um2']/total
 lines.append('  {'+' '.join([z['name']]+[f'{v:.6f}' for v in z['bbox_um']]+[f'{budget:.9f}'])+'}')
lines+=['}','set ::ot_ctl_road_seeds {']
for p in m['cells']:
 assert not any(c in p['name'] for c in '{}\n')
 lines.append('  {'+'{'+p['name']+'} '+p['master']+' '+p['zone']+'}')
lines+=['}','source /work/ctl_comb_roads.tcl',''];(O/'ctl_comb_roads_spec.tcl').write_text('\n'.join(lines))
