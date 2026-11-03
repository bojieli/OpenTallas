import re,json
from pathlib import Path
root=Path(__file__).parent
text=(root/'1_2_yosys.v').read_text()
text=text[text.index('module ot_s81hd_tile_p('):]
text=text[:text.index('endmodule')]
cells={};drivers={}
for m in re.finditer(r'^  (\S+)\s+(\S+)\s+\(\n(.*?)^  \);',text,re.M|re.S):
 master,name,body=m.groups();name=name.lstrip('\\')
 ports={p:n.strip().lstrip('\\') for p,n in re.findall(r'\.(\w+)\(([^()]*)\)',body)}
 cells[name]={'master':master,'ports':ports}
 for p in ('Y','QN','Q'):
  if p in ports:drivers.setdefault(ports[p],[]).append((name,p))
roots=[f'u_core.{n}$_DFF_P_' for n in ('kh_gt','kh_eq','kl_gt','kl_eq','rl_q')]
result={};allcomb=set();allboundary=set()
for name in roots:
 assert name in cells,name
 stack=[cells[name]['ports']['D']];seen=set();comb=set();boundary=set();unknown=set()
 while stack:
  n=stack.pop()
  if n in seen:continue
  seen.add(n)
  if re.match(r"\d+'",n):continue
  ds=drivers.get(n,[])
  if len(ds)!=1:unknown.add(n);continue
  cn,port=ds[0];c=cells[cn]
  if c['master'].startswith('DFF'):
   boundary.add(cn);continue
  comb.add(cn)
  stack.extend(v for p,v in c['ports'].items() if p not in ('Y','QN','Q'))
 result[name]={'comb_count':len(comb),'boundaries':sorted(boundary),'unknown':sorted(unknown),'comb':sorted(comb)}
 allcomb|=comb;allboundary|=boundary
out={'scope':'SOURCE_ONLY original mapped combinational closure, not current buffered-route full closure','parsed_cells':len(cells),'captures':result,'unique_comb':len(allcomb),'unique_boundary_ff':len(allboundary),'all_comb':sorted(allcomb),'all_boundary_ff':sorted(allboundary)}
(root/'cone.json').write_text(json.dumps(out,indent=1)+'\n')
(root/'cone_names.json').write_text(json.dumps(sorted(allcomb|allboundary|set(roots))))
print('cells',len(cells),'comb',len(allcomb),'boundary',len(allboundary))
for k,v in result.items():print(k,v['comb_count'],'FF',len(v['boundaries']),'unknown',v['unknown'])
