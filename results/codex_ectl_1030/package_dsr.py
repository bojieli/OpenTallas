#!/usr/bin/env python3
"""Package actual SIGNED/EQ extracted views for die STA; never promote a missing physical view."""
import json,hashlib,re,shutil,sys
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan')
import die_sta_related as D
import core_clock_contract as CC
R=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for q,m in [('q0','qkd_ectlk_q0'),('q3','qkd_ectlk_q3'),('e0','kv3_head_eighth_e0')]:
 v=R/'dsr_views'/m
 if q!='e0':
  src=R/'collected'/q
  for p in (src/'views').iterdir():shutil.copy(p,v/p.name)
  for f in ['signoff.json','lec_routed.json','identity.json']:shutil.copy(src/f,v/f)
  cj=json.loads((src/'core.json').read_text())
 else:
  cj=json.loads((v/'kit_core.json').read_text());shutil.copy(R/'e0_orient/fMX_pins.json',v/'pins.json')
 so=json.loads((v/'signoff.json').read_text());eq=json.loads((v/'lec_routed.json').read_text());assert so['verdict']=='SIGNED' and eq['verdict']=='EQUIVALENT'
 lefp=v/f'{m}.lef';lef=lefp.read_text();outline=list(map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef).groups()))
 planpins=json.loads((v/'pins.json').read_text())
 errors=[]
 for p in planpins['pins']:
  pin=re.search(r'\bPIN\s+'+re.escape(p['name'])+r'\s*\n(.*?)\n\s*END\s+'+re.escape(p['name'])+r'\s*\n',lef,re.S)
  if not pin:errors.append((p['name'],'missing'));continue
  matches=[];layer=None
  for line in pin[1].splitlines():
   lm=re.search(r'LAYER\s+(\S+)\s*;',line)
   if lm:layer=lm[1]
   rm=re.search(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;',line)
   if rm:
    a,b,c,d=map(float,rm.groups());matches.append((layer,(a+c)/2,(b+d)/2))
  if not any(layer==p['layer'] and abs(x-p['x'])<.0011 and abs(y-p['y'])<.0011 for layer,x,y in matches):errors.append((p['name'],matches,p))
 assert not errors,(m,errors[:2])
 cj['clock_latency_measured']=so['core_latency']['measured'];cj['actual_signed_view']=dict(module=m,lib_cell=m,kit=so['inputs']['kit'],source='actual extracted SIGNED + current routed EQ',alias=False)
 (v/f'{m}.core.json').write_text(json.dumps(cj,indent=1)+'\n')
 pc=D.canon_sha256(D.canon_pins(planpins,outline))
 prov=dict(verdict='SIGNED',views_status='signoff',kit=dict(module=m,outline_um=outline,pins_file='pins.json',pins_sha256=sha(v/'pins.json'),pins_canon_sha256=pc,pins=len(planpins['pins'])),routed_lec=dict(verdict=eq['verdict'],counts=eq['counts'],record='lec_routed.json'),measurement=dict(pin_means=so['core_latency']['measured'],source='signoff.json corners insertion_pinflops',info_droop='NOT RUN; non-gating'))
 (v/'provenance.json').write_text(json.dumps(prov,indent=1)+'\n')
 contract=CC.from_signoff(v/f'{m}_tt.lib',so,v/'signoff.json')
 (v/'clock_contract.json').write_text(json.dumps(contract,indent=1)+'\n')
 for corner in ['TT','FF']:
  cm=D.core_view_model(m,v,corner,2.0,0)
  assert cm['meta']['verdict']=='SIGNED'
  how,why=D.pins_relation(cm['meta'],str(v/'pins.json'),None,outline);assert why is None,(how,why)
 print(m,len(planpins['pins']),'LEF centres match; DSR TT/FF load and pin match PASS')
