#!/usr/bin/env python3
"""Independent final engineering gate: zero slew/cap/fanout/antenna/DRC."""
import argparse,json,math,pathlib,sys
p=argparse.ArgumentParser();p.add_argument('physical');a=p.parse_args()
d=json.loads(pathlib.Path(a.physical).read_text());checks=d.get('acceptance',{}).get('checks',[])
keys=['max_slew_violations','max_cap_violations','max_fanout_violations','antenna_violating_nets','antenna_violating_pins','drc_errors']
physical=[c for c in checks if c.get('stage')=='place_and_route'];bad=[]
if not physical:bad.append('missingfinalplace_and_routeengineeringcheck')
for c in physical:
 for key in keys:
  val=c.get(key)
  if not isinstance(val,(int,float)) or not math.isfinite(val) or val!=0:bad.append(f'{key}={val}')
print(json.dumps(dict(verdict='FAIL' if bad else 'PASS',fails=bad)))
sys.exit(1 if bad else 0)
