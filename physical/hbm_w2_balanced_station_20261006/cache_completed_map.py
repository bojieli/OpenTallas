#!/usr/bin/env python3
"""Pin a completed Yosys map for P&R variants while the original route runs."""
import argparse, hashlib, json, shlex
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);a=p.parse_args()
w=a.work.resolve();r=a.source_root.resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
log=(w/'yosys.log').read_text();assert 'End of script.' in log and 'ERROR:' not in log
recipe=(w/'synth.ys').read_text(); sources=[];libs=set();params={}
started=(w/'synth.ys').stat().st_mtime
for line in recipe.splitlines():
 t=shlex.split(line)
 if t[:2]==['read_verilog','-sv']:
  s=Path(t[-1]);assert s.stat().st_mtime<=started
  sources.append(dict(path=str(s.relative_to(r)),sha256=sha(s)))
 if t and t[0]=='hierarchy':
  for n,x in enumerate(t):
   if x=='-chparam':params[t[n+1]]=int(t[n+2])
 for n,x in enumerate(t):
  if x=='-liberty':libs.add(Path(t[n+1]))
assert sources and libs and params==dict(ENABLE=1,NO=2,REGISTERED_CURRENT=1,REGISTERED_CHECK=1)
for path in libs:assert path.stat().st_mtime<=started, 'library changed after map began'
inventory=json.loads((w.parent/'mapped_inventory.json').read_text())
assert sha(w/'mapped.v')==inventory['netlist_normalization']['normalized_netlist_sha256']
# Normalized mapped.v is emitted after the successful log; its digest is checked above.
for f in ['mapped.raw.v','stat.txt']:assert (w/f).stat().st_mtime<=(w/'yosys.log').stat().st_mtime
record=dict(schema='completed-yosys-map-for-route-reuse-v1',terminal='PASS',route_terminal=False,
 design=dict(parameters=params,sources=sources),corner=dict(liberty=[dict(path=str(x),sha256=sha(x)) for x in sorted(libs)]),
 artifacts={x:sha(w/x) for x in ['synth.ys','yosys.log','mapped.raw.v','mapped.v','stat.txt']},
 basis='Successful Yosys end-of-script, original mapped-inventory digest, original source/library files unchanged since recipe creation; no route status inferred')
out=w.parent/'completed_map.json';assert not out.exists();out.write_text(json.dumps(record,indent=2)+'\n')
print(out)
