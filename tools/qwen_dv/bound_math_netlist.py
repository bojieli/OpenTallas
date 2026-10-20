#!/usr/bin/env python3
"""Emit fixed-shape structural math with recursively bounded data fanout.

Input is a Yosys synth -noabc -nofsm -noshare flattened JSON. Each retained
cell has its own parameterized hierarchy identity; overloaded FFs capture the
same D at the same edge. Added copies' input loads participate in subsequent
passes. This is source construction, never mapped timing qualification.
"""
import argparse,copy,hashlib,json
from collections import defaultdict,Counter
from pathlib import Path

GATES={'$_AND_':'A & B','$_OR_':'A | B','$_XOR_':'A ^ B','$_XNOR_':'~(A ^ B)',
       '$_NOT_':'~A','$_MUX_':'S ? B : A','$_NAND_':'~(A & B)','$_NOR_':'~(A | B)',
       '$_ANDNOT_':'A & ~B','$_ORNOT_':'A | ~B'}
FFS={'$_DFF_P_','$_DFF_PN0_','$_DFF_PP0_','$_DFF_PN1_','$_DFF_PP1_',
     '$_SDFF_PN0_','$_SDFF_PP0_','$_SDFF_PN1_','$_SDFF_PP1_'}

def build(raw,top,new,drop=(),collapse=False):
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
 for name in drop:
  assert name in ports and ports[name]['direction']=='output',name
  del ports[name]
 # Specialize actual output consumers before retaining any state. In data-only
 # lanes this removes the entire otherwise-unobserved valid pipeline.
 bybit={b:n for n,c in cells.items() for p,bs in c['connections'].items() if c['port_directions'][p]=='output' for b in bs if isinstance(b,int)}
 todo=[b for p in ports.values() if p['direction']=='output' for b in p['bits']];live=set();seen=set()
 while todo:
  b=todo.pop()
  if b in seen:continue
  seen.add(b)
  if b not in bybit:continue
  n=bybit[b]
  if n in live:continue
  live.add(n);todo.extend(b for p,bs in cells[n]['connections'].items() if cells[n]['port_directions'][p]=='input' for b in bs)
 removed=len(cells)-len(live);cells={n:c for n,c in cells.items() if n in live}
 unused_inputs=[n for n,p in ports.items() if p['direction']=='input' and not any(b in seen for b in p['bits'])]
 for n in unused_inputs:del ports[n]
 delay_chains=[];ring_groups=[]
 if collapse:
  users=defaultdict(list)
  for n,c in cells.items():
   for p,bs in c['connections'].items():
    if c['port_directions'][p]=='input':
     for i,b in enumerate(bs):users[b].append((n,p,i))
  for n,p in ports.items():
   if p['direction']=='output':
    for b in p['bits']:users[b].append((None,'output',0))
  plain={n:c for n,c in cells.items() if c['type']=='$_DFF_P_'};following={};pred={}
  for n,c in plain.items():
   q=c['connections']['Q'][0];u=users[q]
   if len(u)==1 and u[0][1]=='D' and u[0][0] in plain:
    dst=u[0][0]
    if c['connections']['C']==plain[dst]['connections']['C']:following[n]=dst;pred[dst]=n
  groups=defaultdict(list)
  for n in plain:
   if n in pred:continue
   chain=[n]
   while chain[-1] in following:
    nxt=following[chain[-1]]
    if nxt in chain:raise ValueError('holding-delay feedback cycle')
    chain.append(nxt)
   if len(chain)<3:continue
   if len(chain)>12:raise ValueError('holding chain exceeds finite ring shape')
   first,last=plain[chain[0]],plain[chain[-1]]
   row=dict(cells=chain,d=first['connections']['D'][0],q=last['connections']['Q'][0],clock=first['connections']['C'][0],depth=len(chain))
   delay_chains.append(row);groups[(row['depth'],row['clock'],len(users[row['q']])>32)].append(row)
  if delay_chains:
   if 'rst_n' not in ports:ports['rst_n']={'direction':'input','bits':[nextbit]};nextbit+=1
   rst=ports['rst_n']['bits'][0]
   for (depth,clock,high),rows in groups.items():
    size=1 if high else 32
    for start in range(0,len(rows),size):
     part=rows[start:start+size];name=f'$holding_ring_{len(ring_groups)}'
     for row in part:
      for n in row['cells']:del cells[n]
     cells[name]={'type':'$_QFD_RING_','width':len(part),'depth':depth,'connections':{'C':[clock],'R':[rst],'D':[r['d'] for r in part],'Q':[r['q'] for r in part]},'port_directions':{'C':'input','R':'input','D':'input','Q':'output'}}
     ring_groups.append({'W':len(part),'D':depth,'removed_flops':sum(len(r['cells']) for r in part)})
 original=len(cells);original_types=dict(Counter(c['type'] for c in cells.values()));added=defaultdict(int)
 for iteration in range(100):
  sinks=defaultdict(list);drivers={}
  for n,c in cells.items():
   for p,bs in c['connections'].items():
    for i,b in enumerate(bs):
     if not isinstance(b,int):continue
     if c['port_directions'][p]=='output':
      assert b not in drivers,(b,n,drivers.get(b));drivers[b]=(n,p,i)
     elif p!='C':sinks[b].append((4 if c['type']=='$_QFD_RING_' and p=='D' and c['depth']%3==0 else 1,'cell',n,p,i))
  for n,p in ports.items():
   if p['direction']=='output':
    for i,b in enumerate(p['bits']):
     if isinstance(b,int):sinks[b].append((16 if n=='valid_rep' else 5 if n=='valid_out' else 1,'port',n,None,i))
  overloaded=[(b,x) for b,x in sinks.items() if sum(v[0] for v in x)>32]
  if not overloaded:break
  # Reverse cell order helps process a downstream copy before its parents.
  for b,x in reversed(overloaded):
   if b not in drivers:raise ValueError(f'input bit{b} exceeds32 loads; source producer replicas required')
   n,p,i=drivers[b];c=cells[n];assert c['type']=='$_QFD_RING_' or sum(len(bs) for pn,bs in c['connections'].items() if c['port_directions'][pn]=='output')==1
   chunks=[];part=[];cost=0
   for sink in x:
    if part and cost+sink[0]>32:chunks.append(part);part=[];cost=0
    part.append(sink);cost+=sink[0]
   chunks.append(part)
   for j,chunk in enumerate(chunks[1:],1):
    cn=f'{n}__bounded_{iteration}_{j}';assert cn not in cells
    cc=copy.deepcopy(c)
    if c['type']=='$_QFD_RING_':cc['width']=1;cc['connections']['D']=[c['connections']['D'][i]];cc['connections']['Q']=[nextbit]
    else:cc['connections'][p][i]=nextbit
    cells[cn]=cc;added[c['type']]+=1
    for _,kind,sn,sp,si in chunk:
     if kind=='cell':cells[sn]['connections'][sp][si]=nextbit
     else:ports[sn]['bits'][si]=nextbit
    nextbit+=1
 else:raise ValueError('fanout replication did not converge')
 def bit(b):
  if isinstance(b,int):return f'n_{b}'
  assert b in ('0','1','x','z');return "1'b"+b
 def bus(bs):return bit(bs[0]) if len(bs)==1 else '{'+','.join(bit(b) for b in reversed(bs))+'}'
 lines=['// Generated fixed production-shape math. No extra arithmetic edges.',f'module {new}('+','.join(ports)+');']
 for n,p in ports.items():lines.append(f"{p['direction']} wire [{len(p['bits'])-1}:0] {n};")
 lines.extend('wire '+', '.join(f'n_{i}' for i in range(k,min(k+64,nextbit)))+';' for k in range(0,nextbit,64))
 for n,p in ports.items():lines.append(f'assign '+(bus(p['bits'])+' = '+n if p['direction']=='input' else n+' = '+bus(p['bits']))+';')
 used=set()
 for idx,(n,c) in enumerate(cells.items()):
  typ=c['type']
  if typ=='$_QFD_RING_':
   x=c['connections'];lines.append(f"qfd_dv_ring_delay #(.W({c['width']}),.D({c['depth']})) u_{idx}(.clk({bus(x['C'])}),.rst_n({bus(x['R'])}),.d({bus(x['D'])}),.q({bus(x['Q'])}));");continue
  if typ in GATES and '__bounded_' not in n:
   expr=GATES[typ]
   for p in ('A','B','S'):
    if p in c['connections']:expr=expr.replace(p,'('+bus(c['connections'][p])+')')
   lines.append('assign '+bus(c['connections']['Y'])+' = '+expr+';');continue
  used.add(typ);mod='qfd_bmath_'+typ.strip('$_').lower()
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
 return '\n'.join(lines)+'\n',helpers,dict(original_cells=original,original_by_type=original_types,final_by_type=dict(Counter(c['type'] for c in cells.values())),unconsumed_cells_removed=removed,dropped_outputs=list(drop),unused_inputs_removed=unused_inputs,holding_chain_count=len(delay_chains),holding_ring_groups=ring_groups,actual_final_rings=[{'W':c['width'],'D':c['depth']} for c in cells.values() if c['type']=='$_QFD_RING_'],ring_input_load_contract='D%3==0 writer4slots=>4loads/bit; otherwise one prefix D; R drives one local reset branch',retention='FF cells and added combinational cone copies retain distinct hierarchy identities; ordinary logic stays available for native technology mapping',final_cells=len(cells),added_by_type=dict(added),passes=iteration,input_sha256=hashlib.sha256(raw).hexdigest(),max_data_reset_loads=32,clock_only_excluded=True,output_boundary_assumptions={'valid_rep_each':16,'valid_out':5,'data_error_each':1},qualification='STRUCTURAL_CONSTRUCTION_ONLY; exact equivalence and mapped clocks/timing/area required')

def main():
 p=argparse.ArgumentParser();p.add_argument('json');p.add_argument('--top',required=True);p.add_argument('--name',required=True);p.add_argument('--out',required=True);p.add_argument('--helpers',required=True);p.add_argument('--record',required=True);p.add_argument('--drop-output',action='append',default=[]);p.add_argument('--collapse-delays',action='store_true');a=p.parse_args()
 s,h,r=build(Path(a.json).read_bytes(),a.top,a.name,a.drop_output,a.collapse_delays);Path(a.out).write_text(s);Path(a.helpers).write_text('\n'.join(h)+'\n');Path(a.record).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
