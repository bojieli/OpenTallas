#!/usr/bin/env python3
"""Owner SS/FF +15ps policy. Raw corner reports remain immutable history."""
import argparse,hashlib,json,pathlib
p=argparse.ArgumentParser();p.add_argument('--physical',type=pathlib.Path,required=True)
p.add_argument('--corners',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True)
a=p.parse_args();physical=json.loads(a.physical.read_text());corners=json.loads(a.corners.read_text())
ss=corners.get('setup_ss',{}).get('worst_slack_ps')
ff=corners.get('hold_ff',{}).get('worst_slack_ps')
drc=physical.get('design',{}).get('drc')
passing=bool(ss is not None and ff is not None and ss>=15 and ff>=15 and drc==0)
r=dict(policy='Owner directives: SS setup >=15ps, FF hold >=15ps, DRC0, 1.2GHz, 60ps setup/25ps hold uncertainty',
setup_ss_ps=ss,hold_ff_ps=ff,drc=drc,standalone_corner_gate='PASS' if passing else 'FAIL',
qualification='GENERIC_IO_PATHFINDING',actual_die_clock_and_pin_budget_qualified=False,headline_closed=False,
raw_corner_closes_signoff_ignored=corners.get('closes_signoff'),
source_records_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.physical,a.corners)})
with a.out.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r,indent=2))
