from pathlib import Path
import importlib.util,sys,json,hashlib,gc
root=Path(__file__).resolve().parent;parser=root/'textbook_lint.py';sp=importlib.util.spec_from_file_location('T',parser);T=importlib.util.module_from_spec(sp);sys.modules['T']=T;sp.loader.exec_module(T)
assert hashlib.sha256(parser.read_bytes()).hexdigest()=='4adb3e6072ab0e5d93ddaa5205d5139c37971aa87175b1923beea9261dd2619b'
def estimate(path,portprefix):
 raw=path.read_bytes();g,top=T.flatten(T.parse_verilog(raw.decode()),None);A=T.build(g,None);clk,_=T.clock_nets(g,A);order=T.topo(g,A,clk);q={};lev={};pred={};scale=T.THRESHOLDS['depth_scale']
 for c,kind in enumerate(A['kind']):
  if kind in ['ff','macro']:
   for n in T._out_nets(g,A,c):q[n]=(0.0,g.cells[c][1]);lev[n]=0
 for c in order:
  if A['kind'][c] not in ['comb','buf']:continue
  inputs=[n for n in T._in_nets(g,A,c,False) if n in q]
  if not inputs:continue
  best=max(inputs,key=lambda n:q[n][0]);depth,start=q[best];weight=T.cell_w(g.cells[c][0]);levels=max(lev[n] for n in inputs)+(A['kind'][c]!='buf')
  for n in T._out_nets(g,A,c):q[n]=(depth+weight,start);lev[n]=levels;pred[n]=(best,c)
 outputs=[]
 for name,(d,n) in g.ports.items():
  if d=='output' and name.startswith(portprefix+'[') and n in q:outputs.append((q[n][0]*scale,name,n))
 outputs.sort(reverse=True);assert len(outputs)==32
 traces=[]
 for depth,name,n in outputs[:3]:
  chain=[];seen=set();x=n
  while x in pred:
   assert x not in seen;seen.add(x);up,c=pred[x];chain.append(dict(instance=g.cells[c][1],master=g.cells[c][0],weight_ps=T.cell_w(g.cells[c][0])*scale));x=up
  traces.append(dict(endpoint=name,estimate_ps=round(depth,1),logic_levels=lev[n],start=q[n][1],cone=list(reversed(chain))))
 worst=(0,None,None)
 for c,kind in enumerate(A['kind']):
  if kind not in ['ff','macro','icg']:continue
  for pn,bs in g.cells[c][2].items():
   if A['pin_dir'][c].get(pn)!='in' or pn in T.SEQ_CLK_PINS:continue
   for n in bs:
    if n in q and q[n][0]*scale>worst[0]:worst=(q[n][0]*scale,q[n][1],g.cells[c][1]+'/'+pn)
 r=dict(netlist=str(path),sha256=hashlib.sha256(raw).hexdigest(),top=top,cells=len(g.cells),flops=A['kind'].count('ff'),macros=A['kind'].count('macro'),address_outputs=[dict(endpoint=name,estimate_ps=round(depth,1),levels=lev[n],start=q[n][1]) for depth,name,n in outputs],worst_address_traces=traces,reg_to_reg_worst=dict(estimate_ps=round(worst[0],1),start=worst[1],end=worst[2]));return r
for name,sha in json.loads((root/'readset_sha256.json').read_text()).items():
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
out={'scope':'exact actual production mapped graph, unchanged textbook scalar weights; no native copy/placement/wire/load/slew or STA qualification','parser_sha256':hashlib.sha256(parser.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'depth_scale':T.THRESHOLDS['depth_scale']}
out['current_qualified_prefix']=estimate(root/'old.v','w_addr');gc.collect();out['selected_late_ring_production']=estimate(root/'new.v','w_addr');Path('production_map_estimate.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:{'worst_address':v['address_outputs'][0],'reg_to_reg_worst':v['reg_to_reg_worst']} for k,v in out.items() if isinstance(v,dict)}))
