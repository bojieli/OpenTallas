import json,collections,math
from pathlib import Path
p=Path(__file__).parent;m=json.load(open(p/'output_probe_margin.json'));o=json.load(open(p/'quarter_bay_lower_bound.json'));b={tuple(r['point_um']):r for r in o['rows']};edges={}
for path in m['paths']:
 points=[tuple(path['source_um'])]+[tuple(w['point_um']) for w in path['waypoints']]+[tuple(path['target_um'])]
 for i,(a,z) in enumerate(zip(points,points[1:])):
  if a==z:continue
  d=abs(a[0]-z[0])+abs(a[1]-z[1]);ra=b[a]['l1_radius_area_lower_bound_um'] if i>0 else 0;rz=b[z]['l1_radius_area_lower_bound_um'] if i+1<len(points)-1 else 0
  key=(a,z);edges[key]=dict(a=a,b=z,hop_um=d,point_slack_um=405-d,minimum_radius_a_um=ra,minimum_radius_b_um=rz,robust_envelope_shortfall_um=max(0,d+ra+rz-405))
failed=sorted([e for e in edges.values() if e['robust_envelope_shortfall_um']>0],key=lambda e:-e['robust_envelope_shortfall_um'])
o['robust_envelope_qualification']='Sufficient worst-direction envelope diagnostic only; failure does not prove optimized placement impossible. Plain FF lower-bound L1 radii at60%, excluding obstacles and clock/PG/holds.';o['edges_requiring_directional_pack_or_geometry_shift']=failed
(p/'quarter_bay_lower_bound.json').write_text(json.dumps(o,indent=1));print('shortfall edges',len(failed));print(failed[:5])
