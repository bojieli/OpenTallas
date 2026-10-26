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

# The plan's PLANDIR-relative references (564 hard_cores pins_file 'cores/...', census/ rows/map/bitcon, the
# die_io.json sidecar of reset_tree.die_io_entries, r8/ tables) resolve against the directory of the plan FILE, so
# the candidate plan is written as a SIBLING of its input plan (PLANDIR/die_plan.<OUT name>.json); OUT holds only the
# plan cells, impact and recipe.  A relocated plan lost die_io.json (b21 ERROR 'pll.por_n driven by pad_por_n,
# expected io_pad_por_n') and then the cores/ pin tables (b24 ResetError), PATH-KV 2026-10-25 23:4x.
def check_reset_pad(plan_file,p):
 pad=(p.get('reset',{}).get('source') or {}).get('pad')
 if pad and not p.get('die',{}).get('io'):
  sc=Path(plan_file).parent/'die_io.json'
  io=json.loads(sc.read_text()) if sc.is_file() else []
  if not any(w.get('name')==pad for w in io):
   raise SystemExit(f'declared reset pad {pad}: no die.io entry in the plan and no {sc}')

IDENTITY_RTL='rtl/physical/kv_hg_identity_cfg.sv'
MERGED_INTO='kv3_hg_v1'

def rewrite_recipe(rin,out,removed):
 """The bind recipe for the candidate: the input recipe with every type-name list entry of a removed HG master mapped
 onto kv3_hg_v1 (deduplicated), the identity decoder RTL added, and its paths rebased from the input recipe's
 directory to OUT (base / map_file relative to the recipe file, plan_cells relative to base), so the candidate binds
 repo-relative from OUT.  A removed type used as a dict KEY fails closed (needs an explicit decision)."""
 import os
 rin=Path(rin).resolve();a=json.loads(rin.read_text());src=rin.parent;out=out.resolve()
 rm=set(removed)
 def walk(v,path):
  if isinstance(v,dict):
   bad=[k for k in v if k in rm]
   if bad:raise SystemExit(f'recipe {path}: removed HG type(s) {bad} used as keys; decide explicitly')
   return {k:walk(x,f'{path}.{k}') for k,x in v.items()}
  if isinstance(v,list):
   r=[];seen=set()
   for x in v:
    y=MERGED_INTO if isinstance(x,str) and x in rm else walk(x,path)
    k=json.dumps(y,sort_keys=True)
    if isinstance(x,str) and x in rm and k in seen:continue
    seen.add(k);r.append(y)
   return r
  return v
 a=walk(a,'')
 base=(src/a['base']).resolve();a['base']=os.path.relpath(base,out)
 if a.get('map_file') and not Path(a['map_file']).is_absolute():
  a['map_file']=os.path.relpath((src/a['map_file']).resolve(),out)
 a['plan_cells']=os.path.relpath(out/'plan_cells.json',base)
 for k in ('files','prefer'):
  if IDENTITY_RTL not in a.get(k,[]):a.setdefault(k,[]).append(IDENTITY_RTL)
 a['hg_identity_note']=(f'generated by tools/qwen_layerbench/kv_hg_identity_1025/candidate_plan.py from '
  f'{os.path.relpath(rin,base)}: removed {sorted(rm)} -> {MERGED_INTO}, + {IDENTITY_RTL}. CANDIDATE ONLY.')
 return a

if __name__=='__main__':
 pin,cin,out,*rest=sys.argv[1:];out=Path(out)
 plan_out=Path(pin).resolve().parent/f'die_plan.{out.name}.json'
 if out.exists() or plan_out.exists():raise SystemExit(f'Refuse existing output {out} / {plan_out}')
 p,c,r=make(json.loads(Path(pin).read_text()),json.loads(Path(cin).read_text()))
 check_reset_pad(plan_out,p);out.mkdir(parents=True)
 import os;r['plan']=os.path.relpath(plan_out,Path.cwd())
 plan_out.write_text(json.dumps(p,indent=1)+'\n')
 docs=[('plan_cells.json',c),('impact.json',r)]
 if rest:docs.append(('recipe.json',rewrite_recipe(rest[0],out,r['removed_types'])))
 for n,d in docs: (out/n).write_text(json.dumps(d,indent=1)+'\n')
 print(json.dumps(r))
