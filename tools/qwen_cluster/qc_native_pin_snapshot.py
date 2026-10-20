#!/usr/bin/env python3
"""Read-only gate pin geometry snapshot for subsequent parent endpoint checks."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('manifest');a=p.parse_args()
for r in json.loads(Path(a.manifest).read_text()):
 run=Path(r['run']);p=run/'routes/gate/work/orfs/gate_dump.json';raw=p.read_bytes();d=json.loads(raw);pins={}
 for name,net,sig,direction,rects in d['bterms']:
  if sig in ['POWER','GROUND']:continue
  assert name not in pins
  pins[name]=dict(direction=direction,sig_type=sig,rectangles=rects,centers_um=[[(v[0]+v[2])/2,(v[1]+v[3])/2]for layer,v in rects])
 out=dict(schema='opentallas.cb16.native_pin_snapshot.v1',gate_run=str(run),gate_dump_sha256=hashlib.sha256(raw).hexdigest(),die_um=d['die'],signal_clock_pins=len(pins),pins=pins,scope='gated pin geometry only; parent position/orientation/routes must be separately checked')
 Path('native_pins_'+r['half']+'.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print('NATIVE_PINS',r['half'],len(pins))
