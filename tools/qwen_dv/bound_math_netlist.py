#!/usr/bin/env python3
"""Emit fixed-shape structural math with recursively bounded data fanout.

Input is a Yosys synth -noabc -nofsm -noshare flattened JSON. Each retained
cell has its own parameterized hierarchy identity; overloaded FFs capture the
same D at the same edge. Added copies' input loads participate in subsequent
passes. This is source construction, never mapped timing qualification.
"""
import argparse,copy,hashlib,json
from collections import defaultdict
from pathlib import Path

GATES={'$_AND_':'A & B','$_OR_':'A | B','$_XOR_':'A ^ B','$_XNOR_':'~(A ^ B)',
       '$_NOT_':'~A','$_MUX_':'S ? B : A','$_NAND_':'~(A & B)','$_NOR_':'~(A | B)',
       '$_ANDNOT_':'A & ~B','$_ORNOT_':'A | ~B'}
FFS={'$_DFF_P_','$_DFF_PN0_','$_DFF_PP0_','$_DFF_PN1_','$_DFF_PP1_',
     '$_SDFF_PN0_','$_SDFF_PP0_','$_SDFF_PN1_','$_SDFF_PP1_'}

def build(raw,top,new):
 design=json.loads(raw);m=copy.deepcopy(design['modules'][top]);cells=m['cells'];ports=m['ports']
 nextbit=max(b for c in cells.values() for bs in c['connections'].values() for b in bs if isinstance(b,int))+1
 # Retained output-copy boundaries are real logic, not black-box stand-ins.
 # Expand every such source module into its actual generic FF cells.
 while True:
  nested=[(n,c) for n,c in cells.items() if c['type'] in design['modules']]
  if not nested:break
  for n,c in nested:
   sub=design['modules'][c['type']];mapping={}
   assert not int(sub.get('attributes',{}).get('blackbox','0'),2),c['type']
   for p,v in sub['ports'].items():
    assert len(v['bits'])==len(c['connections'][p])
    for b,d in zip(v['bits'],c['connections'][p]):mapping[b]=d
   for sc in sub['cells'].values():
    for bs in sc['connections'].values():
     for b in bs:
      if isinstance(b,int) and b not in mapping:mapping[b]=nextbit;nextbit+=1
   del cells[n]
   for sn,sc in sub['cells'].items():
    cc=copy.deepcopy(sc);cc['connections']={p:[mapping[b] if isinstance(b,int) else b for b in bs] for p,bs in sc['connections'].items()};cells[n+'/'+sn]=cc
 cells={n:c for n,c in cells.items() if c['type']!='$scopeinfo'}
 assert all(c['type'] in GATES or c['type'] in FFS for c in cells.values()),sorted({c['type'] for c in cells.values() if c['type'] not in GATES and c['type'] not in FFS})
 original=len(cells);added=defaultdict(int)
 for iteration in range(100):
  sinks=defaultdict(list);drivers={}
  for n,c in cells.items():
   for p,bs in c['connections'].items():
    for i,b in enumerate(bs):
     if not isinstance(b,int):continue
     if c['port_directions'][p]=='output':
      assert b not in drivers,(b,n,drivers.get(b));drivers[b]=(n,p,i)
     elif p!='C':sinks[b].append((1,'cell',n,p,i))
  for n,p in ports.items():
   if p['direction']=='output':
    for i,b in enumerate(p['bits']):
     if isinstance(b,int):sinks[b].append((16 if n=='valid_rep' else 5 if n=='valid_out' else 1,'port',n,None,i))
  overloaded=[(b,x) for b,x in sinks.items() if sum(v[0] for v in x)>32]
  if not overloaded:break
  # Reverse cell order helps process a downstream copy before its parents.
  for b,x in reversed(overloaded):
   if b not in drivers:raise ValueError(f'input bit{b} exceeds32 loads; source producer replicas required')
   n,p,i=drivers[b];c=cells[n];assert sum(len(bs) for pn,bs in c['connections'].items() if c['port_directions'][pn]=='output')==1
   chunks=[];part=[];cost=0
   for sink in x:
    if part and cost+sink[0]>32:chunks.append(part);part=[];cost=0
    part.append(sink);cost+=sink[0]
   chunks.append(part)
   for j,chunk in enumerate(chunks[1:],1):
    cn=f'{n}__bounded_{iteration}_{j}';assert cn not in cells
    cc=copy.deepcopy(c);cc['connections'][p][i]=nextbit;cells[cn]=cc;added[c['type']]+=1
    for _,kind,sn,sp,si in chunk:
     if kind=='cell':cells[sn]['connections'][sp][si]=nextbit
     else:ports[sn]['bits'][si]=nextbit
    nextbit+=1
 else:raise ValueError('fanout replication did not converge')
 def bit(b):
  if isinstance(b,int):return f'n[{b}]'
  assert b in ('0','1','x','z');return "1'b"+b
 def bus(bs):return bit(bs[0]) if len(bs)==1 else '{'+','.join(bit(b) for b in reversed(bs))+'}'
 lines=['// Generated fixed production-shape math. No extra arithmetic edges.',f'module {new}('+','.join(ports)+');']
 for n,p in ports.items():lines.append(f"{p['direction']} wire [{len(p['bits'])-1}:0] {n};")
 lines.append(f'wire [{nextbit-1}:0] n;')
 for n,p in ports.items():lines.append(f'assign '+(bus(p['bits'])+' = '+n if p['direction']=='input' else n+' = '+bus(p['bits']))+';')
 used=set()
 for idx,(n,c) in enumerate(cells.items()):
  typ=c['type'];used.add(typ);mod='qfd_bmath_'+typ.strip('$_').lower()
  con=','.join('.'+p+'('+bus(bs)+')' for p,bs in c['connections'].items())
  lines.append(f'(* keep_hierarchy="yes" *) {mod} #(.ID({idx})) u_{idx}({con});')
 lines.append('endmodule')
 helpers=[]
 for typ in sorted(used):
  con=next(c for c in cells.values() if c['type']==typ)
  mod='qfd_bmath_'+typ.strip('$_').lower()
  h=[f'(* keep_hierarchy="yes" *) module {mod} #(parameter integer ID=0)('+','.join(con['connections'])+');']
  for p in con['connections']:h.append(('output reg' if typ in FFS and p=='Q' else 'output wire' if con['port_directions'][p]=='output' else 'input wire')+' '+p+';')
  if typ in GATES:h.append('assign Y='+GATES[typ]+';')
  elif typ=='$_DFF_P_':h.append('always @(posedge C) Q<=D;')
  else:
   polarity,val=typ[-3:-1];edge='negedge' if polarity=='N' else 'posedge';test='!R' if polarity=='N' else 'R'
   event='posedge C' if typ.startswith('$_SDFF') else f'posedge C or {edge} R'
   h.append(f"always @({event}) if({test}) Q<=1'b{val};else Q<=D;")
  h.append('endmodule');helpers.append('\n'.join(h))
 return '\n'.join(lines)+'\n',helpers,dict(original_cells=original,final_cells=len(cells),added_by_type=dict(added),passes=iteration,input_sha256=hashlib.sha256(raw).hexdigest(),max_data_reset_loads=32,clock_only_excluded=True,output_boundary_assumptions={'valid_rep_each':16,'valid_out':5,'data_error_each':1},qualification='STRUCTURAL_CONSTRUCTION_ONLY; exact equivalence and mapped clocks/timing/area required')

def main():
 p=argparse.ArgumentParser();p.add_argument('json');p.add_argument('--top',required=True);p.add_argument('--name',required=True);p.add_argument('--out',required=True);p.add_argument('--helpers',required=True);p.add_argument('--record',required=True);a=p.parse_args()
 s,h,r=build(Path(a.json).read_bytes(),a.top,a.name);Path(a.out).write_text(s);Path(a.helpers).write_text('\n'.join(h)+'\n');Path(a.record).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
