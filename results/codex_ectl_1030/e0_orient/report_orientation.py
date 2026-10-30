#!/usr/bin/env python3
"""E0 pin-preserving plan correction candidate; never writes a release plan implicitly."""
import argparse,json,re,hashlib
from pathlib import Path

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def records(p):
 j=json.loads(p.read_text());return {v['name']:v for v in j.get('pins',j)}
def mirror_rect(r,h):return (r[0],round(h-r[3],6),r[2],round(h-r[1],6))
def shapes(text):
 out=[];layer=None
 for line in text.splitlines():
  m=re.search(r'\bLAYER\s+(\S+)\s*;',line)
  if m:layer=m[1]
  m=re.search(r'\bRECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;',line)
  if m:out.append((layer,tuple(map(float,m.groups()))))
 return out

def run(root,plan=None,out=None):
 raw=records(root/'raw_pins.json');fm=records(root/'fMX_pins.json');lef=(root/'signed.lef').read_text()
 w,h=map(float,re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef).groups())
 assert w==h==216 and raw.keys()==fm.keys()
 bad=[n for n in raw if raw[n]['layer']!=fm[n]['layer'] or abs(raw[n]['x']-fm[n]['x'])>1e-6 or abs(raw[n]['y']+fm[n]['y']-h)>1e-6]
 assert not bad,bad[:3]
 pins={}
 for match in re.finditer(r'\bPIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1\s*\n',lef,re.S):pins[match[1]]=shapes(match[2])
 pg={}
 for n in ['VDD','VSS']:
  ss=pins[n];other={(l,mirror_rect(r,h)) for l,r in ss};assert set(ss)==other,(n,'not MX invariant')
  pg[n]=dict(rectangles=len(ss),mx_invariant=True)
 obs=shapes(re.search(r'\bOBS\s*\n(.*?)\n\s*END\s*\n',lef,re.S)[1]);assert set(obs)=={(l,mirror_rect(r,h)) for l,r in obs}
 centres=[]
 for n in fm:
  ss=pins[n]
  # The generated pin table is the centre of the actual emitted LEF rectangle.
  assert any(l==fm[n]['layer'] and abs((r[0]+r[2])/2-fm[n]['x'])<1e-6 and abs((r[1]+r[3])/2-fm[n]['y'])<1e-6 for l,r in ss),n
  centres.append(n)
 report=dict(schema='opentallas.e0_pin_preserving_orientation.v1',outline_um=[w,h],all_pins=len(raw),exact_parent_pin_equal=True,pin_equation='raw/MX = signed-fMX/R0',lef_signal_centres_match=len(centres),power=pg,obstructions=dict(rectangles=len(obs),mx_invariant=True,layers=sorted({l for l,r in obs})),source_sha256={p.name:digest(p) for p in [root/'raw_pins.json',root/'fMX_pins.json',root/'signed.lef']},raw_physical_view='NOT BUILT; no claim of separate raw SIGNED view',adoption='CANDIDATE: root approval + parent G0/bind/clock gates required; no release plan changed')
 if plan:
  j=json.loads(plan.read_text());changes=[]
  for tn,t in j['partition_types'].items():
   for c in t.get('hard_cores',[]):
    if c.get('module')!='kv3_head_eighth_e0':continue
    if Path(c.get('pins_file','')).name!='kv3_head_eighth_e0_pins_r25_r26q4.json':continue
    assert c.get('orient')=='MX';changes.append(dict(type=tn,inst=c['inst'],before='raw/MX',after='signed-fMX/R0',origin_um=c['origin_um']))
    c['orient']='R0';c['pins_file']=c['pins_file'].replace('_pins_r25_r26q4.json','_pins_fMX_r25_r26q4.json')
  assert len(changes)==10, f'expected ten raw/MX entries, got {len(changes)}'
  report['candidate_entries']=changes
  if out:out.write_text(json.dumps(j,indent=1)+'\n')
 (root/'report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report,indent=1))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path);ap.add_argument('--candidate-out',type=Path);a=ap.parse_args();run(Path(__file__).parent,a.plan,a.candidate_out)
