import sys,json,hashlib
from pathlib import Path
x=Path(sys.argv[1]);raw=x.read_bytes();d=json.loads(raw)['modules']['qfd_dv_redstn2'];drivers={};ff={};roots=[]
for p in d['ports'].values():
 if p['direction']=='output':roots.extend(p['bits'])
for n,c in d['cells'].items():
 if c['type'].startswith(('$_DFF','$_SDFF')):ff[n]=c
 for p,bs in c['connections'].items():
  if c['port_directions'][p]=='output':
   for b in bs:
    if isinstance(b,int):drivers[b]=n
 if c['type']=='ot_sram_1r1w_32x64_m1':
  roots.extend(b for p,bs in c['connections'].items() if c['port_directions'][p]=='input' and p!='clk' for b in bs)
seenbits=set();seen=set()
while roots:
 b=roots.pop()
 if not isinstance(b,int) or b in seenbits:continue
 seenbits.add(b);n=drivers.get(b)
 if n is None or n in seen:continue
 seen.add(n);c=d['cells'][n]
 roots.extend(b for p,bs in c['connections'].items() if c['port_directions'][p]=='input' and p not in ('C','CLK','clk','ck') for b in bs)
dead=[n for n in ff if n not in seen]
r=dict(netlist_sha256=hashlib.sha256(raw).hexdigest(),scope='Backward sequential+combinational reachability from actual top outputs and real native memory data/control input pins; excludes clocks; no functional-correlation or physical timing inference',total_ff=len(ff),ff_outside_functional_boundary_cones=len(dead),examples=dead[:40])
Path(sys.argv[2]).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
