#!/usr/bin/env python3
"""Prepare canonical Yosys submod groups for the two complete Q2NF links.

Input is proc/flatten/opt_clean/splitnets/rename-wire JSON. No cell, register,
parameter or connection is rewritten. Shared named drivers remain in rest;
private anonymous combinational cones follow their sole owned consumers.
"""
import argparse,collections,json,re
from pathlib import Path

def prepare(raw,top='ot_q2nf_rest',split_rest=False,entry_capture=None,bank_only=False):
 t=raw['modules'][top];cells=t['cells'];owners={};aliases=collections.defaultdict(set);users=collections.defaultdict(set)
 def group(n):
  for j in range(2):
   needle=f'g_link[{j}].u_link.g_bank[' if bank_only else f'g_link[{j}].u_link.'
   encoded=f'u_body_g_link_{j}_u_link_g_bank_' if bank_only else f'u_body_g_link_{j}_u_link_'
   if needle in n or encoded in n:return f'g_linkstore{j}'
  return None
 def semantic(n):return not n.startswith('$') and not re.fullmatch(r'(?:u_x\.)?_\d+_(?:\[\d+\])?',n)
 for n,q in t['netnames'].items():
  if semantic(n):
   for b in q['bits']:
    if isinstance(b,int):aliases[b].add(group(n) or 'rest')
 for n,c in cells.items():
  g=group(n)
  if g:owners[n]=g
  for p,bits in c['connections'].items():
   if c['port_directions'][p]=='input':
    for b in bits:
     if isinstance(b,int):users[b].add(n)
 # Named output wires own ordinary combinational drivers. Mixed aliases are shared.
 for n,c in cells.items():
  if n in owners:continue
  a=set().union(*(aliases[b] for p,bs in c['connections'].items() if c['port_directions'][p]=='output' for b in bs if isinstance(b,int)))
  if len(a)==1 and 'rest' not in a:owners[n]=next(iter(a))
 changed=True
 while changed:
  changed=False
  for n,c in cells.items():
   if n in owners or c['type'].startswith(('$dff','$adff','$sdff','$dlatch','ot_sram')):continue
   bits=[b for p,bs in c['connections'].items() if c['port_directions'][p]=='output' for b in bs if isinstance(b,int)]
   if not bits or any('rest' in aliases[b] for b in bits):continue
   use=set().union(*(users[b] for b in bits));gs={owners.get(q,'rest') for q in use}
   if use and len(gs)==1 and 'rest' not in gs:
    owners[n]=next(iter(gs));changed=True
 if entry_capture:
  if entry_capture.get('schema')!='q2nf.entry_capture.v1' or not split_rest:
   raise ValueError('entry capture needs exact Q2NF source spec and controller split')
  expected=t['ports'][entry_capture['external_port']]['bits']
  selected=[expected[i] for i in entry_capture['source_bit_indices']]
  rows=entry_capture['first_registers']
  if len(rows)!=1 or rows[0]['Q_bits']!=612 or entry_capture['comb_cells']:
   raise ValueError('expected the one direct612-bit native right RX capture, no guessed cone')
  n=rows[0]['cell'];c=cells[n]
  if owners.get(n)!='g_linkstore1' or c['connections']['D']!=selected or c['connections']['CLK']!=[t['ports']['clk_link']['bits'][5]]:
   raise ValueError('right RX first-capture source/data/clock identity changed')
  owners.pop(n) # existing cell becomes controller-owned, no state/edge changes
 profile={}
 for n,c in cells.items():
  c.setdefault('attributes',{})['q2nf_original_cell']=n
  if n in owners:c['attributes']['submod']=owners[n]
  elif split_rest and c['type']!='$scopeinfo':c['attributes']['submod']='rest_control'
 for g in ['g_linkstore0','g_linkstore1','rest']:
  cs=[c for n,c in cells.items() if owners.get(n,'rest')==g]
  profile[g]={'word_cells':len(cs),'register_bits':sum(len(c['connections'].get('Q',[])) for c in cs if c['type'].startswith(('$dff','$adff','$sdff'))),'macros':collections.Counter(c['type'] for c in cs if c['type'].startswith('ot_sram'))}
 return raw,profile

def graph(raw,top):
 """Exact sequential graph independent of hierarchy/net numbering (no SAT bound)."""
 t=raw['modules'][top];driver=collections.defaultdict(set)
 for n,p in t['ports'].items():
  if p['direction']=='input':
   for j,b in enumerate(p['bits']):driver[b].add(('input',n,j))
 for n,c in t['cells'].items():
  if c['type']=='$scopeinfo':continue
  identity=c.get('attributes',{}).get('q2nf_original_cell',n)
  for p,bs in c['connections'].items():
   if c['port_directions'][p]=='output':
    for j,b in enumerate(bs):
     if isinstance(b,int):driver[b].add(('cell',identity,p,j))
 def bit(b):
  if isinstance(b,str):return ('constant',b)
  if not driver[b]:raise ValueError(f'undriven bit{b}')
  return tuple(sorted(driver[b]))
 out={}
 for n,c in t['cells'].items():
  if c['type']=='$scopeinfo':continue
  identity=c.get('attributes',{}).get('q2nf_original_cell',n)
  if identity in out:raise ValueError('duplicated original cell '+identity)
  out[identity]={'type':c['type'],'parameters':c['parameters'],'inputs':{p:[bit(b) for b in bs] for p,bs in c['connections'].items() if c['port_directions'][p]=='input'}}
 return {'cells':out,'outputs':{n:[bit(b) for b in p['bits']] for n,p in t['ports'].items() if p['direction']=='output'}}

def trim_ports(raw,top='ot_q2nf_rest'):
 """Remove only unused child input bits, preserving an explicit parent-index map.

 submod carries entire original buses even when a child uses one half. Keeping
 those unused clock/data pins would create a misleading physical interface.
 """
 parent=raw['modules'][top];types={c['type'] for c in parent['cells'].values() if c['type'].startswith(top+'_')};manifest={}
 for typ in sorted(types):
  child=raw['modules'][typ];used={b for c in child['cells'].values() for p,bs in c['connections'].items() if c['port_directions'][p]=='input' for b in bs}
  used.update(b for q in child['ports'].values() if q['direction']=='output' for b in q['bits'])
  cuts={}
  for n,q in list(child['ports'].items()):
   if q['direction']!='input':continue
   indices=[j for j,b in enumerate(q['bits']) if b in used]
   cuts[n]={'original_width':len(q['bits']),'kept_original_indices_lsb_first':indices}
   if len(indices)==len(q['bits']):continue
   for c in parent['cells'].values():
    if c['type']==typ:
     if indices:c['connections'][n]=[c['connections'][n][j] for j in indices]
     else:del c['connections'][n]
   if indices:
    q['bits']=[q['bits'][j] for j in indices];q['offset']=0;q['upto']=0
    if n in child['netnames']:
     child['netnames'][n]['bits']=q['bits'];child['netnames'][n]['offset']=0;child['netnames'][n]['upto']=0
   else:
    del child['ports'][n]
    child['netnames'].pop(n,None)
  manifest[typ]=cuts
 return raw,manifest

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','trim','compare']);p.add_argument('input');p.add_argument('output');p.add_argument('--top',default='ot_q2nf_rest');p.add_argument('--split-rest',action='store_true');p.add_argument('--entry-capture-json');p.add_argument('--bank-only',action='store_true');p.add_argument('--other-top');a=p.parse_args()
 r=json.loads(Path(a.input).read_text())
 if a.mode=='prepare':
  r,profile=prepare(r,a.top,a.split_rest,json.loads(Path(a.entry_capture_json).read_text()) if a.entry_capture_json else None,a.bank_only);Path(a.output).write_text(json.dumps(r));Path(a.output+'.profile.json').write_text(json.dumps(profile,indent=2)+'\n');print(json.dumps(profile))
 elif a.mode=='trim':
  r,manifest=trim_ports(r,a.top);Path(a.output).write_text(json.dumps(r));Path(a.output+'.ports.json').write_text(json.dumps(manifest,indent=2)+'\n');print('trimmed unused child input bits; exact original index masks recorded')
 else:
  other=json.loads(Path(a.output).read_text());g=graph(r,a.top);h=graph(other,a.other_top or a.top)
  if g!=h:raise SystemExit('FAIL: hierarchy changed exact cell/parameter/driver graph')
  print('PASS: exact sequential graph,',len(g['cells']),'cells; no changed register, parameter, connection or cycle')
if __name__=='__main__':main()
