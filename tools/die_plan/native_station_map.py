#!/usr/bin/env python3
"""Derive bare-peer endpoints only from exact native bit identities, never port-name guesses."""
import argparse,collections,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hbm_b2'))
from b2_top import Die,parse_expr
from rebind_station_endpoints import split_ref,baseinst
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan_dir');ap.add_argument('rebind_report');ap.add_argument('native');ap.add_argument('asbuilt');ap.add_argument('out');ap.add_argument('--asbuilt-map',help='generated native instance -> local role map (paired with plan census_map)');ap.add_argument('--split-maps',help='explicit type:base-instance -> native_parent, expected_module, cut_map for external master ports only');a=ap.parse_args()
pd=Path(a.plan_dir);raw=json.load(open(pd/'die_plan.json'));report=json.load(open(a.rebind_report));cfg=json.load(open(a.asbuilt));d=Die(a.native,cfg['transport']);out=Path(a.out)
if out.exists():raise SystemExit('refusing existing output')
out.mkdir(parents=True)
split_maps=json.load(open(a.split_maps)) if a.split_maps else {}
amap_path=Path(a.asbuilt_map) if a.asbuilt_map else Path(__file__).resolve().parents[2]/'physical/die_plan/hbm/bind/asbuilt_map.json'
amap=json.load(open(amap_path))['parts'] if amap_path.is_file() else {}
census_path=pd/'census_map.json';census=json.load(open(census_path))['parts'] if census_path.is_file() else {}
parts_by_type=collections.defaultdict(set)
for part in raw['partitions']:parts_by_type[part['type']].add(part['name'])

connection_cache={}
cache={}
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
  spec=split_maps.get(f"{tn}:{baseinst(h['inst'])}")
  if not spec:raise
  if h['module']!=spec['expected_module']:raise ValueError('split-map module contract differs from actual core')
  receipt=json.load(open(spec['abi_receipt']));hook=receipt['subcores'][spec['subcore']]
  if hook.get('equal_ignoring_whitespace') is not True:raise ValueError('current q2/q3 public subcore hookup ABI is not verified')
  allowed=set(re.findall(r'[A-Za-z_$][\w$]*',hook['source_connections']))
  n=spec['native_parent']
  if n not in d.insts:raise ValueError('split-map parent absent in native die')
  mapping=json.load(open(spec['cut_map']))
  if mapping['module']!=h['module']:raise ValueError('cut map module differs from actual core')
  ports={}
  for port,labels in mapping['buses'].items():
   vv=[];complete=True
   for label in labels:
    m=re.fullmatch(r'([A-Za-z_$][\w$]*)(?:\[(\d+)\])?',label)
    if not m or m[1] not in allowed or m[1] not in d.insts[n]['conns']:complete=False;break
    vect=bits(d.insts[n]['conns'][m[1]]);bit=int(m[2]) if m[2] is not None else 0
    if bit>=len(vect):complete=False;break
    vv.append(vect[bit])
   if complete:ports[port]=vv
  value=(n+'::'+h['inst'],ports)
 connection_cache[key]=value
 return value

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
   if not matched or len(matched)>expected:raise ValueError(f'exact native bit coverage {len(matched)} exceeds/does not fit priced station width {expected}; bundle/canonical mapping required')
   if not selected:raise ValueError('no exact native target-port intersection')
   key=f'{tn}:{i}:{field}';source_selected=[];source_physical=source.get('pin_select',{}).get(sp,sp);sourcepins={p['name'] for p in json.load(open(pd/source['pins_file']))}
   for k,b in enumerate(sourcevector):
    if b not in matched:continue
    logical=sp if len(sourcevector)==1 and source_physical in sourcepins else f'{sp}[{k}]'
    actual=source_physical if len(sourcevector)==1 and source_physical in sourcepins else f'{source_physical}[{k}]'
    if actual not in sourcepins:raise ValueError(f'exact source native pin {actual} is absent from current table')
    source_selected.append(logical)
   emap[key]=dict(core=target['inst'],ports=selected,expected_reference=s[field],expected_conn=s.get('conn'),expected_r9_segments=s.get('r9_segments'))
   emap[f'{tn}:{i}:{other}']=dict(core=source['inst'],ports=source_selected,expected_reference=s[other],expected_conn=s.get('conn'),expected_r9_segments=s.get('r9_segments'))
   row.update(verdict='PASS',source_native=sn,source_port=sp,source_plan_module=source['module'],target_native=tnative,target_plan_module=target['module'],unique_native_bits=len(matched),reserved_parallel_bits=expected,unused_reserved_bits=expected-len(matched),source_pin_bits=len(source_selected),target_pin_bits=len(selected),matches=matches,map_key=key)
  except (ValueError,KeyError,TypeError,IndexError) as e:row.update(verdict='FAIL',reason=str(e))
  rows.append(row)
meta=dict(schema='opentallas.native_station_map.v1',plan=str(pd),plan_sha256=hashlib.sha256((pd/'die_plan.json').read_bytes()).hexdigest(),native=str(a.native),native_sha256=hashlib.sha256(Path(a.native).read_bytes()).hexdigest(),maps=len(emap),mapped_bare_endpoints=sum(r['verdict']=='PASS' for r in rows),failed=sum(r['verdict']=='FAIL' for r in rows),rows=rows,asbuilt_map=str(amap_path),split_maps=a.split_maps,method='Exact native variable-bit identity after real transport resolution; source/target identity uses generated role map + current census assignment, not template as-built annotations; Native used bits must fit existing reserved parallel width, which is never reduced; exact source and target bit subsets supplied. Clone/split binding on the current unified native top remains an independent requirement.')
(out/'endpoint_map.json').write_text(json.dumps(emap,indent=1)+'\n');(out/'report.json').write_text(json.dumps(meta,indent=1)+'\n');print('EXACT_MAPS',len(emap),'FAILED',meta['failed']);print(collections.Counter(r.get('reason','PASS') for r in rows))
