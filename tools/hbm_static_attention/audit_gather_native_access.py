#!/usr/bin/env python3
"""Independent actual ODB readback + conservative PG escape-cut model."""
import argparse,json,math,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('actual',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();x=json.loads(a.actual.read_text());D=x['die'];layers={v['name']:v for v in x['layers']};faces={f:[] for f in 'WENS'}
for bt in x['bterms']:
 if bt[2] in ('POWER','GROUND'):continue
 assert len(bt[4])==1,(bt[0],'multiplepinrectangles')
 layer,r=bt[4][0];cx=(r[0]+r[2])/2;cy=(r[1]+r[3])/2
 face=min([(abs(cx-D[0]),'W'),(abs(cx-D[2]),'E'),(abs(cy-D[1]),'S'),(abs(cy-D[3]),'N')])[1]
 faces[face].append((bt[0],layer,cx if face in 'NS' else cy))
r={'scope':'ActualODBpinandPDNgeometry; conservative3umfaceescape-cut model usingactualtechnologypitchandtrackphasefromplacedpins. Uniformtrack-gridmodel, notroutedaccess/DRCproof.','source_sha256':hashlib.sha256(a.actual.read_bytes()).hexdigest(),'outline_um':D,'face_band_um':3,'corner_margin_um':5.4,'signal_pitch_um':.096,'PG_spacing_um':.024,'headroom_limit':.6,'faces':{}}
for f in ('W','E','N'):
 pts=faces[f];assert pts
 lay='M4' if f in 'WE' else 'M5';assert all(t[1]==lay for t in pts)
 extent=D[3] if f in 'WE' else D[2];pitch=layers[lay]['pitch'];half=layers[lay]['width']/2;phase=round(pts[0][2]%pitch,6)
 if abs(phase-pitch)<1e-6:phase=0
 assert all(abs((t[2]-phase)/pitch-round((t[2]-phase)/pitch))<1e-5 for t in pts),'offtrack'
 obs=[]
 for kind,l1,l2,b in x['pdn_edge']:
  if lay not in (l1,l2):continue
  if (f=='W' and b[0]<3) or (f=='E' and b[2]>D[2]-3) or (f=='N' and b[3]>D[3]-3):obs.append(b)
 along=(1,3) if f in 'WE' else (0,2);slots=[]
 for k in range(math.ceil(extent/pitch)+1):
  pos=phase+k*pitch
  if pos<5.4 or pos>extent-5.4:continue
  if any(pos+half+.024>b[along[0]] and pos-half-.024<b[along[1]] for b in obs):continue
  if slots and pos-slots[-1]<.096-1e-6:continue
  slots.append(pos)
 ratio=len(pts)/max(1,len(slots))
 r['faces'][f]={'pins':len(pts),'layer':lay,'actual_PG_wire_or_via_shapes_in_band':len(obs),'actual_placed_track_phase_um':phase,'conservative_available_separated_slots':len(slots),'utilization':ratio,'pass':ratio<=.6}
r['pass']=all(v['pass'] for v in r['faces'].values());a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(0 if r['pass'] else 1)
