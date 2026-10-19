import hashlib,json,re
from pathlib import Path
root=Path('/home/ubuntu/wt/codex-qw-d2d-safe2-1019')
result={'schema':'opentallas.literal_macro_face_inventory.v1','literal_limit_pins_per_um':6,'escape_qualification':False,'macros':[]}
for name in ['ot_sram_1r1w_64x512_m1_r2c2']:
 p=root/'physical/asap7_memory_macros_v2'/name/(name+'.lef');raw=p.read_text();w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',raw).groups());faces={x:[] for x in 'WENS'};layers={}
 for m in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1\s*$',raw,re.M|re.S):
  pin,body=m.groups()
  if re.search(r'USE\s+(POWER|GROUND)',body):continue
  current=None
  for line in body.splitlines():
   lm=re.search(r'LAYER\s+(\S+)\s*;',line)
   if lm:current=lm.group(1)
   rm=re.search(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',line)
   if not rm:continue
   x1,y1,x2,y2=map(float,rm.groups());layers[current]=layers.get(current,0)+1
   for face,hit,along in [('W',abs(x1)<1e-6,(y1+y2)/2),('E',abs(x2-w)<1e-6,(y1+y2)/2),('S',abs(y1)<1e-6,(x1+x2)/2),('N',abs(y2-h)<1e-6,(x1+x2)/2)]:
    if hit:faces[face].append((pin,current,along))
 rows={}
 for face,grants in faces.items():
  span=h if face in 'WE' else w;coords=sorted(set(g[2] for g in grants));count=len(set(g[0] for g in grants));density=count/span
  rows[face]={'signal_clock_pins':count,'face_length_um':span,'pins_per_um':density,'literal_pass':density<=6,'min_center_pitch_um':min((b-a for a,b in zip(coords,coords[1:])),default=None),'occupied_center_span_um':(coords[-1]-coords[0] if len(coords)>1 else 0),'occupied_center_density_pins_per_um':(count/(coords[-1]-coords[0]) if len(coords)>1 else None),'pin_layers':sorted(set(g[1] for g in grants)),'minimum_spread_length_for_literal6_um':count/6}
 result['macros'].append(dict(master=name,lef=str(p.relative_to(root)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size_um=[w,h],signal_clock_rects_by_layer=layers,faces=rows))
result['required_actual_escape_evidence']=['Actual successor placed macro orientations and pin-layer inventory','Allocated legal access strip and channel per face, with all PG/via obstructions deducted by routing layer','Legal track-to-pin transitions and spread row pitch; abstract projected count is insufficient','Actual GRT overflow and DRT pin-access/DRC evidence tied to exact source snapshot']
out=Path('/home/ubuntu/scratch/codex-qw-ctlm-cones/d2d_v2_macro_face_inventory.json');out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
