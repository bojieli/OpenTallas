#!/usr/bin/env python3
"""Derive bare-peer endpoints only from exact native bit identities, never port-name guesses."""
import argparse,collections,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hbm_b2'))
from b2_top import Die,parse_expr
from rebind_station_endpoints import split_ref,baseinst
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan_dir');ap.add_argument('rebind_report');ap.add_argument('native');ap.add_argument('asbuilt');ap.add_argument('out');ap.add_argument('--core-graph',action='store_true',help='emit exact native producer/consumer graph instead of station maps; pass - for report');ap.add_argument('--types',help='comma-separated plan types for core graph');ap.add_argument('--bus-bindings',help='exact per-type bus/native-bit bindings');ap.add_argument('--role-map',help='explicit per-instance logical native roles with expected_plan_master');ap.add_argument('--asbuilt-map',help='generated native instance -> local role map (paired with plan census_map)');ap.add_argument('--split-maps',help='explicit type:base-instance -> native_parent, expected_module, cut_map for external master ports only');a=ap.parse_args()
pd=Path(a.plan_dir);raw=json.load(open(pd/'die_plan.json'));original_types={}
if a.core_graph:
 selected_types=set(a.types.split(',')) if a.types else None
 original_types={p['name']:p['type'] for p in raw['partitions'] if selected_types is None or p['type'] in selected_types}
 if not original_types:raise SystemExit('core graph selection has no physical partitions')
 raw=dict(raw,partition_types={part:raw['partition_types'][tn] for part,tn in original_types.items()},partitions=[dict(p,type=p['name']) for p in raw['partitions'] if p['name'] in original_types])
report=json.load(open(a.rebind_report)) if a.rebind_report!='-' else {'unresolved':[]};cfg=json.load(open(a.asbuilt));d=Die(a.native,cfg['transport']);out=Path(a.out)
if out.exists():raise SystemExit('refusing existing output')
out.mkdir(parents=True)
split_maps=json.load(open(a.split_maps)) if a.split_maps else {}
role_maps=json.load(open(a.role_map)).get('role_map',{}) if a.role_map else {}
amap_path=Path(a.asbuilt_map) if a.asbuilt_map else Path(__file__).resolve().parents[2]/'physical/die_plan/hbm/bind/asbuilt_map.json'
amap=json.load(open(amap_path))['parts'] if amap_path.is_file() else {}
census_path=pd/'census_map.json';census=json.load(open(census_path))['parts'] if census_path.is_file() else {}
parts_by_type=collections.defaultdict(set)
for part in raw['partitions']:parts_by_type[part['type']].add(part['name'])

connection_cache={}
alias_directions={}
alias_binding_failures={}
cache={}
def lookup(config,tn,inst):
 for key in [f'{tn}:{inst}',f'{tn}:{baseinst(inst)}',f'{original_types.get(tn,tn)}:{inst}',f'{original_types.get(tn,tn)}:{baseinst(inst)}']:
  if key in config:return config[key]
 return None

def bits(expr):
 if expr not in cache:
  vals=[]
  for s,age in d.resolve(parse_expr(expr,d.widths)):
   if s[0]=='n':vals.extend((s[1],i) for i in range(s[2],s[3]+1))
   elif s[0]=='c':vals.extend([None]*len(s[1]) if isinstance(s[1],str) else [None]*s[1])
  cache[expr]=vals
 return cache[expr]

def choose(t,s,field):
 cand=split_ref(s[field],t.get('hard_cores',[]));side=0 if field=='launch' else 1
 if len(cand)>1 and isinstance(s.get('r9_segments'),list):cand=[(h,p) for h,p in cand if h['inst'].endswith('__q'+str(s['r9_segments'][side]))]
 if len(cand)!=1:raise ValueError('actual core replica is not unique from exact name/segment')
 return cand[0]

def native(t,h,tn):
 override=lookup(role_maps,tn,h['inst'])
 if override:
  if h['module']!=override['expected_plan_master']:raise ValueError(f"logical native role requires plan master {override['expected_plan_master']}, current {h['module']}")
  n=override['native_instance']
  if n not in d.insts:raise ValueError('logical native role is absent from supplied native source vehicle')
  if d.insts[n]['master']!=override['expected_plan_master']:raise ValueError('supplied native source vehicle has the wrong master for explicit logical role')
  return n
 bn=baseinst(h['inst']);role=bn[2:] if bn.startswith('u_') else bn
 # as-built notes identify a source template, not its physical quadrant. The
 # generated role map plus CURRENT census assignment selects the actual native instance.
 scoped={n for n,v in amap.items() if len(v)==2 and v[1]==role and census.get(n) in parts_by_type[tn] and n in d.insts}
 if len(scoped)==1:return next(iter(scoped))
 if len(scoped)>1:raise ValueError('current census/role native identity is ambiguous')
 contents=[c for c in t.get('contents',[]) if c.get('inst') in [h['inst'],bn]]
 names=set()
 for c in contents+[h]:
  for n in re.findall(r'\bas-built\s+([\w$]+)',c.get('note','')):
   if n in d.insts and census.get(n) in parts_by_type[tn]:names.add(n)
 if len(names)!=1:raise ValueError('no unique original-native as-built alias; split/hierarchy manifest required')
 return next(iter(names))

def connections(tn,t,h):
 key=(tn,h['inst'])
 if key in connection_cache:return connection_cache[key]
 try:
  n=native(t,h,tn)
  value=(n,{p:bits(expr) for p,expr in d.insts[n]['conns'].items()})
 except ValueError:
  spec=lookup(split_maps,tn,h['inst'])
  if not spec:raise
  if h['module']!=spec['expected_module']:raise ValueError('split-map module contract differs from actual core')
  current_map=json.load(open(spec['cut_map']))
  if current_map.get('parent_alias_source'):
   if current_map.get('verdict')!='PASS':raise ValueError('current parent alias map is not complete')
   for source,sha in current_map['sources'].items():
    if hashlib.sha256(Path(source).read_bytes()).hexdigest()!=sha:raise ValueError('current cut source changed since parent alias extraction')
  elif current_map.get('public_identity_only'):
   if hashlib.sha256(Path(current_map['source']).read_bytes()).hexdigest()!=current_map['source_sha256']:raise ValueError('current public wrapper source changed since exact map extraction')
   allowed=set(current_map['identity_public_widths'])
  else:
   receipt=json.load(open(spec['abi_receipt']));hook=receipt['subcores'][spec['subcore']]
   if hook.get('equal_ignoring_whitespace') is not True:raise ValueError('current q2/q3 public subcore hookup ABI is not verified')
   allowed=set(re.findall(r'[A-Za-z_$][\w$]*',hook['source_connections']))
  n=spec['native_parent']
  if n not in d.insts:raise ValueError('split-map parent absent in native die')
  mapping=json.load(open(spec['cut_map']))
  if mapping.get('public_identity_only') or mapping.get('parent_alias_source'):
   declared=re.search(r'\.NLINK\((\d+)\)',d.insts[n]['params'])
   if not declared or int(declared[1])!=mapping['variant']['nlink']:raise ValueError('current public wrapper NLINK differs from actual native parent')
  if mapping['module']!=h['module']:raise ValueError('cut map module differs from actual core')
  ports={}
  if mapping.get('parent_alias_source'):
   from parent_alias_binding import bind
   ports,alias_failures=bind(mapping,n,{p:bits(e) for p,e in d.insts[n]['conns'].items()})
   alias_directions[key]=mapping['directions']
   if alias_failures:alias_binding_failures[f'{tn}:{h["inst"]}']=alias_failures
  for port,labels in mapping.get('buses',{}).items():
   vv=[];complete=True
   for label in labels:
    m=re.fullmatch(r'([A-Za-z_$][\w$]*)(?:\[(\d+)\])?',label)
    if not m or m[1] not in allowed or m[1] not in d.insts[n]['conns']:complete=False;break
    vect=bits(d.insts[n]['conns'][m[1]])
    if mapping.get('public_identity_only') and len(vect)!=mapping['identity_public_widths'][m[1]]:complete=False;break
    bit=int(m[2]) if m[2] is not None else 0
    if bit>=len(vect):complete=False;break
    vv.append(vect[bit])
   if complete:ports[port]=vv
  value=(n+'::'+h['inst'],ports)
 connection_cache[key]=value
 return value

if a.core_graph:
 from native_core_graph import build
 def source_identity(tn,h,label):
  if '::' not in label:return label
  spec=lookup(split_maps,tn,h['inst']) or {}
  return spec.get('native_parent',label.split('::')[0])+'::'+spec.get('subcore',h['module'])
 def source_direction(tn,h,label,port,vector):
  if (tn,h['inst']) in alias_directions:return alias_directions[(tn,h['inst'])].get(port,'unknown')
  origin=label.split('::')[0];states=set()
  for value in vector:
   if value is None:continue
   driver=d.driver.get(value[0])
   if driver==(origin,port):states.add('output')
   elif driver is not None or d.dirs.get(value[0])=='input':states.add('input')
   else:states.add('unknown')
  return next(iter(states)) if len(states)==1 else 'unknown'
 bus=json.load(open(a.bus_bindings)) if a.bus_bindings else []
 instance_bus=[]
 for b in bus:
  context=b.get('partition') or (b['type'] if b['type'] in original_types else None)
  if context is None:
   candidates=[part for part,tn in original_types.items() if tn==b['type']]
   if len(candidates)!=1:raise ValueError('replicated-type buses require explicit per-partition native bit bindings')
   context=candidates[0]
  instance_bus.append(dict(b,type=context))
 cc,edges,gr=build(raw,pd,connections,source_identity,source_direction,None,instance_bus,entry_types=original_types)
 aggregate={}
 for part,cores in cc.items():
  tn=original_types[part];target=aggregate.setdefault(tn,{})
  for inst,ports in cores.items():
   for port,peers in ports.items():target.setdefault(inst,{}).setdefault(port,set()).update(peers)
 aggregate={tn:{inst:{port:sorted(peers) for port,peers in ports.items()} for inst,ports in cores.items()} for tn,cores in aggregate.items()}
 for edge in edges:edge['partition']=edge['type'];edge['type']=original_types[edge['type']]
 gr.update(alias_binding_failures=alias_binding_failures,native=a.native,plan=str(pd),role_map=a.role_map,split_maps=a.split_maps,instance_types=original_types,aggregation='Union of exact per-physical-partition edges only; no replica source aliases inferred.')
 (out/'core_conns_by_instance.json').write_text(json.dumps(cc,indent=1)+'\n')
 (out/'core_conns.json').write_text(json.dumps(aggregate,indent=1)+'\n')
 (out/'core_edges.json').write_text(json.dumps(edges,indent=1)+'\n')
 (out/'report.json').write_text(json.dumps(gr,indent=1)+'\n')
 print('CORE_GRAPH',gr['verdict'],'errors',len(gr['errors']),'alias_collisions',len(gr['source_alias_collisions']),'edges',gr['edges'])
 sys.exit(gr['verdict']!='PASS')

emap={};rows=[]
for entry in report['unresolved']:
 tn,i=entry['type'],entry['station'];t=raw['partition_types'][tn];s=t['internal_stations'][i]
 for err in entry['errors']:
  field=err['field'];row=dict(type=tn,station=i,field=field,reference=s.get(field),conn=s.get('conn'))
  try:
   target,tp=choose(t,s,field);other='capture' if field=='launch' else 'launch';source,sp=choose(t,s,other)
   if tp or not sp:raise ValueError('only bare-peer endpoint opposite an explicit source port is supported')
   sn,source_ports=connections(tn,t,source);tnative,target_ports=connections(tn,t,target)
   if sp not in source_ports:raise ValueError('explicit source port absent in original native alias; split/canonical map required')
   sourcevector=source_ports[sp];sourcebits=set(sourcevector)-{None}
   row.update(source_native=sn,source_port=sp,target_native=tnative,source_variable_bits=len(sourcebits),target_mapped_ports=len(target_ports),target_alias_binding_failures=alias_binding_failures.get(f'{tn}:{target["inst"]}',{}))
   if not sourcebits:raise ValueError('source contains no variable native bits')
   pf=pd/target['pins_file'];pins=json.load(open(pf));pnames={p['name'] for p in pins};selected=[];matched=set();matches=[]
   for port,resolved in target_ports.items():
    hit=[(k,b) for k,b in enumerate(resolved) if b in sourcebits]
    if not hit:continue
    physical=target.get('pin_select',{}).get(port,port)
    targets=[]
    for k,b in hit:
     logical=port if len(resolved)==1 and physical in pnames else f'{port}[{k}]'
     actual=physical if len(resolved)==1 and physical in pnames else f'{physical}[{k}]'
     if actual not in pnames:raise ValueError(f'exact target native pin {actual} is absent from current table')
     selected.append(logical);targets.append(dict(target_pin=logical,source_net=b[0],source_bit=b[1]));matched.add(b)
    matches.append(dict(target_port=port,bits=targets))
   expected=s.get('bits_parallel',s.get('bits'))
   if not matched:raise ValueError('exact supplied-source bit intersection is empty; peer graph is not a native binding')
   if len(matched)>expected:raise ValueError(f'exact native bit coverage {len(matched)} exceeds priced station width {expected}; real bundle/source contract required')
   if not selected:raise ValueError('no exact native target-port intersection')
   key=f'{tn}:{i}:{field}';source_selected=[];source_physical=source.get('pin_select',{}).get(sp,sp);sourcepins={p['name'] for p in json.load(open(pd/source['pins_file']))}
   for k,b in enumerate(sourcevector):
    if b not in matched:continue
    logical=sp if len(sourcevector)==1 and source_physical in sourcepins else f'{sp}[{k}]'
    actual=source_physical if len(sourcevector)==1 and source_physical in sourcepins else f'{source_physical}[{k}]'
    if actual not in sourcepins:raise ValueError(f'exact source native pin {actual} is absent from current table')
    source_selected.append(logical)
   emap[key]=dict(core=target['inst'],ports=selected,expected_plan_module=target['module'],expected_reference=s[field],expected_conn=s.get('conn'),expected_r9_segments=s.get('r9_segments'))
   emap[f'{tn}:{i}:{other}']=dict(core=source['inst'],ports=source_selected,expected_plan_module=source['module'],expected_reference=s[other],expected_conn=s.get('conn'),expected_r9_segments=s.get('r9_segments'))
   row.update(verdict='PASS',source_native=sn,source_port=sp,source_plan_module=source['module'],target_native=tnative,target_plan_module=target['module'],unique_native_bits=len(matched),reserved_parallel_bits=expected,unused_reserved_bits=expected-len(matched),source_pin_bits=len(source_selected),target_pin_bits=len(selected),matches=matches,map_key=key)
  except (ValueError,KeyError,TypeError,IndexError) as e:row.update(verdict='FAIL',reason=str(e))
  rows.append(row)
meta=dict(schema='opentallas.native_station_map.v1',plan=str(pd),plan_sha256=hashlib.sha256((pd/'die_plan.json').read_bytes()).hexdigest(),native=str(a.native),native_sha256=hashlib.sha256(Path(a.native).read_bytes()).hexdigest(),maps=len(emap),mapped_bare_endpoints=sum(r['verdict']=='PASS' for r in rows),failed=sum(r['verdict']=='FAIL' for r in rows),rows=rows,asbuilt_map=str(amap_path),split_maps=a.split_maps,role_map=a.role_map,method='Exact native variable-bit identity after real transport resolution; source/target identity uses generated role map + current census assignment, not template as-built annotations; Native used bits must fit existing reserved parallel width, which is never reduced; exact source and target bit subsets supplied. Clone/split binding on the current unified native top remains an independent requirement.')
meta['alias_binding_failures']=alias_binding_failures
meta['verdict']='FAIL' if meta['failed'] else 'PASS';meta['scope']='Exact endpoint map construction on the supplied source vehicle; current unified full native binding and physical gates remain required.'
(out/'endpoint_map.json').write_text(json.dumps(emap,indent=1)+'\n');(out/'report.json').write_text(json.dumps(meta,indent=1)+'\n');print('EXACT_MAPS',len(emap),'FAILED',meta['failed'],'VERDICT',meta['verdict']);print(collections.Counter(r.get('reason','PASS') for r in rows));sys.exit(1 if meta['failed'] else 0)
