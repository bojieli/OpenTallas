#!/usr/bin/env python3
"""Export actual hierarchical cell ownership from lossless post-map JSON."""
from pathlib import Path
import json,collections,sys,gzip,hashlib,re
p=Path(sys.argv[1]);d=json.load(open(p));mods=d['modules'];top='ot_hbm_idx_score_quarter_col8_control';counts=collections.Counter();ffclocks=collections.Counter();areascope=collections.Counter();rows=[];hard=[]
def group(path):
 if re.fullmatch(r'_\d+_',path):return 'anonymous_mapped_logic'
 m=re.match(r'(ge\[[01]\]\.gc\[[0-3]\]\.leaf)(?:[./]|$)',path)
 if m:return m[1]
 m=re.match(r'(ge\[[01]\]\.(?:md|u_t|keep_pipe))(?:[./]|$)',path)
 if m:return m[1]
 m=re.match(r'(ge\[[01]\])(?:[./]|$)',path)
 return m[1]+'.engine_glue' if m else 'quarter_root'
def walk(mod,prefix,bindings):
 m=mods[mod];drivers={}
 for n,c in m['cells'].items():
  if c['type'].startswith(('INV','BUF')):
   for b in c['connections'].get('Y',[]):drivers[b]=c
 def ck(b,seen=None):
  if b in bindings:return bindings[b]
  c=drivers.get(b)
  if c:
   a=c['connections'].get('A',[])
   if len(a)==1:
    x=ck(a[0]);return 'inverted('+x+')' if c['type'].startswith('INV') else x
  return prefix+'local_net_'+str(b)
 owner={n:group(prefix+n) for n,c in m['cells'].items() if 'DFF' in c['type'] or c['type'] in mods or c['type']=='ot_hidx_meta_sram146'}
 bybit=collections.defaultdict(set);drv=collections.defaultdict(set)
 def outputs(c):
  if c['type'] in mods:return {pn for pn,pv in mods[c['type']]['ports'].items() if pv['direction']=='output'}
  if c['type']=='ot_hidx_meta_sram146':return {'q'}
  return {'Y','QN','Q','H','L'}
 for nn,cc in m['cells'].items():
  for pn,bs in cc['connections'].items():
   for b in bs:(drv if pn in outputs(cc) else bybit)[b].add(nn)
 boundary_in=collections.defaultdict(set);boundary_out=collections.defaultdict(set)
 for pn,pv in m['ports'].items():
  for i,b in enumerate(pv['bits']):
   gg=group(prefix.removesuffix('/')) if prefix else 'quarter_root'
   if not prefix and pn.startswith('cut_'):
    width={'cut_rst_n':1,'cut_qv':1,'cut_q':568,'cut_key':544,'cut_hid':64,'cut_cs':32,'cut_cf':1,'cut_prdy':4}[pn];ci=i//width;gg=f'ge[{ci//16}].gc[{(ci//4)%4}].leaf'
   (boundary_out if pv['direction']=='output' else boundary_in)[b].add(gg)
 cache={};active=set()
 def endpoint_groups(n,up=False):
  if n in owner:return {owner[n]}
  key=(n,up)
  if key in cache:return cache[key]
  assert key not in active, ('combinational cycle',prefix,n,up)
  active.add(key);ss=set();cc=m['cells'][n]
  for pn,bs in cc['connections'].items():
   if (pn in outputs(cc)) != up:
    for b in bs:
     ss.update((boundary_in if up else boundary_out).get(b,()))
     for nxt in (drv if up else bybit).get(b,()):
      if nxt!=n:ss.update(endpoint_groups(nxt,up))
  active.remove(key);cache[key]=ss;return ss
 for n,c in m['cells'].items():
  path=prefix+n;t=c['type']
  if t in mods and mods[t].get('cells'):
   binds={b:ck(c['connections'][pn][i]) for pn,pv in mods[t]['ports'].items() for i,b in enumerate(pv['bits']) if pn in c['connections']}
   walk(t,path+'/',binds);continue
  row={'instance':path,'master':t,'source_group':group(path)}
  counts[t]+=1
  if row['source_group']=='anonymous_mapped_logic':
   ds=sorted(endpoint_groups(n));us=sorted(endpoint_groups(n,True)) if not ds else [];owners=ds or us
   row['actual_downstream_source_groups']=ds;row['actual_upstream_groups_when_no_sinks']=us
   row['source_group']=owners[0] if len(owners)==1 else ('shared_mapped_logic' if owners else 'unassigned_mapped_logic')
  areascope[row['source_group']]+=1
  if 'DFF' in t:
   row['clock']=ck(c['connections']['CLK'][0]);ffclocks[row['clock']]+=1
  if t=='ot_hidx_meta_sram146':
   row['hard_view']='physical/ref_tile/hidx_meta146_main_1021/views/ot_hidx_meta_sram146';row['record']='06d0f5e44';row['D']=146;row['clock_terminals']={pn:ck(c['connections'][pn][0]) for pn in ('clk','clk_mem')};hard.append(row.copy())
  rows.append(row)
bindings={b:(pn if len(pv['bits'])==1 else f'{pn}[{i}]') for pn,pv in mods[top]['ports'].items() for i,b in enumerate(pv['bits'])}
walk(top,'',bindings)
assert len(hard)==2,hard
for h in hard:assert h['clock_terminals']['clk']==h['clock_terminals']['clk_mem']
r={'schema':'col8.residual_mapped_cells.v1','functional_source':'f9d6fc51f','physical_specialization':'f9d6fc51f','specialization_method':'a08546f1e','physical_mapping_source':'f9d6fc51f','top':top,'cell_counts':dict(counts),'source_group_cells':dict(areascope),'ff_clock_counts':dict(ffclocks),'hard_metadata_instances':hard,'cells':rows,'notes':['Actual source group associations only, no residual detailed placement or footprint qualification.','Source groups retain exact mapped hierarchy. Cell connections remain in lossless Verilog and JSON.','Two metadata hard cells per controller, eight across four quarters, preserve literal clk/clk_mem.','Controller active clocks and the 128 separate pair clocks together retain 143 external clocks per quarter. Inverted clock roots preserve negative source edges and are not additional external clocks.']}
q=p.parent/'residual_cell_association.json.gz'
with gzip.GzipFile(filename=str(q),mode='wb',mtime=0) as z:z.write((json.dumps(r,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in r.items() if k!='cells'},indent=2))
