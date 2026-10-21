import json,sys,re,hashlib
from pathlib import Path
p=Path('/srv/opentallas-scratch/claude/ref_gate/codex_s5_1020');sys.path.insert(0,str(p/'admission042/tools'));sys.path.insert(0,str(p/'admission042/tools/ref_tile'));import native_census as C;import textbook_lint as T
base=p.parent/'qkd_kvs_grp_h_s4b-20261019-221603/src';libs=sorted(p.glob('*.lib'))+[base/'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/ot_sram_1r1w_128x256_m1_r2c2_p192_mir_tt.lib'];roles,receipt=C.liberty_roles(libs)
for top in ['qkd_kvs_grp_s5','qkd_kvs_grp_h_s5']:
 v=p/(top+'.mapped.v');mods=T.parse_verilog(v.read_text());mods={k:m for k,m in mods.items() if k==top or k not in roles};g,_=T.flatten(mods,top)
 dump={'macros':[dict(name=n,master=t,pins=[[pn,0,0,pr['direction'].upper()] for pn,pr in roles[t]['pins'].items()]) for t,n,pins in g.cells if 'ASAP7' not in t]};a=T.build(g,dump)
 for ci,(typ,n,pins) in enumerate(g.cells):
  for pn in pins:
   role=roles[typ]['pins'].get(pn) or roles[typ]['pins'].get(re.sub(r'\[.*','',pn));assert role is not None,(typ,pn)
   assert a['pin_dir'][ci][pn]==('in' if role['direction']=='input' else 'out'),(typ,pn,a['pin_dir'][ci][pn],role)
 def stop(ci):return roles[g.cells[ci][0]]['sequential'] or a['kind'][ci]=='macro'
 clocks,_=T.clock_nets(g,a);outs={x:n for n,(d,x) in g.ports.items() if d=='output'};inputs={};outputs={}
 for pn,(dr,root) in g.ports.items():
  if dr!='input' or root in clocks:continue
  todo=[(root,0)];seen={};ends={};direct=[]
  while todo:
   x,l=todo.pop()
   if seen.get(x,-1)>=l:continue
   seen[x]=l;assert l<len(g.cells)
   if x in outs:direct.append(outs[x])
   for ci,cp,bi in a['loads'].get(x,[]):
    typ,n,pins=g.cells[ci]
    pr=roles[typ]['pins'].get(cp) or roles[typ]['pins'].get(re.sub(r'\[.*','',cp));
    if pr['clock']:continue
    if stop(ci):ends[n+'/'+cp]=max(l,ends.get(n+'/'+cp,-1));continue
    dl=0 if a['kind'][ci] in ['buf','tie'] else 1
    for y in T._out_nets(g,a,ci):todo.append((y,l+dl))
  inputs[pn]=dict(endpoints=len(ends),max_levels=max(ends.values(),default=None),min_levels=min(ends.values(),default=None),examples=sorted(ends.items(),key=lambda q:-q[1])[:4],combinational_output_bits=direct)
 for pn,(dr,root) in g.ports.items():
  if dr!='output':continue
  todo=[(root,0)];seen={};ends={};constants=[];ports=[]
  while todo:
   x,l=todo.pop()
   if seen.get(x,-1)>=l:continue
   seen[x]=l;d=a['driver'].get(x)
   if d is None or x<=3:constants.append(x);continue
   ci,cp=d
   if ci<0:ports.append(cp);continue
   typ,n,pins=g.cells[ci]
   if stop(ci):ends[n+'/'+cp]=max(l,ends.get(n+'/'+cp,-1));continue
   if a['kind'][ci]=='tie':constants.append(x);continue
   dl=0 if a['kind'][ci]=='buf' else 1
   for y in T._in_nets(g,a,ci,False):todo.append((y,l+dl))
  outputs[pn]=dict(sequential_frontiers=len(ends),max_levels=max(ends.values(),default=None),input_ports=ports,constant_only=not ends and not ports,examples=sorted(ends.items(),key=lambda q:-q[1])[:2])
 result=dict(top=top,netlist_sha256=hashlib.sha256(v.read_bytes()).hexdigest(),roles_verified_all_cells=True,liberty=receipt,inputs=inputs,outputs=outputs,combinational_input_output_bits=sum(bool(q['combinational_output_bits']) for q in inputs.values()),max_input_levels=max((q['max_levels'] or 0) for q in inputs.values()),max_output_levels=max((q['max_levels'] or 0) for q in outputs.values()))
 (p/(top+'.io_frontier.json')).write_text(json.dumps(result,indent=1)+'\n');print(top,'IO',result['combinational_input_output_bits'],result['max_input_levels'],result['max_output_levels'],'straps',{n:r for n,r in inputs.items() if 'cfg_' in n},flush=True)
