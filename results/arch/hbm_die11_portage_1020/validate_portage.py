import collections,gzip,json,sys,hashlib
from pathlib import Path
base=Path('/srv/opentallas-scratch/claude/codex-hbm-die11-1020')
a=json.load(gzip.open(base/'layer.json.gz','rt')); r=json.load(open(base/'report.json'))
old=json.load(gzip.open('/srv/opentallas-scratch/claude/hbm-die10-1020/planA/artifacts/net/relays_d4g_land.json.gz','rt'))
def groups(l):
 g=collections.defaultdict(list)
 for b in l['relay_splice_v2']:
  nd={x['id']:x for x in b['nodes']}
  for sink,sk in b['sinks'].items():
   n=0;p=sk['src'][0]
   while p is not None:n+=1;p=nd[p]['parent']
   age=(-(-n//2)+1+len(sk['chain'])) if b['inter_region'] else n+len(sk['chain'])
   for bit,loads in zip(b['driver_bits'],b['loads']):
    for dst in loads:
     if dst[0]==sink:g[b['driver'],bit[0],dst[0],dst[1]].append((age,b['bus'],b['inter_region']))
 return g
g=groups(a); bad={str(k):sorted(set(v)) for k,v in g.items() if len({x[0] for x in v})>1}
print('ACTUAL_PORT_MODEL',len(g),'unequal',len(bad),list(bad.items())[:4]);assert not bad
oldbad={str(k):sorted(set(v)) for k,v in groups(old).items() if len({x[0] for x in v})>1};assert oldbad
print('ORIGINAL_UNEQUAL',len(oldbad),list(oldbad.items())[:4])
# Real causal mutation: delete one inserted sink stage from the actual layer.
mut=json.loads(json.dumps(a));picked=None
for b in mut['relay_splice_v2']:
 for sink,sk in b['sinks'].items():
  if sk['chain'] and '_pa' in sk['chain'][-1][0]:
   sk['chain'].pop();picked=(b['bus'],sink);break
 if picked:break
assert picked
mb={str(k):v for k,v in groups(mut).items() if len({x[0] for x in v})>1};assert mb
print('REMOVED_PAD_CAUGHT',picked,len(mb))
assert not r['problems'];assert r['landing']['no_E']>0
# All missing measurements remain explicitly unknown, never promoted by the model.
for x in r['landing']['rows']:
 if x['E'] is None:assert x['latency_edges'] is None
# Selected production-shape changed buses for actual RTL lockstep.
tags={x['bus'] for x in a['relay_splice_v2'] if any('_pa' in sk['chain'][-1][0] for sk in x['sinks'].values() if sk['chain'])}
sel=[b for b in a['relay_splice_v2'] if b['bus'] in tags]
# Include both branches of each changed functional producer port.
producers={b['driver'] for b in sel}
sel=[b for b in a['relay_splice_v2'] if b['driver'] in producers]
names={n for b in sel for nd in b['nodes'] for n in nd['names']};names|={n for b in sel for sk in b['sinks'].values() for st in sk['chain'] for n in st}
sub=dict(a,relay_splice_v2=sel,instances=[x for x in a['instances'] if x['name'] in names])
json.dump(sub,gzip.open(base/'changed.json.gz','wt'))
print('CHANGED_BUSES',len(sel),'INSTANCES',len(names),'E_UNKNOWN',r['landing']['no_E'],'HOPS_OVER',len(r['hops_over_reach']))
json.dump({'groups':len(g),'unequal':len(bad),'original_unequal':len(oldbad),'causal_removed_pad_caught':len(mb),'selected_buses':len(sel),'selected_instances':len(names),'E_unknown':r['landing']['no_E'],'hops_over':len(r['hops_over_reach'])},open(base/'model_verdict.json','w'),indent=2)
