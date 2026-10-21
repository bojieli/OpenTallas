import sys,pathlib,collections,json,importlib.util,re
r=pathlib.Path.cwd(); p=r/'src/tools/ref_tile/native_census.py';spec=importlib.util.spec_from_file_location('nc',p);nc=importlib.util.module_from_spec(spec);spec.loader.exec_module(nc)
mods=nc.TL.parse_verilog((r/'eng_readonly/mapped.v').read_text());mods={k:v for k,v in mods.items() if not k.startswith('ot_sram')};g,_=nc.TL.flatten(mods,'dsdv_eng_rr');name='u_c.u_xq.u_aq.amax[15]$_SDFF_PP0_';cell=next(c for c in g.cells if c[1]==name);print('ROOT',cell);nets=cell[2]['QN'];hits=[]
for master,n,pins in g.cells:
 if n==name:continue
 for pin,ns in pins.items():
  for x in ns:
   if x in nets:hits.append((master,n,pin))
roles,_=nc.liberty_roles([r/'out_mul_native'/n for n in ['ao.lib','invbuf.lib','oa.lib','seq.lib','simple.lib']])
loads=collections.defaultdict(set);transparent={}
for i,(m,n,pins) in enumerate(g.cells):
 role=roles.get(m)
 if not role:continue
 ins=[];outs=[]
 for pn,ns in pins.items():
  q=role['pins'].get(pn,{})
  for net in ns:
   if q.get('direction')=='output':outs.append((net,q.get('function')))
   elif q.get('direction')=='input' and not q.get('clock'):loads[net].add((i,pn));ins.append((pn,net))
 if not role['sequential'] and len(ins)==len(outs)==1:
  pn,src=ins[0];dst,f=outs[0]
  if f is not None and re.sub(r'[\s()]','',f) in (pn,'!'+pn,'~'+pn,pn+"'"):transparent[i]=(src,dst)
todo=list(nets);seen=set();ends=set()
while todo:
 net=todo.pop()
 if net in seen:continue
 seen.add(net)
 for i,pn in loads[net]:
  if i in transparent:todo.append(transparent[i][1])
  else:ends.add((i,pn))
hits=[(g.cells[i][0],g.cells[i][1],pn) for i,pn in sorted(ends)]
print('DYNAMIC_PINS',len(hits));print('GROUPS',collections.Counter('.'.join(n.split('.')[:-1]) for _,n,_ in hits));(r/'eng_readonly/amax15_dynamic_consumers.json').write_text(json.dumps(hits,indent=2)+'\n')
