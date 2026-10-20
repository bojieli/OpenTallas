import collections,gzip,json,sys
from pathlib import Path
p=Path(sys.argv[1]);L=json.load(gzip.open(p));old=json.load(gzip.open('/srv/opentallas-scratch/claude/hbm-die10-1020/planA/artifacts/net/relays_d4g_land.json.gz'))
def inventory(l):
 return collections.Counter((b['driver'],*bit,*dst) for b in l['relay_splice_v2'] for bit,loads in zip(b['driver_bits'],b['loads']) for dst in loads)
def ages(l):
 out=collections.defaultdict(set)
 for b in l['relay_splice_v2']:
  nodes={x['id']:x for x in b['nodes']}
  for sink,sk in b['sinks'].items():
   n=0;parent=sk['src'][0]
   while parent is not None:n+=1;parent=nodes[parent]['parent']
   age=(-(-n//2)+1+len(sk['chain'])) if b['inter_region'] else n+len(sk['chain'])
   for bit,loads in zip(b['driver_bits'],b['loads']):
    for d in loads:
     if d[0]==sink:out[b['driver'],bit[0],d[0],d[1]].add(age)
 return out
io,inn=inventory(old),inventory(L);missing=io-inn;extra=inn-io
print('BIT_LOAD_INVENTORY',len(io),len(inn),'missing',sum(missing.values()),'extra',sum(extra.values()),list(missing.items())[:3],list(extra.items())[:3]);assert inn==io
ag=ages(L);bad={str(k):sorted(v) for k,v in ag.items() if len(v)!=1};print('FUNCTIONAL_PORT_AGES',len(ag),'unequal',len(bad),list(bad.items())[:4]);assert not bad
# An actual destination-bit corruption is caught independently of planner rules.
b=next(b for b in L['relay_splice_v2'] if b['loads'] and b['loads'][0]);b['loads'][0][0][2]+=1
assert inventory(L)!=io;print('DESTINATION_BIT_MUTANT_CAUGHT')
json.dump({'inventory_terms':len(io),'missing':0,'extra':0,'port_groups':len(ag),'unequal':0,'destination_bit_mutant_caught':True},open(str(p)+'.oracle.json','w'),indent=2)
