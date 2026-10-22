import json,collections
r=json.load(open('/tmp/s81_twelve_pair_result.json'));pools=[]
for kind,shift in [(0,0),(1,0),(1,7),(0,0),(1,0),(1,7)]:
 pool=[]
 for c in r[kind]['candidates']:
  if len(c['ret'])>10:continue
  edges=[v[0]+shift for v in c['ret']];mask=sum(1<<(t-1700) for t in edges)
  if len(set(edges))!=len(edges):continue
  pool.append(dict(mask=mask,edges=edges,assign=c['assign'],ret=c['ret']))
 pools.append(sorted(pool,key=lambda c:(len(c['edges']),c['edges'])))
print('pools',list(map(len,pools)),flush=True);nodes=0
# Forward check all remaining domains; stop on first exact cover of six valid calendars.
def solve(domains,occupied=0,chosen=None):
 global nodes
 nodes+=1;chosen={} if chosen is None else chosen
 if not domains:return chosen
 i=min(domains,key=lambda j:len(domains[j]))
 for c in domains[i]:
  if c['mask']&occupied:continue
  nd={j:[v for v in dom if not(v['mask']&c['mask'])] for j,dom in domains.items() if j!=i}
  if any(not v for v in nd.values()):continue
  sol=solve(nd,occupied|c['mask'],dict(chosen,**{str(i):c}))
  if sol:return sol
 return None
sol=solve({i:p for i,p in enumerate(pools)})
print('nodes',nodes,'solution',bool(sol));json.dump(dict(nodes=nodes,solution=sol,finite_pool_sizes=list(map(len,pools)),scope='Symbolic calendar candidate pool only; absence is not exhaustive12pair impossibility'),open('/tmp/s81_twelve_pack.json','w'),indent=2)
if sol:
 for i,c in sol.items():print(i,c['edges'],c['assign'])
