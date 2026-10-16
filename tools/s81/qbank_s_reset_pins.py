#!/usr/bin/env python3
"""S81F-05: preserve qbank data bus order, put ck/rs at S-face sink centroid.
The unchanged 60.48x25.92 outline retains the margin missing in the old 17.28 gate.
A candidate assignment; die adoption is separate from gate/route qualification.
"""
from pathlib import Path
import collections,hashlib,json,re,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import fill2_kits as F
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'physical/s81_die_pins/fill2_gen19b/dsfd_qbank_S_t.tcl'
DEST=ROOT/'physical/s81_die_pins/qbank_s_reset_1016/dsfd_qbank_S.tcl'
W,H=60.48,25.92
rows=[]
for name,layer,x,y in re.findall(r'place_pin -pin_name \{([^}]+)\} -layer (\w+) -location \{([\d.]+) ([\d.]+)\}',SOURCE.read_text()):
 x,y=float(x),float(y)
 face=min({'W':x,'E':W-x,'S':y,'N':H-y},key={'W':x,'E':W-x,'S':y,'N':H-y}.get)
 if name in ('ck','rs'):face='S';layer='M5' if name=='ck' else 'M3'
 rows.append(dict(pin=name,layer=layer,x=x,y=y,face=face))
assert len(rows)==1210,len(rows)
pins,report=F.spread(dict(w=W,h=H,pins=rows),W,H,'ck',['rs'])
assert all(v['cut']<=.60 for v in report.values()),report
assert len({(p['layer'],p['x'],p['y']) for p in pins})==len(pins)
groups=collections.defaultdict(list)
for p in pins:
 along=p['x'] if p['face'] in 'NS' else p['y']
 assert abs((along-.012)/.048-round((along-.012)/.048))<1e-7,(p,'off track')
 groups[(p['face'],p['layer'])].append(along)
min_spacing={}
for (face,layer),values in groups.items():
 values=sorted(values)
 spacing=min(b-a for a,b in zip(values,values[1:]))
 assert spacing>=.096-1e-7,(face,layer,spacing)
 min_spacing[face+'/'+layer]=round(spacing,6)
old_n={p['pin']:p['x'] for p in rows if p['face']=='N'}
assert old_n=={p['pin']:p['x'] for p in pins if p['face']=='N'},'element-side coordinates must stay exact'
DEST.parent.mkdir(parents=True,exist_ok=True)
DEST.write_text('# S81F-05 candidate: data face order preserved, N coordinates exact; ck+rs at S centre; 60.48x25.92\n'+''.join('place_pin -pin_name {%s} -layer %s -location {%.3f %.3f} -force_to_die_boundary\n'%(p['pin'],p['layer'],p['x'],p['y']) for p in pins))
DEST.with_suffix('.json').write_text(json.dumps(dict(master='dsfd_qbank_S',outline_um=[W,H],source=str(SOURCE.relative_to(ROOT)),assignment='candidate pending die adoption',normal_cycles_added=0,init_release_edges_added=1,faces=report,clock_reset=[p for p in pins if p['pin'] in ('ck','rs')],pins=len(pins),unique_layer_positions=True,track_offset_um=.012,track_pitch_um=.048,min_same_layer_spacing_um=min_spacing,element_N_pin_positions_exact=True,tcl_sha256=hashlib.sha256(DEST.read_bytes()).hexdigest()),indent=1)+'\n')
print(DEST);print(json.dumps(report))
