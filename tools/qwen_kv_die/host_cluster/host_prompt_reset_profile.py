#!/usr/bin/env python3
"""Derive exact two-edge landing counts, then falsify each graph obligation."""
from pathlib import Path
import copy,hashlib,importlib.util,json,sys
sp=importlib.util.spec_from_file_location('tl','textbook_lint.py');m=importlib.util.module_from_spec(sp);sys.modules['tl']=m;sp.loader.exec_module(m)
g,top=m.flatten(m.parse_verilog(Path('resynth.v').read_text()),'qkd_hr_core_prompt_n32');a=m.build(g,None)
port='u_rank__u_control__por_n';net=g.ports[port][1]
first={ci for ci,pn,bit in a['loads'].get(net,[])}
last=set()
def walk(x):
 seen=set();stack=[x]
 while stack:
  n=stack.pop()
  if n in seen:continue
  seen.add(n)
  for ci,pn,bit in a['loads'].get(n,[]):
   if a['kind'][ci]=='buf':stack.extend(m._out_nets(g,a,ci))
   else:last.add(ci)
for ci in first:
 for x in m._out_nets(g,a,ci):walk(x)
p=dict(schema='opentallas.ref_tile.reset_landing.v1',top=top,enable=True,stages=2,clock='ck_core',reset_ports=[port],first_copies={port:len(first)},copies={port:len(last)})
proof=m.balanced_reset_proof(g,a,port,net,p)
result=dict(profile=p,proof=proof,generated_sha256=hashlib.sha256(Path(top+'.sv').read_bytes()).hexdigest(),mapped_sha256=hashlib.sha256(Path('resynth.v').read_bytes()).hexdigest(),negatives={})
assert proof['pass'],proof
f=min(first);l=min(last)
for mode in ['root_D','clock','QN_polarity','bypass','extra_consumer','missing_stage']:
 h=copy.deepcopy(g);pp=copy.deepcopy(p)
 if mode in ('root_D','clock'):
  ci=f;typ,nm,pins=h.cells[ci];pins['D'if mode=='root_D'else'CLK']=[0]
 elif mode=='QN_polarity':
  # Force final-stage D to un-inverted first QN.
  q=list(m._out_nets(g,a,f))[0];h.cells[l][2]['D']=[q]
 elif mode=='bypass':h.cells[l][2]['D']=[net]
 elif mode=='extra_consumer':
  # An actual downstream async-reset contact appears directly on the root.
  ci=next(k for k,(ty,nm,pins) in enumerate(h.cells) if k not in first|last and 'RESETN'in pins)
  h.cells[ci][2]['RESETN']=[net]
 elif mode=='missing_stage':h.cells[l][2]['D']=[0]
 aa=m.build(h,None);r=m.balanced_reset_proof(h,aa,port,net,pp);assert not r['pass'],mode
 result['negatives'][mode]=r
Path('reset_profile.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
