"""HBM-specific clock planner adapter: search around the actual blocking macro extents.
The shared A* helper's 600um box clips corridors around the HBM 1635um VM core.
No pin/clock/latency/gate change; only planner search extent, priced before build.
"""
def install(D):
 original=D.legal_detour
 stats=[]
 components={}
 def detour(site,a,b,step=5.4,margin=600.,turn_um=20.):
  route=original(site,a,b,step=step,margin=margin,turn_um=turn_um)
  if route is not None:return route
  x0,x1=sorted((a[0],b[0]));y0,y1=sorted((a[1],b[1]))
  blockers=[r for r in site.forb if r[0]<x1+step and r[2]>x0-step and r[1]<y1+step and r[3]>y0-step]
  if not blockers:return None
  # Abutting hard halves have overlapping halos: bypass the connected wall,
  # rather than the outline of one half. Cache the exact rectangle components.
  sid=id(site)
  if sid not in components:
   rects=list(site.forb);pending=set(range(len(rects)));cc=[]
   while pending:
    first=pending.pop();ids=[first];todo=[first]
    while todo:
     u=rects[todo.pop()]
     hit=[i for i in pending if u[0]<=rects[i][2] and rects[i][0]<=u[2] and u[1]<=rects[i][3] and rects[i][1]<=u[3]]
     for i in hit:pending.remove(i);ids.append(i);todo.append(i)
    cc.append((set(ids),(min(rects[i][0] for i in ids),min(rects[i][1] for i in ids),max(rects[i][2] for i in ids),max(rects[i][3] for i in ids))))
   components[sid]=(rects,cc)
  rects,cc=components[sid]
  seed={i for i,r in enumerate(rects) if r in blockers}
  blockers=[box for ids,box in cc if ids&seed]
  # A rectangle intersecting the direct box may be bypassed above/below or left/right.
  # The nearest pair of outward faces determines the minimum search expansion.
  escape=[]
  for r in blockers:
   choices=[max(0.,y0-r[1]),max(0.,r[3]-y1),max(0.,x0-r[0]),max(0.,r[2]-x1)]
   # Directions whose required extension is zero cannot bypass the box-crossing wall.
   positive=[v for v in choices if v>step]
   if positive:escape.append(min(positive)+2*step)
  needed=max([margin]+escape)
  extent=max(max(r[2]-r[0],r[3]-r[1]) for r in blockers)+2*step
  margins=sorted({round(max(needed,margin+step),3),round(max(extent,needed),3)})
  for grid in sorted({step,min(step,2.16)},reverse=True):
   for m in margins:
    route=original(site,a,b,step=grid,margin=m,turn_um=turn_um)
    if route is not None:
     stats.append(dict(a=list(a),b=list(b),old_margin_um=margin,new_margin_um=m,grid_um=grid,blockers=len(blockers)))
     return route
  stats.append(dict(a=list(a),b=list(b),old_margin_um=margin,failed=True,blockers=len(blockers)))
  return None
 D.legal_detour=detour
 return stats
