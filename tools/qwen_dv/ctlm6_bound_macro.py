#!/usr/bin/env python3
"""Emit fixed-shape structural math with recursively bounded data fanout.

Input is a Yosys synth -noabc -nofsm -noshare flattened JSON. Each retained
cell has its own parameterized hierarchy identity; overloaded FFs capture the
same D at the same edge. Added copies' input loads participate in subsequent
passes. This is source construction, never mapped timing qualification.
"""
import argparse,copy,hashlib,json,re
from collections import defaultdict,Counter
from pathlib import Path

GATES={'$_AND_':'A & B','$_OR_':'A | B','$_XOR_':'A ^ B','$_XNOR_':'~(A ^ B)',
       '$_NOT_':'~A','$_MUX_':'S ? B : A','$_NAND_':'~(A & B)','$_NOR_':'~(A | B)',
       '$_ANDNOT_':'A & ~B','$_ORNOT_':'A | ~B',
       '$_AO21_':'(A & B) | X','$_OA21_':'(A | B) & X'}
FFS={'$_DFF_P_','$_DFF_PN0_','$_DFF_PP0_','$_DFF_PN1_','$_DFF_PP1_',
     '$_SDFF_PN0_','$_SDFF_PP0_','$_SDFF_PN1_','$_SDFF_PP1_'}

def build(raw,top,new,drop=(),collapse=False,load_cap=32,transparent_inverters=False,retain_mux=False,shared_helpers=False,retain_bits=(),retain_all_comb=False,fuse_ao=False,retain_keep=False,macro_contracts=None):
 if not 1 <= load_cap <= 32:raise ValueError("load_cap must be1..32")
 design=json.loads(raw);m=copy.deepcopy(design['modules'][top]);cells=m['cells'];ports=m['ports']
 macro_contracts=macro_contracts or {}
 def macro(c):return c['type'] in macro_contracts
 def validate_macro(n,c):
  typ=c['type'];contract=macro_contracts[typ]
  if typ not in design['modules']:raise ValueError(f'{n}: macro module metadata absent: {typ}')
  mod=design['modules'][typ]
  if not int(str(mod.get('attributes',{}).get('blackbox','0')),2):
   raise ValueError(f'{n}: macro is not an actual declared blackbox: {typ}')
  if contract.get('kind') not in ('physical_macro','soft_child'):
   raise ValueError(f'{n}: kind must explicitly identify physical_macro or soft_child')
  if contract.get('kind')=='soft_child' and not re.fullmatch('[0-9a-f]{64}',contract.get('load_source_sha256','')):
   raise ValueError(f'{n}: soft child requires source-pinned terminal load weights')
  cp=contract['ports'];mp=mod['ports'];con=c['connections'];pd=c.get('port_directions',{})
  if set(cp)!=set(mp) or set(cp)!=set(con) or set(cp)!=set(pd):
   raise ValueError(f'{n}: macro ports differ from exact module/connection/direction contract')
  for pin,row in cp.items():
   dr=row['direction'];width=row['width']
   if dr not in ('input','output') or type(width) is not int or width<1:
    raise ValueError(f'{n}.{pin}: unsupported macro port contract')
   if dr!=mp[pin]['direction'] or dr!=pd[pin] or width!=len(mp[pin]['bits']) or not (
       width==len(con[pin]) or (dr=='output' and not con[pin])):
    raise ValueError(f'{n}.{pin}: macro direction/width mismatch')
   if type(row.get('clock')) is not bool:raise ValueError(f'{n}.{pin}: explicit boolean clock role required')
   if row['clock'] and dr!='input':raise ValueError(f'{n}.{pin}: macro clock must be input')
   if contract['kind']=='soft_child' and dr=='input' and not row['clock']:
    weights=contract.get('input_loads',{}).get(pin)
    if not isinstance(weights,list) or len(weights)!=width or any(type(v) is not int or v<0 or v>32 for v in weights):
     raise ValueError(f'{n}.{pin}: each soft input needs exact source-pinned0..32 terminal loads')
    if any(v>load_cap for v in weights):
     raise ValueError(f'{n}.{pin}: indivisible soft input exceeds constructor load cap; expand child interface first')
  parameter_types=contract.get('parameter_types',{})
  if not isinstance(parameter_types,dict) or any(v not in ('bits','string') for v in parameter_types.values()):
   raise ValueError(f'{n}: macro parameter type must be bits or string')
  declared=set(mod.get('parameter_default_values',{}))|set(c.get('parameters',{}))
  if set(parameter_types)-declared:raise ValueError(f'{n}: parameter type metadata names undeclared parameter')
  for pin,value in c.get('parameters',{}).items():
   kind=parameter_types.get(pin,'bits')
   if not isinstance(value,str):raise ValueError(f'{n}.{pin}: macro parameter must be an explicit Yosys string/bits value')
   if kind=='bits' and not re.fullmatch('[01xz]+',value):
    raise ValueError(f'{n}.{pin}: nonbinary/empty parameter requires explicit string type metadata')
   if kind=='string' and any(ord(ch)>127 for ch in value):
    raise ValueError(f'{n}.{pin}: non-ASCII macro string parameter unsupported; no lossy conversion')
 # --retain-keep (QW-SLICE7 10-20): every (* keep *) net of the flattened source (e.g. the Kogge-Stone prefix levels of
 # ot_hdc_ksadd_k) stays a retained operator boundary, so ABC cannot re-ripple prefix carries (bounded red2 LA7: a
 # 9-deep AND chain in the round increment without it).
 if retain_keep:
  retain_bits=set(retain_bits)|{b for v in m['netnames'].values() if 'keep' in v.get('attributes',{}) for b in v['bits'] if isinstance(b,int)}
 nextbit=max(b for c in cells.values() for bs in c['connections'].values() for b in bs if isinstance(b,int))+1
 # Retained output-copy boundaries are real logic, not black-box stand-ins.
 # Expand every such source module into its actual generic FF cells.
 while True:
  nested=[(n,c) for n,c in cells.items() if c['type'] in design['modules'] and not macro(c)]
  if not nested:break
  aliases={}
  def canonical(bit):
   seen=set()
   while bit in aliases:
    if bit in seen:raise ValueError('cyclic source output alias')
    seen.add(bit);bit=aliases[bit]
   return bit
  def output_alias(dst,src):
   dst,src=canonical(dst),canonical(src)
   if dst==src:return
   if not isinstance(dst,int):raise ValueError('conflicting source constant output terminals')
   aliases[dst]=src
  for n,c in nested:
   sub=design['modules'][c['type']];mapping={}
   assert not int(sub.get('attributes',{}).get('blackbox','0'),2),c['type']
   for p,v in sorted(sub['ports'].items(),key=lambda item:item[1]['direction']!='input'):
    if p not in c['connections']:raise ValueError(f'{n}.{p}: expanded child port missing from source connection metadata')
    con=c['connections'].get(p,[])
    if len(v['bits'])!=len(con) and not (v['direction']=='output' and not con):
     raise ValueError(f'{n}.{p}: expanded child input/partial-output width mismatch')
    for b,d in zip(v['bits'],con):
     if not isinstance(b,int):
      if v['direction']!='output':raise ValueError(f'{n}.{p}: constant input port metadata unsupported')
      output_alias(d,b)
     elif b in mapping and mapping[b]!=d:
      if v['direction']!='output':raise ValueError(f'{n}.{p}: conflicting aliased child input terminals')
      output_alias(d,mapping[b])
     else:mapping[b]=d
   for sc in sub['cells'].values():
    for bs in sc['connections'].values():
     for b in bs:
      if isinstance(b,int) and b not in mapping:mapping[b]=nextbit;nextbit+=1
   del cells[n]
   for sn,sc in sub['cells'].items():
    cc=copy.deepcopy(sc);cc['connections']={p:[mapping[b] if isinstance(b,int) else b for b in bs] for p,bs in sc['connections'].items()};cells[n+'/'+sn]=cc
  # A retained child can expose constant or duplicate output bits through
  # different outer nets. They are actual source assignments, not new ties.
  # Substitute the complete graph before pruning/replication; never leave
  # those outer nets undriven after expanding the hierarchy.
  for c in cells.values():
   c['connections']={p:[canonical(b) for b in bs] for p,bs in c['connections'].items()}
  for p in ports.values():p['bits']=[canonical(b) for b in p['bits']]
 cells={n:c for n,c in cells.items() if c['type']!='$scopeinfo'}
 # Lower only explicitly supported positive-clock asynchronous enabled FFs.
 # The mux feeds D; the asynchronous reset pin and its priority are untouched.
 normalized_enabled=[]
 for n,c in list(cells.items()):
  typ=c['type']
  if typ.startswith('$_DFFE_'):
   match=re.fullmatch(r'\$_DFFE_(P[NP][01])([PN])_',typ)
   if not match or set(c['connections'])!={'C','D','E','R','Q'} or any(len(bs)!=1 for bs in c['connections'].values()):
    raise ValueError(f'{n}: unsupported enabled FF ABI: {typ}')
   q=list(c['connections']['Q']);d=list(c['connections']['D']);e=list(c['connections']['E']);newbit=nextbit;nextbit+=1
   cells[n+'__enable_mux']={'type':'$_MUX_','connections':{'A':q if match[2]=='P' else d,'B':d if match[2]=='P' else q,'S':e,'Y':[newbit]},'port_directions':{'A':'input','B':'input','S':'input','Y':'output'}}
   normalized_enabled.append({'cell':n,'original_type':typ,'emitted_type':'$_DFF_'+match[1]+'_','enable_polarity':match[2]})
   c['type']='$_DFF_'+match[1]+'_';c['connections']['D']=[newbit];del c['connections']['E'];del c['port_directions']['E']
 for n,c in cells.items():
  if macro(c):validate_macro(n,c)
 assert all(c['type'] in GATES or c['type'] in FFS or macro(c) for c in cells.values()),sorted({c['type'] for c in cells.values() if c['type'] not in GATES and c['type'] not in FFS and not macro(c)})
 original_macros={n:copy.deepcopy(c) for n,c in cells.items() if macro(c)}
 for name in drop:
  assert name in ports and ports[name]['direction']=='output',name
  del ports[name]
 # Specialize actual output consumers before retaining any state. In data-only
 # lanes this removes the entire otherwise-unobserved valid pipeline.
 bybit={b:n for n,c in cells.items() for p,bs in c['connections'].items() if c['port_directions'][p]=='output' for b in bs if isinstance(b,int)}
 todo=[b for p in ports.values() if p['direction']=='output' for b in p['bits']];live=set(original_macros);seen=set()
 todo.extend(b for c in original_macros.values() for pin,bs in c['connections'].items() if c['port_directions'][pin]=='input' for b in bs)
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
 if not macro_contracts:
  for n in unused_inputs:del ports[n]
 pre_fusion_cells=len(cells);ao_fusions=0
 if fuse_ao:
  # One-consumer boolean pairs become one retained complex operator. This
  # permits native AO21/OA21 mapping without exposing a wide shared cone.
  while True:
   producer={};users=Counter()
   for n,c in cells.items():
    for p,bs in c['connections'].items():
     for b in bs:
      if c['port_directions'][p]=='output':producer[b]=n
      else:users[b]+=1
   for p in ports.values():
    if p['direction']=='output':users.update(p['bits'])
   fused=False
   for n,c in list(cells.items()):
    if n not in cells:continue
    c=cells[n]
    if c['type'] not in ('$_OR_','$_AND_'):continue
    inner_type='$_AND_' if c['type']=='$_OR_' else '$_OR_'
    for pin,other in (('A','B'),('B','A')):
     bit=c['connections'][pin][0];sn=producer.get(bit)
     if users[bit]!=1 or sn is None or sn not in cells or cells[sn]['type']!=inner_type:continue
     sub=cells[sn]
     cells[n]={'type':'$_AO21_' if c['type']=='$_OR_' else '$_OA21_',
      'connections':{'A':sub['connections']['A'],'B':sub['connections']['B'],'X':c['connections'][other],'Y':c['connections']['Y']},
      'port_directions':{'A':'input','B':'input','X':'input','Y':'output'}}
     del cells[sn];ao_fusions+=1;fused=True;break
   if not fused:break
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
   delay_chains.append(row);groups[(row['depth'],row['clock'],len(users[row['q']])>load_cap)].append(row)
  if delay_chains:
   if 'rst_n' not in ports:ports['rst_n']={'direction':'input','bits':[nextbit]};nextbit+=1
   rst=ports['rst_n']['bits'][0]
   for (depth,clock,high),rows in groups.items():
    size=1 if high else load_cap
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
     elif not ((not macro(c) and p=='C') or (macro(c) and macro_contracts[c['type']]['ports'][p].get('clock',False))):
      cost=(macro_contracts[c['type']]['input_loads'][p][i] if macro(c) and macro_contracts[c['type']]['kind']=='soft_child'
            else 4 if c['type']=='$_QFD_RING_' and p=='D' and c['depth']%3==0 else 2 if c['type']=='$_MUX_' and p=='S' else 1)
      if cost: sinks[b].append((cost,'cell',n,p,i))
  for n,p in ports.items():
   if p['direction']=='output':
    for i,b in enumerate(p['bits']):
     if isinstance(b,int):sinks[b].append((16 if n=='valid_rep' else 5 if n=='valid_out' else 1,'port',n,None,i))
  if transparent_inverters:
   # Native census collapses INV trees.  Match that topology before making
   # copies, rather than hiding a many-load cone behind one generic NOT pin.
   terminal_sinks={}
   for b in sinks:
    if b in drivers and cells[drivers[b][0]]['type']=='$_NOT_':continue
    work=[(b,0)];seen=set();ends=[]
    while work:
     bit,inv=work.pop()
     if (bit,inv) in seen:continue
     seen.add((bit,inv))
     for sink in sinks.get(bit,()):
      _,kind,sn,sp,si=sink
      if kind=='cell' and cells[sn]['type']=='$_NOT_' and sp=='A':
       work.append((cells[sn]['connections']['Y'][0],inv^1))
      else:ends.append((*sink,inv))
    terminal_sinks[b]=ends
  else:terminal_sinks={b:[(*sink,0) for sink in x] for b,x in sinks.items()}
  overloaded=[(b,x) for b,x in terminal_sinks.items() if sum(v[0] for v in x)>(load_cap if b in drivers else 32)]
  if not overloaded:break
  # Reverse cell order helps process a downstream copy before its parents.
  for b,x in reversed(overloaded):
   if b not in drivers:raise ValueError(f'input bit{b} exceeds32 loads; source producer replicas required')
   n,p,i=drivers[b];c=cells[n]
   if macro(c):raise ValueError(f'{n}.{p}[{i}]: actual macro output overload requires a registered landing; macro replication forbidden')
   assert c['type']=='$_QFD_RING_' or sum(len(bs) for pn,bs in c['connections'].items() if c['port_directions'][pn]=='output')==1
   chunks=[];part=[];cost=0
   for sink in x:
    if part and cost+sink[0]>load_cap:chunks.append(part);part=[];cost=0
    part.append(sink);cost+=sink[0]
   chunks.append(part)
   for j,chunk in enumerate(chunks[1:],1):
    cn=f'{n}__bounded_{iteration}_{j}';assert cn not in cells
    cc=copy.deepcopy(c)
    if c['type']=='$_QFD_RING_':cc['width']=1;cc['connections']['D']=[c['connections']['D'][i]];cc['connections']['Q']=[nextbit]
    else:cc['connections'][p][i]=nextbit
    cells[cn]=cc;added[c['type']]+=1
    positive=nextbit;nextbit+=1;negative=None
    for _,kind,sn,sp,si,inv in chunk:
     if inv and negative is None:
      negative=nextbit;nextbit+=1
      ni=cn+'__polarity'
      cells[ni]={'type':'$_NOT_','connections':{'A':[positive],'Y':[negative]},'port_directions':{'A':'input','Y':'output'}}
      added['$_NOT_']+=1
     bit=negative if inv else positive
     if kind=='cell':cells[sn]['connections'][sp][si]=bit
     else:ports[sn]['bits'][si]=bit
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
 def vid(name):return name if re.fullmatch('[a-zA-Z_][a-zA-Z0-9_$]*',name) else '\\'+name+' '
 def sv_string(value):
  escapes={'\\':'\\\\','"':'\\"','\n':'\\n','\r':'\\r','\t':'\\t'}
  return '"'+''.join(escapes.get(ch,ch if 32<=ord(ch)<127 else '\\%03o'%ord(ch)) for ch in value)+'"'
 for idx,(n,c) in enumerate(cells.items()):
  typ=c['type']
  if macro(c):
   old=original_macros[n];validate_macro(n,c)
   if c.get('parameters',{})!=old.get('parameters',{}):raise ValueError(f'{n}: macro parameters changed')
   for pin,bs in old['connections'].items():
    if old['port_directions'][pin]=='output' or macro_contracts[typ]['ports'][pin].get('clock',False):
     if c['connections'][pin]!=bs:raise ValueError(f'{n}.{pin}: macro output/clock terminal changed')
   def param_value(pin,value):
    return sv_string(value) if macro_contracts[typ].get('parameter_types',{}).get(pin)=='string' else str(len(value))+"'b"+value
   pars=','.join('.'+vid(p)+'('+param_value(p,v)+')' for p,v in c.get('parameters',{}).items())
   con=','.join('.'+vid(p)+'('+(bus(bs) if bs else '')+')' for p,bs in c['connections'].items())
   lines.append(f'{vid(typ)} '+(f'#({pars}) ' if pars else '')+f'{vid(n)}({con});')
   continue
  if typ=='$_QFD_RING_':
   x=c['connections'];lines.append(f"qfd_dv_ring_delay #(.W({c['width']}),.D({c['depth']})) u_{idx}(.clk({bus(x['C'])}),.rst_n({bus(x['R'])}),.d({bus(x['D'])}),.q({bus(x['Q'])}));");continue
  retain_driver=any(b in retain_bits for p,bs in c['connections'].items() if c['port_directions'][p]=='output' for b in bs)
  if typ in GATES and '__bounded_' not in n and not (retain_mux and typ=='$_MUX_') and not retain_driver and not retain_all_comb:
   expr=GATES[typ]
   for p in ('A','B','S','X'):
    if p in c['connections']:expr=expr.replace(p,'('+bus(c['connections'][p])+')')
   lines.append('assign '+bus(c['connections']['Y'])+' = '+expr+';');continue
  used.add(typ);mod='qfd_bmath_'+typ.strip('$_').lower()
  con=','.join('.'+p+'('+bus(bs)+')' for p,bs in c['connections'].items())
  attr='keep=1, keep_hierarchy="yes"' if shared_helpers else 'keep_hierarchy="yes"'
  lines.append(f'(* {attr} *) {mod} #(.ID({0 if shared_helpers else idx})) u_{idx}({con});')
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
 return '\n'.join(lines)+'\n',helpers,dict(generic_terminal_cost_contract='MUX select counts two actual dynamic pins through inversion; other generic gate inputs one; exact child weights remain authoritative; full mapped census still required', normalized_enabled_flops=normalized_enabled, macro_contracts=macro_contracts, retained_macro_terminals=[dict(instance=n,module=c['type'],parameters=c.get('parameters',{}),original_connections=original_macros[n]['connections'],emitted_connections=c['connections'],port_directions=c['port_directions']) for n,c in cells.items() if macro(c)], source_synth_cells_before_fusion=pre_fusion_cells,fused_ao_pairs=ao_fusions,original_cells=original,original_by_type=original_types,final_by_type=dict(Counter(c['type'] for c in cells.values())),unconsumed_cells_removed=removed,dropped_outputs=list(drop),unused_inputs_removed=unused_inputs,holding_chain_count=len(delay_chains),holding_ring_groups=ring_groups,actual_final_rings=[{'W':c['width'],'D':c['depth']} for c in cells.values() if c['type']=='$_QFD_RING_'],ring_input_load_contract='D%3==0 writer4slots=>4loads/bit; otherwise one prefix D; R drives one local reset branch',retention='FF cells and added combinational cone copies retain hierarchy; ordinary logic stays available for native technology mapping',transparent_inverters=transparent_inverters,retain_mux=retain_mux,shared_helpers=shared_helpers,final_cells=len(cells),added_by_type=dict(added),passes=iteration,input_sha256=hashlib.sha256(raw).hexdigest(),max_data_reset_loads=32,internal_load_cap=load_cap,input_load_cap=32,clock_only_excluded=True,output_boundary_assumptions={'valid_rep_each':16,'valid_out':5,'data_error_each':1},qualification='STRUCTURAL_CONSTRUCTION_ONLY; exact equivalence and mapped clocks/timing/area required')

def main():
 p=argparse.ArgumentParser();p.add_argument('json');p.add_argument('--top',required=True);p.add_argument('--name',required=True);p.add_argument('--out',required=True);p.add_argument('--helpers',required=True);p.add_argument('--record',required=True);p.add_argument('--drop-output',action='append',default=[]);p.add_argument('--collapse-delays',action='store_true');p.add_argument('--load-cap',type=int,default=32);p.add_argument('--transparent-inverters',action='store_true');p.add_argument('--retain-mux',action='store_true');p.add_argument('--shared-helpers',action='store_true');p.add_argument('--retain-bit',type=int,action='append',default=[]);p.add_argument('--retain-all-comb',action='store_true');p.add_argument('--fuse-ao',action='store_true');p.add_argument('--retain-keep',action='store_true');p.add_argument('--macro-contracts',help='JSON exact module->ports metadata; actual blackboxes retained, never replicated');a=p.parse_args()
 s,h,r=build(Path(a.json).read_bytes(),a.top,a.name,a.drop_output,a.collapse_delays,a.load_cap,a.transparent_inverters,a.retain_mux,a.shared_helpers,a.retain_bit,a.retain_all_comb,a.fuse_ao,a.retain_keep,json.loads(Path(a.macro_contracts).read_text()) if a.macro_contracts else None);r['retained_driver_bits']=a.retain_bit;r['retained_all_combinational_operators']=a.retain_all_comb;r['retained_keep_nets']=a.retain_keep;Path(a.out).write_text(s);Path(a.helpers).write_text('\n'.join(h)+'\n');Path(a.record).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
