import json,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-qc-reset-infra-1029')
sys.path.insert(0,str(R/'src/tools/die_plan'))
import schema as S,reset_route as RR,reset_tree as RT
plan_path=Path('/srv/opentallas-scratch2/claude/codex-qc-1029/physical_event/plan_start_native_h800.json')
p=S.Plan(S.load(plan_path),plan_path)
n=RR.network(p);(R/'reset_network.json').write_text(json.dumps(n,indent=1));w=RT.wf_plan(p)
r=json.load(open('/srv/opentallas-scratch2/claude/codex-qc-start-native-0251/perimeter1/emitted/start_stages.json'));root=next(s for s in r['stages'] if s['root']);x,y=root['clock_pin_xy_um'];c=[]
for part in p.parts:
 for pin in RR.scalar_pins(p,p.parts[part]['type']):
  xx,yy=p.to_die(part,pin['xy_um']);d=abs(xx-x)+abs(yy-y)
  c.append(dict(part=part,pin=pin['name'],xy_um=[xx,yy],hop_to_root_um=d,part_release_cycles=w['parts'][part]['release'],net=n['bindings'][part][pin['name']]))
c.sort(key=lambda q:q['hop_to_root_um']);selection=dict(provider_root=root['region'],provider_root_xy_um=[x,y],candidates=c[:12],scope='actual reset_tree native registered output sites; targetLEF+ODB emission still required')
(R/'provider_root_reset.json').write_text(json.dumps(selection,indent=1));print(json.dumps(dict(root=n['root'],parts=len(n['bindings']),edges=len(n['edges']),max_hop_um=n['max_hop_um'],max_release_cycles=n['max_release_cycles'],provider_root_reset_nearest=c[0])),flush=True)
