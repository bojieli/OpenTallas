#!/usr/bin/env python3
"""Emit an isolated HG identity candidate, never overwrite an input/live cohort.
Requires subsequent strict bind, startup/fault proof and physical review.
"""
import copy,json,re,sys
from pathlib import Path
from collections import defaultdict

def make(plan,cells):
 p=copy.deepcopy(plan);c=copy.deepcopy(cells);T=p['partition_types'];parts={x['name']:x['type'] for x in p['partitions']}
 # Track exactly the old cfg chain, including its feedthrough slots.
 g=defaultdict(set)
 def link(a,b):g[a].add(b);g[b].add(a)
 for x in p['ports']:link((x['src']['part'],x['src']['bus']),(x['dst']['part'],x['dst']['bus']))
 for name,tn in parts.items():
  for s in T[tn].get('ft_slots',[]):link((name,s['name']+'_i'),(name,s['name']+'_o'))
 selected={(n,b['name'])for n,t in parts.items()for b in T[t].get('buses',[])if b['name'] in ('i_kvs_hroot_Q_o_cN','o_kvs_hroot_Q_o_cN')}
 todo=list(selected)
 while todo:
  for n in g[todo.pop()]:
   if n not in selected:selected.add(n);todo.append(n)
 changed=[]
 for x in p['ports']:
  if (x['src']['part'],x['src']['bus']) in selected:
   assert (x['dst']['part'],x['dst']['bus']) in selected
   changed.append((x['id'],x['width']));x['width']=2
 widths=defaultdict(set)
 for n,b in selected:widths[parts[n]].add(b)
 for tn,bs in widths.items():
  for b in T[tn].get('buses',[]):
   if b['name'] in bs:b['width']=2
  for s in T[tn].get('ft_slots',[]):
   if s['name']+'_i' in bs:
    s['width']=2
    if 'bit_sites_um'in s:s['bit_sites_um']=[v[:2]for v in s['bit_sites_um']]
 # Explicit plan connections from existing ID sources; no new straps or state.
 for tn,tc in c['types'].items():
  if tn.startswith('kv3_hg') and not tn.startswith('kv3_hgi'):
   if tn not in T:continue
   row={'cell':'u_id_row','port':'y','bits':[0,4]}if tn=='kv3_hg'else{'bus':'i_idhg_Q_N_y','bits':[0,4]}
   out={'cell':'u_identity_cfg','port':'cfg','bits':[0,4]}
   tc['cells']['u_identity_cfg']={'module':'kv_hg_identity_cfg','params':{},'conns':{'row_id':[row],'stack_id':[{'bus':'i_kvs_hroot_Q_o_cN','bits':[0,1]}]}}
   tc.setdefault('rewired',[]).append({'sink':{'inst':'ectl','port':'cfg','bits':[0,4]},'driver':out})
   if any(b['name']=='o_kvs_hroot_Q_o_cN' for b in T[tn]['buses']):tc.setdefault('bus_drivers',[]).append({'bus':'o_kvs_hroot_Q_o_cN','drivers':[{'bus':'i_kvs_hroot_Q_o_cN','bits':[0,1]}]})
  if tn.startswith('kv3_hroot') and tn in T:
   assert 'u_id_stk'in tc['cells'],tn
   tc.setdefault('bus_drivers',[]).append({'bus':'o_kvs_hroot_Q_o_cN','drivers':[{'cell':'u_id_stk','port':'y','bits':[0,1]}]})
 removed=[]
 for k in range(2,7):
  old=f'kv3_hg_v1p{k}'
  assert old in T
  for x in p['partitions']:
   if x['type']==old:x['type']='kv3_hg_v1'
  del T[old];del c['types'][old];removed.append(old)
 c['types']['kv3_hg_v1']['replicas']=[x['name']for x in p['partitions']if x['type']=='kv3_hg_v1']
 return p,c,dict(candidate_only=True,removed_types=removed,types_after=len(T),ports=len(changed),old_port_bits=sum(w for _,w in changed),new_port_bits=2*len(changed),added_registers=0,added_cycles=0,obligations=['strict bind/R8','startup identity arrival vs config readiness','bootcfg/fault contract','render and G0C before route'])

# PLANDIR sidecars the die tools resolve next to the plan file (reset_tree.die_io_entries, die_ci): a relocated
# candidate must carry them byte-identical, else the declared reset pad falls back to its bare name (b21 ERROR
# 'pll.por_n driven by pad_por_n, expected io_pad_por_n', PATH-KV 2026-10-25 23:32).
SIDECARS=('die_io.json',)

def copy_sidecars(pin,out,p):
 src=Path(pin).resolve().parent;copied=[]
 for n in SIDECARS:
  if (src/n).is_file():(out/n).write_bytes((src/n).read_bytes());copied.append(n)
 pad=(p.get('reset',{}).get('source') or {}).get('pad')
 if pad and not p.get('die',{}).get('io'):
  io=json.loads((out/'die_io.json').read_text()) if (out/'die_io.json').is_file() else []
  if not any(w.get('name')==pad for w in io):
   raise SystemExit(f'declared reset pad {pad}: no die.io entry in the plan and no die_io.json sidecar next to {pin}')
 return copied

if __name__=='__main__':
 pin,cin,out=sys.argv[1:];out=Path(out)
 if out.exists():raise SystemExit('Refuse existing output directory')
 p,c,r=make(json.loads(Path(pin).read_text()),json.loads(Path(cin).read_text()));out.mkdir(parents=True)
 r['sidecars']=copy_sidecars(pin,out,p)
 for n,d in [('plan.json',p),('plan_cells.json',c),('impact.json',r)]: (out/n).write_text(json.dumps(d,indent=1)+'\n')
 print(json.dumps(r))
