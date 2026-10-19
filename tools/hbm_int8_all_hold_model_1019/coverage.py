import json,pathlib,csv,collections
P=pathlib.Path(__file__).parent;B=pathlib.Path('/srv/opentallas-scratch/claude/hbm-int8-cts-v2-run-1019');mod=next(iter(json.load(open(B/'output/native/raw.json'))['modules'].values()));cells=mod['cells'];drivers=collections.defaultdict(list)
for n,c in cells.items():
 for pin,bs in c['connections'].items():
  if c['port_directions'][pin]=='output':
   for b in bs:drivers[b].append(dict(instance=n,master=c['type'],pin=pin))
inv=list(csv.DictReader(open(P/'inventory_FF.tsv'),delimiter='\t'));out=[];co_stats={}
for i in inv:
 ep=i['pin'];n,pin=ep.rsplit('/',1);net=cells[n]['connections'][pin];r=dict(endpoint=ep,role=i['role'],native_master=i['master'],native_net=net,drivers=[d for b in net for d in drivers[b]],coverage={})
 for co in ['TT','FF']:
  for delay in ['min','max']:
   for edge in ['rise','fall']:
    timed=[]
    for cls in ['internal','rootIO']:
     f=P/f'{co}_{i["role"]}_{cls}_{delay}_{edge}.tsv';a=list(csv.DictReader(open(f),delimiter='\t'));matching=[x for x in a if x['endpoint']==ep]
     if matching:timed.append(dict(source_class=cls,**matching[0]))
    key=co+'_'+delay+'_'+edge
    if timed:r['coverage'][key]=dict(status='TIMED',native_paths=timed)
    elif all(d['master'].startswith(('TIEHI','TIELO')) for d in r['drivers']) and r['drivers']:r['coverage'][key]=dict(status='CONSTANT_NATIVE_TIE_NO_LAUNCH',tie_role='HIGH' if r['drivers'][0]['master'].startswith('TIEHI') else 'LOW')
    elif pin in ['RESETN','SETN'] and edge=='fall':r['coverage'][key]=dict(status='NO_NATIVE_RECOVERY_REMOVAL_ON_FALL',reason='Liberty recovery_rising/removal_rising checks constrain release rising; falling assertion is pulse/function check, not an invented hold arc')
    else:r['coverage'][key]=dict(status='UNEXPLAINED_UNTIMED_HOLD',reason='must investigate before completeness claim')
 out.append(r)
assert len(out)==3186
stats=collections.Counter(c['status'] for r in out for c in r['coverage'].values());json.dump(dict(schema='int8.native_endpoint.coverage.v1',endpoints=len(out),D=sum(r['role']=='data' for r in out),async_endpoints=sum(r['role']=='async' for r in out),status_counts=stats,endpoints_native_inventory=out),open(P/'endpoint_coverage.json','w'),indent=2);print('COVERAGE',stats)
