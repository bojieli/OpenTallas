import json,csv,collections,pathlib,gzip,hashlib
P=pathlib.Path(__file__).parent
BASE=pathlib.Path('/srv/opentallas-scratch/claude/hbm-int8-cts-v2-run-1019')
load=lambda f:json.loads(pathlib.Path(f).read_text())
raw=load(BASE/'output/native/raw.json');mod=next(iter(raw['modules'].values()));cells=mod['cells'];nets=collections.defaultdict(list)
for n,c in cells.items():
 for pin,bs in c['connections'].items():
  for b in bs:nets[b].append(dict(cell=n,pin=pin,master=c['type'],direction=c['port_directions'][pin]))
rows={};summ={};inventory=list(csv.DictReader(open(P/'inventory_FF.tsv'),delimiter='\t'))
for f in P.glob('*.json'):
 if f.name.startswith(('FF_','TT_')):
  key=tuple(f.stem.split('_'))
  data=load(f)['checks'];rows[key]={d['endpoint']:d for d in data}
  assert len(rows[key])==len(data),(f,'DUPLICATE_ENDPOINT')
  role=key[1]; allpins={r['pin'] for r in inventory if r['role']==role}
  assert set(rows[key])<=allpins
  sl=[r['slack']*1e12 for r in data]
  summ[f.stem]=dict(timed_endpoints=len(data),negative=sum(v<0 for v in sl),below30=sum(v<30 for v in sl),minimum_ps=min(sl,default=None),untimed=sorted(allpins-set(rows[key])))
# Native JSON rounded ps differ <.01ps from direct native get_property TSV; counts use unrounded TSV.
low={};negative={}
for co in ['TT','FF']:
 for role in ['data','async']:
  for edge in ['rise','fall']:
   f=P/f'{co}_{role}_internal_min_{edge}.tsv'
   a=list(csv.DictReader(open(f),delimiter='\t'))
   for r in a:
    if float(r['slack_ps'])<30:low.setdefault(role,set()).add(r['endpoint'])
    if float(r['slack_ps'])<0:negative.setdefault(role,set()).add(r['endpoint'])
manifest=[]
for role,ps in low.items():
 for ep in sorted(ps):
  n,pin=ep.rsplit('/',1);c=cells[n];bs=c['connections'][pin];assert len(bs)==1
  net=bs[0];native=nets[net];drivers=[r for r in native if r['direction']=='output'];assert len(drivers)==1,(ep,drivers)
  paths={}
  for co in ['TT','FF']:
   for edge in ['rise','fall']:
    for delay in ['min','max']:
     r=rows[(co,role,'internal',delay,edge)].get(ep)
     if r:paths[f'{co}_{delay}_{edge}']=r
  manifest.append(dict(endpoint=ep,role=role,net=net,driver=drivers[0],all_native_net_pins=native,paths=paths))
# Match 359 source-domain changes so initial no-overlap assumptions cannot be inherited.
old=load(P/'integrated_inputs/model.json');changed={b['driver']['cell'] for b in old['boundary']}
changed|={next(z for z in c['native_pins'] if z['direction']=='output')['cell'] for c in old['typed_cones'].values()}
for r in manifest:
 r['driver_already_in_359']=r['driver']['cell'] in changed
 r['min_source_instances']=sorted({v['startpoint'].rsplit('/',1)[0] for k,v in r['paths'].items() if '_min_' in k})
 r['baseline_final_driver_has_one_D_sink']=sum(x['direction']=='input' and x['pin']=='D' for x in r['all_native_net_pins'])==1
json.dump(dict(schema='int8.all_endpoint.native_census.v1',frozen_odb=raw['source_odb_sha256'],method='every actual native endpoint and transition; endpoint_path_count=1 selects true worst per explicit polarity; group bound is actual inventory cardinality, not topN; all selected endpoints unique and native JSON agrees direct API TSV',counts={k:dict(lowmargin=len(v),negative=len(negative.get(k,set()))) for k,v in low.items()},classes=summ),open(P/'census_summary.json','w'),indent=2)
json.dump(manifest,open(P/'typed_lowmargin_manifest.json','w'),indent=2)
print('COUNTS', {k:len(v) for k,v in low.items()})
for role in low:
 a=[r for r in manifest if r['role']==role];print(role,'nets',len({r['net'] for r in a}),'drivers',len({r['driver']['cell'] for r in a}),'driver_masters',collections.Counter(r['driver']['master'] for r in a),'359overlap',sum(r['driver_already_in_359'] for r in a),'not_single_D',sum(not r['baseline_final_driver_has_one_D_sink'] for r in a));print('async nets' if role=='async' else '',[(r['net'],r['driver']['cell'],r['endpoint']) for r in a] if role=='async' else '')
