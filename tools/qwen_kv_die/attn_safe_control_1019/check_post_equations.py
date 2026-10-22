import pathlib,importlib.util,json
r=pathlib.Path('.');sp=importlib.util.spec_from_file_location('lint',r/'tools/textbook_lint.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
g,top=T.flatten(T.parse_verilog((r/'candidate/qkd_kvs_attn_safe_control.v').read_text()),None);A=T.build(g,None)
p=r/'synth_fork_r2/results/asap7/opentallas_qkd_kvs_attn_safe_control_asap7_ref_gate/base/1_2_yosys.v';h,ht=T.flatten(T.parse_verilog(p.read_text()),None);B=T.build(h,None);idx={n:i for i,(t,n,ps) in enumerate(h.cells)};oldnames={n for t,n,ps in g.cells};anchors={i:i for i in range(4)}
for n,(d,x) in g.ports.items():
 assert n in h.ports and d==h.ports[n][0]
 if d=='input':anchors[h.ports[n][1]]=x
for ci,(typ,nm,pins) in enumerate(g.cells):
 hi=idx[nm];tt,nn,pp=h.cells[hi];assert typ==tt,(nm,typ,tt);assert set(pins)==set(pp)
 for pn,bs in pins.items():
  if A['pin_dir'][ci][pn]=='out':
   assert len(bs)==len(pp[pn])==1
   y=pp[pn][0];assert y not in anchors or anchors[y]==bs[0];anchors[y]=bs[0]
new=[]
for ci,(typ,nm,pins) in enumerate(h.cells):
 if nm not in oldnames:assert B['kind'][ci]=='buf',(nm,typ);new.append(ci)
def resolve(y):
 seen=set();parity=0
 while y not in anchors:
  assert y not in seen;seen.add(y);ci,pn=B['driver'][y];assert ci in new,(ci,h.cells[ci][1]);typ,nm,pins=h.cells[ci];parity^=int(T.INV_RE.search(typ)!=None) if hasattr(T,'INV_RE') else int(typ.startswith('INV'))
  v=[x for pn,bs in pins.items() if B['pin_dir'][ci][pn]=='in' for x in bs];assert len(v)==1;y=v[0]
 return anchors[y],parity
for ci,(typ,nm,pins) in enumerate(g.cells):
 hi=idx[nm];pp=h.cells[hi][2]
 for pn,bs in pins.items():
  if A['pin_dir'][ci][pn]=='in':assert resolve(pp[pn][0])==(bs[0],0),(nm,pn,resolve(pp[pn][0]),bs)
for n,(d,x) in g.ports.items():
 if d=='output':assert resolve(h.ports[n][1])==(x,0),(n,'public output')
print(json.dumps({'verdict':'PASS','original_native_equations':len(g.cells),'only_added_transparent_cells':len(new),'FF_clock_D_reset_bindings':'exact','public_bits':len(g.ports),'native_timing_qualified':False}))
