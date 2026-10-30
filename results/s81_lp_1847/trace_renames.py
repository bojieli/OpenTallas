"""Locate real mapped flops behind the four missing LP kept names."""
import hashlib
import json
import re
import sys
from pathlib import Path

p=Path(sys.argv[1])
s=p.read_text()
nodes={'_15858_':('u.u_ep.rdy_k[3]','u.u_ep.in_ready'),
       '_18098_':('u.u_gb.g_pc[0].ps[5]','u.u_gb.g_pc[0].g_b[0].a0'),
       '_18030_':('u.u_gb.g_pc[11].ps[3]','u.u_gb.g_pc[11].g_b[280].a2'),
       '_18067_':('u.u_gb.g_pc[5].ps[4]','u.u_gb.g_pc[5].g_b[140].a1')}
found={}
for m in re.finditer(r'(?m)^\s*([A-Za-z][\w]*)\s+(\\[^\s]+|[^\s(]+)\s+\((.*?)\);',s,re.S):
    typ,inst,ports=m.groups()
    if not typ.startswith('DFF'): continue
    for n,(gold,gate) in nodes.items():
        if re.search(r'\.QN?\(\s*'+re.escape(n)+r'\s*\)',ports):
            if n in found: raise ValueError('nonunique physical driver '+n)
            assert inst.lstrip('\\').startswith(gate+'$_DFF'),(gate,inst)
            found[n]={'gold':gold,'gate':gate,'cell':typ,'instance':inst,'ports':ports.strip()}
if set(found)!=set(nodes): raise ValueError('missing physical drivers')
print(json.dumps({'netlist_sha256':hashlib.sha256(s.encode()).hexdigest(),
                  'verdict':'4_PHYSICAL_FLOPS_LOCATED_NOT_FORMAL_PROOF','flops':found},indent=2))
