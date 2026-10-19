#!/usr/bin/env python3
"""Audit flattened Yosys JSON with native port directions and count checks."""
import argparse,json,collections,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('netlist');p.add_argument('--top',required=True);p.add_argument('--flops',type=int,required=True);p.add_argument('--out',required=True);a=p.parse_args();raw=Path(a.netlist).read_bytes();m=json.loads(raw)['modules'][a.top];loads=collections.Counter();drivers={}
for name,c in m['cells'].items():
 for pin,bits in c['connections'].items():
  direction=c['port_directions'][pin]
  if direction=='input'and pin not in ['CLK','CK','VDD','VSS','VPWR','VGND']:
   for b in bits:
    if isinstance(b,int):loads[b]+=1
  elif direction=='output'and c['type'].startswith(('DFF','SDFF','DF')):
   for b in bits:drivers[b]=dict(inst=name,type=c['type'],pin=pin)
assert len(drivers)==a.flops,('flattened flop count mismatch',len(drivers),a.flops)
reg=[dict(v,bit=b,loads=loads[b])for b,v in drivers.items()];reg.sort(key=lambda r:-r['loads']);flags=m['ports']['vld']['bits'];hist={str(i):loads[b]for i,b in enumerate(flags)}
viol=[v for v in reg if v['loads']>32];result=dict(schema='opentallas.cb16.flat_fanout.v1',netlist_sha256=hashlib.sha256(raw).hexdigest(),mapped_cells=len(m['cells']),flops=len(drivers),maximum_register_loads=reg[0]['loads'],register_violations=viol,top_register_loads=reg[:20],flag_port_direction=m['ports']['vld']['direction'],flag_ports=len(flags),flag_max_loads=max(hist.values()),flag_loads=hist,scope='native flattened mapped netlist; excludesclock/power; output flag pins require linked receiver loads')
Path(a.out).write_text(json.dumps(result,indent=1)+'\n');print('FLAT_FANOUT',a.top,'flops',len(drivers),'maxreg',reg[0]['loads'],'flagports',len(flags),'maxflag',max(hist.values()),'violations',len(viol))
if viol or(m['ports']['vld']['direction']=='input'and max(hist.values())>32):raise SystemExit(1)
