#!/usr/bin/env python3
"""Finite MODEL ONLY: kept native gates, explicit polarity, recursive publication ownership."""
import collections,functools,gzip,hashlib,json,pathlib,re
P=pathlib.Path(__file__).resolve().parent
A=next(q for q in [P.parent/'qw_sysface_candidate_a_native_1019',P.parent/'qw-sysface-candidate-a-native-1019'] if q.exists())
def groups(t,k):
 for m in re.finditer(r'\b'+k+r'\s*\(([^)]*)\)\s*\{',t):
  d=1;i=m.end()
  while d:d+=(t[i]=='{')-(t[i]=='}');i+=1
  yield m.group(1).strip().strip('"'),t[m.end():i-1]
def attr(t,k):
 m=re.search(r'\b'+k+r'\s*:\s*([^;\n]+)',t);return m.group(1).strip().strip('"') if m else None
def lib(t):
 return {n:{'area':float(attr(b,'area')),'pins':{p:{k:attr(pb,k) for k in ['capacitance','rise_capacitance','fall_capacitance','max_capacitance','direction','function']} for p,pb in groups(b,'pin')}} for n,b in groups(t,'cell')}
cache=P/'native_lib_records.json'
if cache.exists():
 cached=json.loads(cache.read_text());TT=cached['TT'];FF=cached['FF']
else:
 expected={pathlib.Path(line.split()[1]).name:line.split()[0] for line in (A/'input/hbm_lib_SHA256SUMS').read_text().splitlines()}
 TT=lib((P/'input/libs/all.lib').read_text());FF={}
 for f in (P/'input/ff').iterdir():
  if f.name not in expected:continue
  FF.update(lib(gzip.open(f,'rt').read() if f.suffix=='.gz' else f.read_text()))
 used=json.load(gzip.open(A/'native_semantics.json.gz'))['candidate']['all_native_types']
 files=[P/'input/libs/all.lib']+[f for f in (P/'input/ff').iterdir() if f.name in expected]
 expected={pathlib.Path(line.split()[1]).name:line.split()[0] for line in (A/'input/hbm_lib_SHA256SUMS').read_text().splitlines()}
 for f in files[1:]:assert hashlib.sha256(f.read_bytes()).hexdigest()==expected[f.name]
 assert hashlib.sha256((P/'input/libs/all.lib').read_bytes()).hexdigest()=='7110a7a75b4d2802053266c170bed511640a53d1c85ba9e43939fd4cb8dfe817'
 TT={t:TT[t] for t in used};FF={t:FF[t] for t in used}
 cache.write_text(json.dumps({'provenance':'Exact pin/area records from pinned TT merged all.lib and all five matching FF native Liberty files. Finite parser extraction, no synthetic values.', 'source_hashes':{str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},'TT':TT,'FF':FF},indent=2)+'\n')
sem=json.load(gzip.open(A/'native_semantics.json.gz'))['candidate'];ls=sem['all_native_types']
m=next(v for k,v in json.loads((A/'mapped_candidate/netlist.json').read_text())['modules'].items() if k.startswith('qfd_host'))
cs=m['cells'];dr={};transparent={};ins={};outs=[]
for n,c in cs.items():
 for p,d in c['port_directions'].items():
  if d=='output':dr[c['connections'][p][0]]=(n,p)
 if not ls[c['type']]['ff']:
  p,f=next(iter(ls[c['type']]['functions'].items()));z=re.fullmatch(r'\s*(!?)\s*([A-Za-z0-9_]+)\s*',f)
  if z:transparent[n]=(z[2],bool(z[1]))
for n,p in m['ports'].items():
 for i,b in enumerate(p['bits']):
  if p['direction']=='input':ins[b]=n+f'[{i}]'
  else:outs.append((n+f'[{i}]',b))
@functools.lru_cache(None)
def canon(b):
 if b in dr and dr[b][0] in transparent:
  n,_=dr[b];p,inv=transparent[n];r,pol=canon(cs[n]['connections'][p][0]);return r,pol^inv
 return b,False
nodes={b:(n,p) for b,(n,p) in dr.items() if n not in transparent}
logic={b for b,(n,p) in nodes.items() if not ls[cs[n]['type']]['ff']}
ff={b for b in nodes if b not in logic};invtype='INVx1_ASAP7_75t_R';invpin=next(p for p,v in TT[invtype]['pins'].items() if v['direction']=='input');invout=next(p for p,v in TT[invtype]['pins'].items() if v['direction']=='output')
# Every original native nontransparent input retains its exact Boolean source and polarity.
inputs={b:{p:canon(bs[0]) for p,bs in cs[n]['connections'].items() if cs[n]['port_directions'][p]=='input'} for b,(n,op) in nodes.items()}
# All measured transparent cells are single INVx1 paths. No double inversion,
# BUF elimination or Z->X semantics is erased by polarity normalization.
assert len(transparent)==256 and all(cs[n]['type']==invtype for n in transparent)
invroots=collections.defaultdict(list)
for n,(pin,pol) in transparent.items():
 b=cs[n]['connections'][pin][0]
 assert b not in dr or dr[b][0] not in transparent
 invroots[b].append(n)
assert all(len(v)==1 for v in invroots.values())
# Derive consumer identities from actual FF-D connectivity, not opaque ABC names.
forward=collections.defaultdict(set)
for b,ports in inputs.items():
 for p,(r,pol) in ports.items():
  if b in logic:forward[r].add(b)
@functools.lru_cache(None)
def consumer_states(b):
 found=[]
 for q in ff:
  if inputs[q]['D'][0]==b:
   x=sem['state_correspondence'][nodes[q][0]];found.append(x['name']+f'[{x["bit"]:02d}]')
 for nxt in forward[b]:found.extend(consumer_states(nxt))
 return tuple(sorted(set(found)))
ownerbits={n:b for b,(n,p) in nodes.items()}
def sink_group(x):
 n=x['owner'];b=int(n.split('_')[1]) if n.startswith('pub_') else ownerbits.get(n)
 return consumer_states(b) if b in logic else ((sem['state_correspondence'][n]['name']+f'[{sem["state_correspondence"][n]["bit"]:02d}]',) if n in sem['state_correspondence'] else ())
counts={b:1 for b in nodes};history=[]
def cap(corner,t,p):
 v=corner[t]['pins'][p];vals=[v.get(k) for k in ['capacitance','rise_capacitance','fall_capacitance']];vals=[float(x) for x in vals if x is not None];assert vals,(t,p);return max(vals)
def limit(corner,t,p):
 x=corner[t]['pins'][p]['max_capacitance'];assert x is not None,(t,p);return float(x)
def demand():
 ds=collections.defaultdict(list)
 for b,(n,op) in nodes.items():
  t=cs[n]['type']
  for k in range(counts[b]):
   for p,(r,pol) in inputs[b].items():ds[r].append({'owner':f'pub_{b}_{k}' if b in logic else n,'pin':p,'master':t,'inverted':pol,'TT_fF':cap(TT,t,p),'FF_fF':cap(FF,t,p)})
 for name,b in outs:
  r,pol=canon(b);ds[r].append({'owner':'OUTPUT','pin':name,'master':None,'inverted':pol,'TT_fF':None,'FF_fF':None})
 return ds
def bounds(r,grp):
 out={}
 for label,L in [('TT',TT),('FF',FF)]:
  pos=sum(x[label+'_fF'] or 0 for x in grp if not x['inverted']);neg=sum(x[label+'_fF'] or 0 for x in grp if x['inverted']);hasneg=any(x['inverted'] for x in grp)
  direct=pos+(cap(L,invtype,invpin) if hasneg else 0)
  lim=limit(L,cs[nodes[r][0]]['type'],nodes[r][1]) if r in nodes else None
  out[label]={'known_direct_fF':direct,'known_inverted_fF':neg,'root_max_fF':lim,'INV_max_fF':limit(L,invtype,invout),'known_internal_legal':(lim is None or direct<=lim) and neg<=limit(L,invtype,invout)}
 return out
def legal(r,g):return len(g)<=32 and all(x['known_internal_legal'] for x in bounds(r,g).values())
initial_demand=demand()
for iteration in range(100):
 ds=demand();ownership={};updates={}
 for r,sinks in ds.items():
  sinks=sorted(sinks,key=lambda x:(sink_group(x),x['owner'],x['pin']))
  if r not in logic:ownership[r]=[sinks];continue
  gs=[];g=[]
  for x in sinks:
   if g and not legal(r,g+[x]):gs.append(g);g=[]
   g.append(x);assert legal(r,g),('single_sink_overcap',r,x)
  if g:gs.append(g)
  # Unused native outputs keep their original cell identity.
  ownership[r]=gs
  if len(gs)>counts[r]:updates[r]=len(gs)
 history.append({'iteration':iteration,'additional_copies':sum(v-counts[b] for b,v in updates.items()),'affected_roots':sorted(updates)})
 if not updates:break
 counts.update(updates)
else:raise RuntimeError('no fixed point')
# The only unused logic nodes retain one physical cell but no publication.
publications=[];invs=0
for r,gs in ownership.items():
 for k,g in enumerate(gs):
  hasneg=any(x['inverted'] for x in g);invs+=hasneg
  for x in g:x['actual_downstream_state_consumers']=sink_group(x)
  publications.append({'identity':f'pub_{r}_{k}','root_bit':r,'original_driver':nodes.get(r),'master':cs[nodes[r][0]]['type'] if r in nodes else None,'function':ls[cs[nodes[r][0]]['type']]['functions'] if r in nodes else None,'sink_count':len(g),'sinks':g,'bounds':bounds(r,g),'negative_publication_INV':invtype if hasneg else None,'external_unknown':any(x['master'] is None for x in g),'fanout_safe':len(g)<=32})
newmasters=collections.Counter()
for b,(n,p) in nodes.items():newmasters[cs[n]['type']]+=counts[b]
newmasters[invtype]+=invs
oldmasters=collections.Counter(c['type'] for c in cs.values())
oldarea=sum(TT[t]['area']*v for t,v in oldmasters.items());newarea=sum(TT[t]['area']*v for t,v in newmasters.items())
original_census=json.load(gzip.open(A/'mapped_candidate/census.json.gz'))
unsafe=[r for r in original_census['all_roots'] if r['load_count']>32 and r['driver']['role']=='logic']
@functools.lru_cache(None)
def support(r):
 if r in ins:return [ins[r]]
 if r not in nodes:return ['constant:'+str(r)]
 n,p=nodes[r]
 if r in ff:
  s=sem['state_correspondence'][n];return ['state:'+s['name']+f'[{s["bit"]}]']
 return sorted(set(y for z,pol in inputs[r].values() for y in support(z)))
rootrecords=[]
for r in unsafe:
 b=r['bit'];n,op=nodes[b]
 rootrecords.append({'bit':b,'original_driver':r['driver'],'actual_function':ls[cs[n]['type']]['functions'],'actual_source_support':support(b),'exact_input_ownership':inputs[b],'old_transparent_paths':r['transparent_paths'],'old_sinks':r['endpoints'],'proposed_copies':counts[b],'publication_ids':[p['identity'] for p in publications if p['root_bit']==b]})
# Reconcile every additional upstream input, including sibling publications and state roots.
upstream=[]
for r in sorted(set(inputs[b][pin][0] for b in logic if counts[b]>1 for pin in inputs[b]),key=str):
 old=initial_demand[r];new=ds[r]
 upstream.append({'root_bit':r,'driver':nodes.get(r),'source_support':support(r),'old_terminal_count':len(old),'new_terminal_count':len(new),'added_terminals':len(new)-len(old),'old_bound':bounds(r,old),'new_publications':[p['identity'] for p in publications if p['root_bit']==r], 'new_total_sink_TT_fF':sum(x['TT_fF'] or 0 for x in new),'new_total_sink_FF_fF':sum(x['FF_fF'] or 0 for x in new)})
assert sum(x['added_terminals'] for x in upstream)==80
assert sum(newmasters.values())==len(cs)+24
assert all(counts[r]==len(ownership[r]) for r in logic if r in ownership)
oldfails=[x for x in original_census['direct_tt_electrical_bounds'] if x['known_load_alone_exceeds_max']]
res={'original_known_TT_cap_failures':oldfails,'full_upstream_ledger':upstream,'added_native_gate_input_pins':80,'added_INV_input_pins':4,'scope':'MODEL ONLY; explicit kept native structural choice; no implementation, build, STA or physical closure','source':'76277b2cb32db263d527bb1e7c66ae91754f2ef1','native_packet':'a42894e3f','input_hashes':{str(f.relative_to(A)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [A/'mapped_candidate/netlist.json',A/'native_semantics.json.gz',A/'mapped_candidate/census.json.gz']},'fixed_point_history':history,'state_cells_preserved':145,'clock_reset_SETN_sinks_each':145,'canonical_feedback_preserved':True,'original_unsafe_roots':rootrecords,'all_publications':publications,'old_master_counts':oldmasters,'proposed_master_counts':newmasters,'old_cells':len(cs),'proposed_cells':sum(newmasters.values()),'old_native_area_um2':oldarea,'proposed_native_area_um2':newarea,'area_delta_um2':newarea-oldarea,'new_nontransparent_gate_copies':sum(counts[b]-1 for b in logic),'removed_transparent_cells':len(transparent),'explicit_INV_cells':invs,'all_affected_roots':sorted(b for b in logic if counts[b]>1),'unresolved_nonlogic_fanout':[p for p in publications if p['root_bit'] not in logic and not p['fanout_safe']],'unknown_output_cap_count':sum(p['external_unknown'] for p in publications),'original_transparent_paths_preserved_without_double_inversion':True,'source_graph_pg_mterms':sum(2*v for v in newmasters.values()),'physical_pg_binding':None,'timing_ps':None,'added_state':0,'added_edges':0}
(P/'model.json').write_text(json.dumps(res,indent=2)+'\n')
summary={k:v for k,v in res.items() if k not in ['all_publications','original_unsafe_roots','unresolved_nonlogic_fanout','full_upstream_ledger','original_known_TT_cap_failures']};summary['original_unsafe_root_copy_counts']={r['bit']:r['proposed_copies'] for r in rootrecords};summary['unresolved_nonlogic_fanout']=[{k:p[k] for k in ['identity','root_bit','sink_count','bounds']} for p in res['unresolved_nonlogic_fanout']]
(P/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:summary[k] for k in ['old_cells','proposed_cells','old_native_area_um2','proposed_native_area_um2','new_nontransparent_gate_copies','explicit_INV_cells','original_unsafe_root_copy_counts','all_affected_roots','unresolved_nonlogic_fanout']},indent=2))
