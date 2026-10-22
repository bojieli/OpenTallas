#!/usr/bin/env python3
"""Independent re-read of emitted primitive equations, state bindings and ports."""
import argparse,collections,hashlib,importlib.util,json,pathlib,re
p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('emitted');p.add_argument('certificate');a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[3];sp=importlib.util.spec_from_file_location('lint',root/'tools/textbook_lint.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
raw=pathlib.Path(a.source).read_text();cert=json.loads(pathlib.Path(a.certificate).read_text());assert hashlib.sha256(raw.encode()).hexdigest()==cert['source_sha256']
g,top=T.flatten(T.parse_verilog(raw),None);emods=T.parse_verilog(pathlib.Path(a.emitted).read_text());assert list(emods)==['qkd_kvs_attn_safe_control'];m=emods['qkd_kvs_attn_safe_control']
origins=cert['origins'];assert origins[:len(g.cells)]==list(range(len(g.cells)));assert len(m.insts)==len(origins)
eq={};emitted={n:(t,pins) for t,n,pins in m.insts};assert len(emitted)==len(origins)
for item in cert['copies']:
 ci,parent=item['copy'],item['parent'];assert len(g.cells)<=ci<len(origins) and 0<=parent<ci;assert origins[ci]==origins[parent]
 assert item['output'] not in eq;eq[item['output']]=item['split_net']
 # Correspondence only permits a new output to map to that exact parent's
 # same primitive output, never to a forged arbitrary equivalence class.
 typ,pins=emitted[f'c{parent}'];assert item['split_net'] in [int(bits[0][1:]) for pn,v in pins.items() for bits in [T.expr_bits(v,m.widths)] if pn in T.OUT_PINS and len(bits)==1 and re.fullmatch('n[0-9]+',bits[0])],(item,typ,pins)
def canonical(x):
 seen=set()
 while x in eq:
  assert x not in seen;seen.add(x);x=eq[x]
 return x
def toknet(tok):
 v=T.expr_bits(tok,m.widths);assert len(v)==1;v=v[0]
 if v in ("1'0","1'1","1'x","1'z"):return ("1'0","1'1","1'x","1'z").index(v)
 assert re.fullmatch('n[0-9]+',v),v;return int(v[1:])
for ci,oi in enumerate(origins):
 typ,pins=emitted[f'c{ci}'];bt,bn,bp=g.cells[oi];assert typ==bt,(ci,'master');assert set(pins)==set(bp),(ci,'pins')
 for pn,tok in pins.items():assert canonical(toknet(tok))==bp[pn][0],(ci,pn,'equation binding')
expected=[]
for b,(d,x) in g.ports.items():expected.append(([f'n{x}'],[b]) if d=='input' else ([b],[f'n{x}']))
actual=[(T.expr_bits(l,m.widths),T.expr_bits(r,m.widths)) for l,r in m.assigns]
assert sorted(actual)==sorted(expected),'public port binding'
eg,et=T.flatten(emods,None);A=T.build(eg,None);drivers=collections.Counter()
for ci,(typ,nm,pins) in enumerate(eg.cells):
 for pn,bs in pins.items():
  if A['pin_dir'][ci][pn]=='out':drivers.update(bs)
assert max(drivers.values())==1,'multiple drivers'
assert all(x<4 or x in A['driver'] for x in A['loads']),'undriven'
clock={x for b,(d,x) in eg.ports.items() if b=='ck'}
assert all(len(ls)<=32 for x,ls in A['loads'].items() if x not in clock and x>=4),'direct fanout'
max_terminal=0
for x in A['loads']:
 if x in clock or x<4:continue
 ci,pn=A['driver'][x]
 if ci>=0 and A['kind'][ci]=='buf':continue
 stack=[x];seen=set();ends=set()
 while stack:
  y=stack.pop()
  if y in seen:continue
  seen.add(y)
  for li,lp,bit in A['loads'].get(y,[]):
   if A['kind'][li]=='buf':stack.extend(z for op,bs in eg.cells[li][2].items() if A['pin_dir'][li][op]=='out' for z in bs)
   else:ends.add((li,lp,bit))
 max_terminal=max(max_terminal,len(ends));assert len(ends)<=32,'first-logic fanout'
print(json.dumps({'verdict':'PASS','cells':len(origins),'FF':sum(k=='ff' for k in A['kind']),'original_equations':len(g.cells),'new_same_equation_cells':len(origins)-len(g.cells),'direct_max':max(len(v) for x,v in A['loads'].items() if x not in clock and x>=4),'first_logic_max':max_terminal,'all_ports':len(g.ports),'native_timing_qualified':False}))
