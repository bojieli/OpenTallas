# Offline exact grouped bipartite capacity feasibility, no native mutation.
import json,collections,sys,hashlib,re
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch/claude/head-spn-bandfix-1102/tools')
import geom_rules as G
p=Path(__file__).parent;D=G.Design(p/'geom.tsv')
grid={a['k']:a for a in D.pins if a['io']=='INPUT' and G.GRID_TAP_RE.match(a['name'])};keys=sorted(grid)
clockline=next(l for l in (p/'3_place.sdc').read_text().replace('\\\n','').splitlines() if l.startswith('create_clock -name clk '))
ports=re.findall(r'get_ports \{([^}]+)\}',clockline)
assert set(ports)=={a['name'] for a in grid.values()};assert '-period 833.0000' in clockline
config=(p/'config.mk').read_text();assert 'export OT_TAP_MAX_SINKS = 1200' in config
assert 'export OT_TAP_PITCH_UM = 100000' in config
for forbidden in ('OT_TAP_GROUP_RE','OT_CORE_ONLY_TAPS','OT_CORE_TAPS','OT_TAP_REASSIGN_UM'):
 assert not re.search(r'^export '+forbidden+r'\s*=',config,re.M),forbidden
sinks={};non_grid=collections.Counter()
for cid,c in D.cells.items():
 if c[0] not in 'SM':continue
 for n,ck in D.cell_in.get(cid,[]):
  if not ck:continue
  dr=D.nets[n][1];assert dr and dr[0]=='p'
  if dr[1] not in grid:non_grid[D.pin_by_k[dr[1]]['name']]+=1;continue
  x,y=G.ctr(c);dist={k:abs(t['x']-x)+abs(t['y']-y) for k,t in grid.items()}
  nearest=min(set(grid),key=lambda k:dist[k]);sinks[cid]=(dist,nearest)
class Flow:
 def __init__(self,n):self.a=[[] for _ in range(n)]
 def edge(self,u,v,c):
  x=[v,c,len(self.a[v]),c];y=[u,0,len(self.a[u]),0];self.a[u].append(x);self.a[v].append(y);return x
 def run(self,s,t):
  total=0
  while True:
   level=[-1]*len(self.a);level[s]=0;q=collections.deque([s])
   while q:
    u=q.popleft()
    for v,c,_,_ in self.a[u]:
     if c and level[v]<0:level[v]=level[u]+1;q.append(v)
   if level[t]<0:break
   idx=[0]*len(self.a)
   def dfs(u,f):
    if u==t:return f
    while idx[u]<len(self.a[u]):
     e=self.a[u][idx[u]];v,c,rev,_=e
     if c and level[v]==level[u]+1:
      d=dfs(v,min(f,c))
      if d:e[1]-=d;self.a[v][rev][1]+=d;return d
     idx[u]+=1
    return 0
   while True:
    x=dfs(s,10**9)
    if not x:break
    total+=x
  return total
 def reachable(self,s):
  seen={s};q=[s]
  for u in q:
   for v,c,_,_ in self.a[u]:
    if c and v not in seen:seen.add(v);q.append(v)
  return seen

def solve(cap,absolute_bound):
 groups=collections.defaultdict(list)
 for cid,(dd,nearest) in sinks.items():
  allow=tuple(k for k in keys if dd[k]-dd[nearest]<=50000 and (absolute_bound is None or dd[k]<=absolute_bound))
  groups[allow].append(cid)
 gs=list(groups);source=0;go=1;to=1+len(gs);target=to+len(keys);f=Flow(target+1);edges={}
 for j,allow in enumerate(gs):
  f.edge(source,go+j,len(groups[allow]))
  for k in allow:edges[j,k]=f.edge(go+j,to+keys.index(k),len(sinks)+1)
 for j,k in enumerate(keys):f.edge(to+j,target,cap)
 total=f.run(source,target)
 out=dict(cap=cap,diagnostic_absolute_envelope_um=absolute_bound,source_max_extra_um=50000,group_classes=len(gs),total_grid_sinks=len(sinks),assigned=total,feasible=total==len(sinks),same_clock_cohort='clk period833 singlecreate_clock object; original source identities/phase declarations preserved',non_grid_domains_unchanged=dict(non_grid))
 if total<len(sinks):
  reach=f.reachable(source);ix=[j for j in range(len(gs)) if go+j in reach];tk=[k for j,k in enumerate(keys) if to+j in reach];subset=[cid for j in ix for cid in groups[gs[j]]]
  out['exact_Hall_subset']=dict(demand=len(subset),taps=[grid[k]['name'] for k in tk],capacity=len(tk)*cap,deficit=len(subset)-len(tk)*cap,instances=[D.cells[cid][6] for cid in subset])
 else:
  ass={}
  for j,allow in enumerate(gs):
   remain=set(groups[allow]);quota={k:edges[j,k][3]-edges[j,k][1] for k in allow}
   for cid in sorted(remain):
    k=sinks[cid][1]
    if quota.get(k,0):ass[cid]=k;quota[k]-=1
   remain-=set(ass)
   for cid in sorted(remain):
    k=min((k for k in allow if quota[k]),key=lambda k:sinks[cid][0][k]);ass[cid]=k;quota[k]-=1
   assert not sum(quota.values())
  assert len(ass)==len(sinks)
  counts=collections.Counter(ass.values())
  out.update(loads={grid[k]['name']:counts[k] for k in keys},max_assigned_reach_um=max(sinks[cid][0][k] for cid,k in ass.items()),moves=[dict(instance=D.cells[cid][6],from_tap=grid[sinks[cid][1]]['name'],to_tap=grid[k]['name'],old_reach=sinks[cid][0][sinks[cid][1]],new_reach=sinks[cid][0][k]) for cid,k in sorted(ass.items()) if sinks[cid][1]!=k])
 print('cap',cap,'absbound',absolute_bound,'flow',total,'/',len(sinks),'feasible',out['feasible'],'cut',out.get('exact_Hall_subset',{}).get('deficit'),'moves',len(out.get('moves',[])))
 return out
out=dict(scope='OFFLINE grouped exact capacity feasibility ONLY; no newclock variant, rewire, move, CTS, P&R, clock-distance or timing PASS',source_geom_sha256=hashlib.sha256((p/'geom.tsv').read_bytes()).hexdigest(),taps=[dict(name=grid[k]['name'],x=grid[k]['x'],y=grid[k]['y']) for k in keys],cases=[solve(1200,405),solve(1200,None)])
(p/'exact_capacity_feasibility.json').write_text(json.dumps(out,indent=1)+'\n')
