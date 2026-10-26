from pathlib import Path
import json,re,hashlib
p=Path('/srv/opentallas-scratch2/claude/codex-qc-sramif-1713')
for k in ('btab','prog'):
 d=p/(k+'_aspect_a1')
 if not d.exists():continue
 ps=json.loads((d/'pins.json').read_text())
 for q in ps:
  if q['bus']=='ck':q['x']=177.132
 (d/'pins.json').write_text(json.dumps(ps,indent=1)+'\n')
 s=(d/'io.tcl').read_text();s=re.sub(r'(place_pin -pin_name \{ck\} -layer M5 -location \{)[^}]+',r'\g<1>177.132000 0.042000',s);(d/'io.tcl').write_text(s)
 s=(d/'target_profile.lef').read_text();s=re.sub(r'( PIN ck\n.*?   RECT )[^;]+',r'\g<1>177.120000 0.000000 177.144000 0.084000 ',s,flags=re.S);(d/'target_profile.lef').write_text(s)
 j=json.loads((d/'target_native_pins.json').read_text())
 for q in j['pins']:
  if q['name']=='ck':q['x']=177.132
 (d/'target_native_pins.json').write_text(json.dumps(j,indent=1)+'\n')
 j=json.loads((d/'profile1713.json').read_text());j['revision']='a1.1_correct_clock_reserved_gap';j['pins_sha256']=hashlib.sha256((d/'pins.json').read_bytes()).hexdigest();j['clock_pin_um']=[177.132,.042];(d/'profile1713.json').write_text(json.dumps(j,indent=1)+'\n')
 print(d,'correctedck',j['clock_pin_um'])
