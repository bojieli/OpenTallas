"""Diagnostic density of actual direct boundary FFs by actual pin face."""
import json,gzip,sys,collections,hashlib
from pathlib import Path
p=Path(sys.argv[1]);d=json.load(gzip.open(p,'rt'));seq={x['instance']:x for x in d['sequential_instances']};faces=collections.defaultdict(lambda:dict(ports=[],flops=set(),along=[]));missing=[]
for port in d['port_bits']:
 if port['base_port']=='ck_core':continue
 face=port['actual_nearest_face'];z=faces[face];z['ports'].append(port['name']);z['along'].append(port['xy_um'][1 if face in 'WE' else 0])
 for k in ('data_input_flops','data_output_flops'):
  for pin in port[k]:
   inst=pin.rsplit('/',1)[0];assert inst in seq
   z['flops'].add(inst)
rows={}
for face,z in faces.items():
 lo,hi=min(z['along']),max(z['along']);coords=[]
 for inst in z['flops']:
  q=seq[inst];coords.append(q['output_pins'][0]['xy_um'][1 if face in 'WE' else 0])
 coords.sort();j=0;peak=0
 for i,x in enumerate(coords):
  while x-coords[j]>10:j+=1
  peak=max(peak,i-j+1)
 rows[face]={'port_bits':len(z['ports']),'unique_direct_boundary_FFs':len(z['flops']),'actual_pin_span_um':[lo,hi],'FF_per_um_over_actual_pin_span':len(z['flops'])/(hi-lo),'peak_FF_per_um_in10um_projection':peak/10,'global_density_le6':len(z['flops'])/(hi-lo)<=6}
r={'schema':'peer.pre_cts_boundary_density.v1','scope':'Frozen3_place diagnostic. Direct source port-stage membership only; each FF counted once per face, shared multi-face FF possible. Global<=6 over actual populated pin span and ten-micron projection are descriptive, not exact track/placement/admission proof. Native pin accessibility separately checked.', 'identity_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'odb_sha256':d['odb_sha256'],'faces':rows};p.with_name('pin_density.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
