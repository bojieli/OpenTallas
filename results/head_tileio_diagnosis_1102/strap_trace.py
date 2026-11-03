from pathlib import Path
import json,re
root=Path(__file__).parent
src=(root/'physical_cone.py').read_text().split('roots=')[0]
exec(compile(src,'physical_cone_parser','exec'))
roots=['u_core.b_en$_DFF_P_']+[f'u_core.row0_q[{i}]$_DFF_P_' for i in range(17)]
results={}
for rn in roots:
 stack=[cells[rn]['ports']['D']];seen=set();comb=set();regs=set();launch=set()
 while stack:
  n=stack.pop()
  if n in seen:continue
  seen.add(n)
  if re.match(r"\d+'",n):continue
  ds=drivers.get(n,[])
  if not ds:launch.add(n);continue
  assert len(ds)==1,(rn,n,ds)
  cn,port=ds[0];c=cells[cn]
  if c['master'].startswith('DFF'):regs.add(cn);continue
  comb.add(cn)
  stack.extend(v for p,v in c['ports'].items() if p not in ('Y','QN','Q','VDD','VSS'))
 results[rn]=dict(D=cells[rn]['ports']['D'],combinational=[dict(name=n,**cells[n]) for n in sorted(comb)],register_boundaries=sorted(regs),launch_nets=sorted(launch))
expected={'u_core.b_en$_DFF_P_':{'strap_ten[0]'}}
expected.update({f'u_core.row0_q[{i}]$_DFF_P_':{f'strap_row0[{i}]'} for i in range(17)})
for n,d in results.items():
 assert not d['register_boundaries'],(n,d)
 assert set(d['launch_nets'])==expected[n],(n,d)
out=dict(scope='read-only finalnativeVerilog structural D fanin trace, no constraint-count waiver',all18_only_declared_strap_launch=True,results=results)
(root/'strap_trace.json').write_text(json.dumps(out,indent=1)+'\n')
print('all18 exact corresponding strap-only D cones; no FF launch boundary')
for n,d in results.items():print(n,'cells',len(d['combinational']),'launch',d['launch_nets'])
