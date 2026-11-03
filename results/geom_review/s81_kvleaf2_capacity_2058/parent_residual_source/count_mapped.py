from pathlib import Path
import json,collections
b=Path(__file__).parent
ps=list((b/'run/results').glob('**/1_2_yosys_native_metadata.json'))
if len(ps)!=1:raise SystemExit(f'Expected one native mapped metadata JSON, got{ps}')
d=json.loads(ps[0].read_text());mods=d['modules'];cache={};vis=set()
def truth(v):
 try:return int(str(v),2)!=0
 except ValueError:return bool(v)
def cells(name):
 if name in cache:return cache[name].copy()
 if name in vis:raise ValueError('recursive module '+name)
 vis.add(name);out=collections.Counter()
 for c in mods[name].get('cells',{}).values():
  typ=c['type'];m=mods.get(typ)
  if 'ASAP7' in typ or typ.startswith(('ot_sram_','ot_rom_','ot_s81_resid_cut_')):
   out[typ]+=1  # Library behavioral modules are physical leaf boundaries, never recurse into specify/primitive models.
  elif m is not None and not truth(m.get('attributes',{}).get('blackbox',0)):
   out.update(cells(typ))
  else:out[typ]+=1
 vis.remove(name);cache[name]=out;return out.copy()
ct=cells('s81p_ot_s81sl_kv_leaf__t2');cuts={k:v for k,v in ct.items()if k.startswith('ot_s81_resid_cut_')};mac={k:v for k,v in ct.items()if k.startswith(('ot_sram_','ot_rom_'))};std={k:v for k,v in ct.items()if 'ASAP7' in k};unknown={k:v for k,v in ct.items()if k not in cuts and k not in mac and k not in std};rec={'status':'ACTUAL PARENT RESIDUAL SIZING ONLY; 24 SOURCE BOUNDARIES ABSTRACTED; NO PHYSICAL OR EQUIVALENCE CREDIT','top':'s81p_ot_s81sl_kv_leaf__t2','mapped_metadata':str(ps[0].relative_to(b)),'std_cells':sum(std.values()),'abstract_cut_count':sum(cuts.values()),'abstract_cut_masters':cuts,'all24_exact_cuts_retained':len(cuts)==24 and all(v==1 for v in cuts.values()),'remaining_memories':mac,'all_leaf_cells':sum(ct.values()),'unmapped_or_other_leaf_types':unknown,'leaf_type_counts':dict(sorted(ct.items())),'count_basis':'recursive actual mapped inventory, 23 matched common direct children + wholeKV abstracted at exact native selected headers/profiles; no parent stage/FF added','extra_cycles':0};(b/'mapped_count.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({k:v for k,v in rec.items()if k!='leaf_type_counts'},indent=2))
