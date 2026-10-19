import json,re,math
from pathlib import Path
P=Path('.').resolve()
q=json.loads((P/'reset_space_serdes5_probe.json').read_text());pos=q['reset_locations']
lef=(P/'reset.lef').read_text()
from functools import lru_cache
@lru_cache(None)
def rects(name):
 body=re.search(r'\n  PIN '+name+r'\n(.*?)\n  END '+name+r'\n',lef,re.S)[1]
 return [tuple(map(float,m)) for m in re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',body)]
def shifted(name,pin):
 x,y,*_=pos[name]
 return [(x+a,y+b,x+c,y+d) for a,b,c,d in rects(pin)]
def dist(src,dst):
 return min(max(a-c1,a1-c,0)+max(b-d1,b1-d,0) for a,b,c,d in shifted(src,'o') for a1,b1,c1,d1 in shifted(dst,'i'))
src={};inputs={}
s=(P.parent/'bound_v2/bind/die.v').read_text()
for m in re.finditer(r'\bdsfd_rly_1_WN\s+(\w+)\s*\((.*?)\);',s,re.S):
 n,body=m.groups();con=dict(re.findall(r'\.(\w+)\s*\(\s*([^()]+?)\s*\)',body))
 if 'o' in con:src[con['o']]=n
 if 'i' in con:inputs[n]=con['i']
rows=[];missing=[]
for n,net in inputs.items():
 parent=src.get(net)
 if n not in pos or parent not in pos:missing.append([n,parent]);continue
 d=dist(parent,n);rows.append({'src':parent,'dst':n,'minimum_rect_distance_um':round(d,6)})
over=sorted([r for r in rows if r['minimum_rect_distance_um']>405.000001],key=lambda r:-r['minimum_rect_distance_um'])
summary={'scope':'LOWER_BOUND_GEOMETRY_REPLAY_OF_OLD_RESET_NETLIST_NOT_NEW_TOPOLOGY','edges_checked':len(rows),'unmodeled_root_or_other':len(missing),'over405':len(over),'max_lower_bound_um':max(r['minimum_rect_distance_um'] for r in rows),'first20':over[:20],'remaining':'Regenerate graph from physically legalized actual-pin nodes, then regenerate coherent reset and gate calendars; no reach pass/adoption.'}
(P/'reset_edge_replay.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

# Diagnostic directed graph over physically legal candidate bodies, independent of old parents.
from collections import defaultdict,deque
B=440.0;buckets=defaultdict(list)
for n,(x,y,*_) in pos.items():buckets[int(x//B),int(y//B)].append(n)
def neighbors(n):
 x,y,*_=pos[n];bx,by=int(x//B),int(y//B)
 for dx in (-1,0,1):
  for dy in (-1,0,1):
   for m in buckets[bx+dx,by+dy]:
    if m!=n and dist(n,m)<=405.000001:yield m
root=min(pos,key=lambda n:pos[n][1]+abs(pos[n][0]-16243.45))
par={root:None};depth={root:2};todo=deque([root])
while todo:
 n=todo.popleft()
 for m in sorted(neighbors(n)):
  if m not in par:par[m]=n;depth[m]=depth[n]+1;todo.append(m)
new={'scope':'DIRECTED_RECT_DISTANCE_LOWER_BOUND_GRAPH_NOT_ROUTED_OR_CALENDAR_BOUND','root':root,'candidate_bodies':len(pos),'connected_to_root':len(par),'unreachable_candidates':len(pos)-len(par),'max_depth':max(depth.values()),'largest_selected_min_rect_edge_um':max(dist(p,n) for n,p in par.items() if p),'first_unreachable':[n for n in pos if n not in par][:20]}
(P/'reset_physical_graph.json').write_text(json.dumps(new,indent=2)+'\n');print(json.dumps(new,indent=2))

newpos=pos
hints=json.loads((P/'place_hints.json').read_text())
pos={r['inst']:[r['xy'][0]-8.64,r['xy'][1]-8.64,17.28,17.28] for r in hints['reset_place']}
oldrows=[]
for n,net in inputs.items():
 parent=src.get(net)
 if n in pos and parent in pos:oldrows.append({'src':parent,'dst':n,'minimum_rect_distance_um':round(dist(parent,n),6)})
oldover=sorted([r for r in oldrows if r['minimum_rect_distance_um']>405.000001],key=lambda r:-r['minimum_rect_distance_um'])
oldsummary={'scope':'ORIGINAL_PLANNED_RESET_BODY_PIN_LOWER_BOUND_NOT_PLACED','edges_checked':len(oldrows),'over405':len(oldover),'max_lower_bound_um':max(r['minimum_rect_distance_um'] for r in oldrows),'first20':oldover[:20]}
(P/'reset_original_edge_replay.json').write_text(json.dumps(oldsummary,indent=2)+'\n');print(json.dumps(oldsummary,indent=2))

# Actual preferred track/via anchors: source .o escapes N to M6, .i uses
# VIA45 at its outer M4 pin, .rs escapes S. M6 horizontal legs use an M7
# vertical track. These are grid-compatible path lengths, not obstacle/RC closure.
def m6_near(y):return .016+round((y-.016)/.064)*.064
def m6_up(y):return .016+math.ceil((y-.016-1e-9)/.064)*.064
def m6_down(y):return .016+math.floor((y-.016+1e-9)/.064)*.064
def escape_path(src,dst,pin):
 sx,sy,*_=pos[src];dx,dy,*_=pos[dst]
 so=(sx+9.084,sy+17.238);s6=m6_up(sy+17.28+.028)
 if pin=='i':target=(dx+.060,dy+8.700);d6=m6_near(target[1])
 else:target=(dx+8.124,dy+.042);d6=m6_down(dy-.028)
 # M7 vertical leg is selected on the actual preferred track lattice.
 qx=.016+round(((so[0]+target[0])/2-.016)/.064)*.064
 return abs(s6-so[1])+abs(so[0]-qx)+abs(qx-target[0])+abs(s6-d6)+abs(d6-target[1])
def dist(src,dst):return max(escape_path(src,dst,'i'),escape_path(src,dst,'rs'))
# Try legal R0 bridge bodies rather than relaxing center/pin reach or orientation.
import sys
sys.path.insert(1,'/srv/opentallas-scratch/claude/codex-s81-dieplace/src/tools')
sys.path.insert(1,'/srv/opentallas-scratch/claude/codex-s81-dieplace/src/tools/s81_dv')
import dv_rvcase as R
pos=newpos
class BridgePlacer(R.Placer):
 def hits(self,r,gap=.5):
  if super().hits(r,gap):return True
  pos['_trial']=[r[0],r[1],17.28,17.28]
  return dist(self.parent,'_trial')>405.000001 or dist('_trial',self.child)>405.000001
placer=BridgePlacer(32486.9,25000)
for r in q['seed']['obstructions']:placer.add(tuple(r))
for x,y,w,h in pos.values():placer.add((x,y,x+w,y+h))
bridges=[];failed=[]
def rebuild():
 buckets.clear()
 for n,(x,y,*_) in pos.items():buckets[int(x//B),int(y//B)].append(n)
 par={root:None};depth={root:2};todo=deque([root])
 while todo:
  n=todo.popleft()
  for m in sorted(neighbors(n)):
   if m not in par:par[m]=n;depth[m]=depth[n]+1;todo.append(m)
 return par,depth
for iteration in range(512):
 par,depth=rebuild()
 if len(par)==len(pos):break
 pairs=[]
 for child,(x,y,*_) in list(pos.items()):
  if child in par:continue
  bx,by=int(x//B),int(y//B)
  for dx in (-2,-1,0,1,2):
   for dy in (-2,-1,0,1,2):
    for parent in buckets[bx+dx,by+dy]:
     if parent in par:
      d=dist(parent,child)
      if d<=810:pairs.append((d,parent,child))
 success=False
 for d,parent,child in sorted(pairs):
  px,py,*_=pos[parent];cx,cy,*_=pos[child]
  placer.parent=parent;placer.child=child
  try:
   x,y,move=placer.put((px+cx)/2,(py+cy)/2,17.28,17.28,step=4,rmax=405,max_distance=405,exact_edges=True,origin_grid=(.048,.048,0,0))
  except ValueError:continue
  finally:pos.pop('_trial',None)
  name='new_bridge_'+str(len(bridges));pos[name]=[x,y,17.28,17.28]
  bridges.append({'inst':name,'origin':[x,y],'parent':parent,'child':child,'parent_escape_path_um':dist(parent,name),'child_escape_path_um':dist(name,child)})
  success=True;break
 if not success:
  failed.append({'iteration':iteration,'connected':len(par),'remaining':len(pos)-len(par),'candidate_pairs':len(pairs)});break
par,depth=rebuild()
summary={'scope':'R0_BODY_BRIDGES_BOTH_I_RS_GRID_ESCAPE_LENGTH_ONLY_NO_OBSTRUCTION_RC_OR_CALENDAR_ADOPTION','original_nodes':5184,'bridges':len(bridges),'total_nodes':len(pos),'connected':len(par),'unreachable':len(pos)-len(par),'max_depth':max(depth.values()),'max_selected_escape_path_um':max(dist(p,n) for n,p in par.items() if p),'failure':failed,'first_unreachable':[n for n in pos if n not in par][:20]}
(P/'reset_physical_access_bridges.json').write_text(json.dumps({'summary':summary,'bridges':bridges,'positions':pos,'parents':par},indent=1)+'\n');print(json.dumps(summary,indent=2))
