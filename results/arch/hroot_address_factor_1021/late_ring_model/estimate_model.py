from pathlib import Path
import importlib.util,sys,json,hashlib,collections
root=Path('/srv/opentallas-scratch/claude/codex-hroot-address-1021');P=root/'source/textbook_lint.py';sp=importlib.util.spec_from_file_location('T',P);T=importlib.util.module_from_spec(sp);sys.modules['T']=T;sp.loader.exec_module(T)
assert hashlib.sha256(P.read_bytes()).hexdigest()=='4adb3e6072ab0e5d93ddaa5205d5139c37971aa87175b1923beea9261dd2619b'
out={'scope':'same-flow bounded combinational four-final-address projection model only; primary input to output scalar depth, no fullproduction reconvergence/mux, no STA/wire/load/slew/corner or qualification','parser_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'depth_scale':T.THRESHOLDS['depth_scale']}
for top in ['original','current_baseline','late_ring_model']:
 p=Path(top+'.mapped.v');g,_=T.flatten(T.parse_verilog(p.read_text()),None);A=T.build(g,None);clk,_=T.clock_nets(g,A);order=T.topo(g,A,clk);q={n:0 for name,(d,n) in g.ports.items() if d=='input'};lev={n:0 for n in q};pred={};start={n:name for name,(d,n) in g.ports.items() if d=='input'}
 for c in order:
  if A['kind'][c] not in ['comb','buf']:continue
  ins=[n for n in T._in_nets(g,A,c,False) if n in q]
  if not ins:continue
  b=max(ins,key=lambda n:q[n]);w=T.cell_w(g.cells[c][0]);l=max(lev[n] for n in ins)+(A['kind'][c]!='buf')
  for n in T._out_nets(g,A,c):q[n]=q[b]+w;lev[n]=l;pred[n]=(b,c);start[n]=start[b]
 outputs=[]
 for name,(d,n) in g.ports.items():
  if d=='output' and n in q:
   chain=[];x=n
   while x in pred:
    x,c=pred[x];chain.append({'instance':g.cells[c][1],'master':g.cells[c][0]})
   outputs.append({'endpoint':name,'estimate_ps':round(q[n]*T.THRESHOLDS['depth_scale'],1),'levels':lev[n],'start':start[n],'cone':list(reversed(chain))})
 groups={label:max([o for o in outputs if lo<=int(o['endpoint'].split('[')[1][:-1])<lo+32],key=lambda o:o['estimate_ps']) for label,lo in [('scale',0),('code',32),('rows',64),('raw',96)]}
 out[top]={'mapped_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'cells':len(g.cells),'kinds':dict(collections.Counter(A['kind'])),'worst_by_address':groups}
Path('model_estimate.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({t:{k:(v['estimate_ps'],v['levels'],v['start']) for k,v in out[t]['worst_by_address'].items()} for t in ['original','current_baseline','late_ring_model']}))
