# Exact minimum number of service reassignments, under the frozen actual nearest-service envelope.
from pathlib import Path
import heapq,json,collections
p=Path(__file__).parent
exec(compile((p/'flow_feasibility.py').read_text().split('class Flow:')[0],'cohort_parser','exec'))
class MCF:
 def __init__(self,n):self.a=[[] for _ in range(n)]
 def edge(self,u,v,cap,cost):
  x=[v,cap,len(self.a[v]),cost,cap];y=[u,0,len(self.a[u]),-cost,0];self.a[u].append(x);self.a[v].append(y);return x
 def run(self,s,t,target):
  n=len(self.a);pot=[0]*n;flow=cost=0;INF=10**15
  while flow<target:
   ds=[INF]*n;prev=[None]*n;ds[s]=0;hp=[(0,s)]
   while hp:
    d,u=heapq.heappop(hp)
    if d!=ds[u]:continue
    for j,e in enumerate(self.a[u]):
     v,cap,_,c,_=e
     if not cap:continue
     nd=d+c+pot[u]-pot[v]
     if nd<ds[v]:ds[v]=nd;prev[v]=(u,j);heapq.heappush(hp,(nd,v))
   if ds[t]==INF:break
   for v in range(n):
    if ds[v]<INF:pot[v]+=ds[v]
   amt=target-flow;v=t
   while v!=s:
    u,j=prev[v];amt=min(amt,self.a[u][j][1]);v=u
   v=t
   while v!=s:
    u,j=prev[v];e=self.a[u][j];e[1]-=amt;self.a[v][e[2]][1]+=amt;cost+=amt*e[3];v=u
   flow+=amt
  return flow,cost
cap=1200;envelope=254.537000000001;groups=collections.defaultdict(list)
for cid,(dd,nearest) in sinks.items():
 allow=tuple(k for k in keys if dd[k]<=envelope and dd[k]-dd[nearest]<=50000)
 groups[allow,nearest].append(cid)
gs=list(groups);source=0;go=1;to=1+len(gs);target=to+len(keys);f=MCF(target+1);edges={}
for j,(allow,nearest) in enumerate(gs):
 f.edge(source,go+j,len(groups[allow,nearest]),0)
 for k in allow:edges[j,k]=f.edge(go+j,to+keys.index(k),len(sinks)+1,0 if k==nearest else 1)
for j,k in enumerate(keys):f.edge(to+j,target,cap,0)
total,minmoves=f.run(source,target,len(sinks));assert total==len(sinks)
ass={}
for j,(allow,nearest) in enumerate(gs):
 remain=set(groups[allow,nearest]);quota={k:edges[j,k][4]-edges[j,k][1] for k in allow}
 for cid in sorted(remain):
  if quota.get(nearest,0):ass[cid]=nearest;quota[nearest]-=1
 remain-=set(ass)
 for cid in sorted(remain):
  k=min((k for k in allow if quota[k]),key=lambda k:sinks[cid][0][k]);ass[cid]=k;quota[k]-=1
 assert not sum(quota.values())
counts=collections.Counter(ass.values());moves=[dict(cid=cid,instance=D.cells[cid][6],from_tap=grid[sinks[cid][1]]['name'],to_tap=grid[k]['name'],old_reach=sinks[cid][0][sinks[cid][1]],new_reach=sinks[cid][0][k]) for cid,k in sorted(ass.items()) if k!=sinks[cid][1]]
assert len(moves)==minmoves
out=dict(scope='OFFLINE service-assignment minmove witness only; no source/clock/pose/phase/edge/PG change, no CTS/timing pass',cap=1200,diagnostic_absolute_envelope_um=envelope,source_max_extra_um=50000,total_grid_sinks=total,minimum_service_changes=minmoves,cohort='all42 actualSDCclk sources period833; all8fclk cohorts excluded',loads={grid[k]['name']:counts[k] for k in keys},max_new_reach_um=max(sinks[cid][0][k] for cid,k in ass.items()),moves=moves)
(p/'minmove_feasibility.json').write_text(json.dumps(out,indent=1)+'\n')
print('exact minmoves',minmoves,'assigned',total,'maxload',max(counts.values()),'maxreach',out['max_new_reach_um'])
print('moveclasses',dict(collections.Counter((x['from_tap'],x['to_tap']) for x in moves)))
