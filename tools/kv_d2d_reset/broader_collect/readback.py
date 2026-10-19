#!/usr/bin/env python3
"""Independent emitted-source congruence and initialization inventory.
Does not consume emitter Boolean claims or its copy-output substitution list.
"""
import collections,hashlib,importlib.util,json,pathlib,sys
root=pathlib.Path(__file__).parent
sp=importlib.util.spec_from_file_location('lint',root/'tools/textbook_lint.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
mode=sys.argv[1];top='qkd_d2d_static'+('_ovl' if mode=='ovl' else '')
bp=root/f'{mode}.kept_native.v';ep=root/f'{mode}_reuse/{top}_safe24.v';cp=root/f'{mode}_reuse/correspondence.json'
bg,bt=T.flatten(T.parse_verilog(bp.read_text()),None);eg,et=T.flatten(T.parse_verilog(ep.read_text()),None)
cert=json.loads(cp.read_text());origin=cert['origins'];assert cert['source_sha256']==hashlib.sha256(bp.read_bytes()).hexdigest()
md={'macros':[{'name':n,'master':t,'pins':[(pn,0,0,'OUTPUT' if pn=='rd_out' else 'INPUT') for pn in p]} for t,n,p in bg.cells if t.startswith('ot_sram_')]};B=T.build(bg,md)
# Output pin classes are reconstructed from emitted native instances and original
# masters, without trusting the generator's rewiring/copy history.
assert len(eg.cells)==len(origin);canonical={0:0,1:1,2:2,3:3};names={n:(i,t,p) for i,(t,n,p) in enumerate(eg.cells)}
for i,oi in enumerate(origin):
 t,n,p=eg.cells[i];ot,on,op=bg.cells[oi];assert n==f'c{i}' and t==ot and set(p)==set(op)
 for pin,bs in p.items():
  if B['pin_dir'][oi][pin]=='out':
   assert len(bs)==len(op[pin]);
   for x,y in zip(bs,op[pin]):assert canonical.setdefault(x,y)==y,('multiple output class',x)
for pin,(direction,x) in eg.ports.items():
 assert pin in bg.ports and bg.ports[pin][0]==direction
 if direction=='input':assert canonical.setdefault(x,bg.ports[pin][1])==bg.ports[pin][1]
for i,oi in enumerate(origin):
 for pin,bs in eg.cells[i][2].items():assert [canonical[x] for x in bs]==bg.cells[oi][2][pin],('equation mismatch',i,pin)
for pin,(direction,x) in eg.ports.items():assert canonical[x]==bg.ports[pin][1],('port mismatch',pin)
assert all(t==ot for (t,n,p),(ot,on,op) in zip(eg.cells[:len(bg.cells)],bg.cells))
clones=[]
for i,oi in enumerate(origin):
 if i<len(bg.cells) or B['kind'][oi]!='ff':continue
 typ,name,pins=bg.cells[oi];row=dict(copy=i,origin=oi,original_name=name,master=typ,pins=pins)
 # Trace original D's combinational cone to its FF or input boundaries. A
 # self-feedback path disproves the emitter's unconditional first-edge claim.
 stack=list(pins['D']);seen=set();ffroots=set();ports=[]
 while stack:
  b=stack.pop()
  if b in seen:continue
  seen.add(b);drv=B['driver'].get(b)
  if not drv or drv[0]<0:ports.append(b);continue
  ci,pn=drv
  if B['kind'][ci]=='ff':ffroots.add(ci);continue
  if B['kind'][ci]=='macro':continue
  stack.extend(x for pin,bs in bg.cells[ci][2].items() if B['pin_dir'][ci][pin]=='in' for x in bs)
 row.update(has_async_pins=('RESETN'in pins),self_feedback=oi in ffroots,upstream_ff_count=len(ffroots),upstream_ffs=sorted(ffroots))
 clones.append(row)
result=dict(source_sha256=hashlib.sha256(bp.read_bytes()).hexdigest(),emitted_sha256=hashlib.sha256(ep.read_bytes()).hexdigest(),cells=len(eg.cells),source_cells=len(bg.cells),all_native_pin_equations_and_ports_congruent=True,induction_requires_corresponding_initial_states=True,source_equivalence_proved=False,source_equivalence_status="REFUSED_UNPROVED_INDEPENDENT_INITIAL_STATE_DOMINATION",missing_obligations=["arbitrary independent copy initialization", "cold writes dominate all data/status/fault consumers", "source clear and retrain startup"],clone_ff_count=len(clones),clone_classes=collections.Counter(('async' if x['has_async_pins'] else 'plain')+('_feedback' if x['self_feedback'] else '') for x in clones),cloned_flops=clones,qualified=False)
(root/f'{mode}.readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='cloned_flops'},indent=2))
