"""HBM connected-wall rectilinear fast paths; fall back to the unchanged A* adapter.
Every segment is checked against the exact existing forbidden rectangles. Returned
polylines are still sampled, snapped, body/row checked and priced by physical_leg.
"""
import math
import adaptive_detour_v2

def install(D):
 slow_stats=adaptive_detour_v2.install(D);slow=D.legal_detour;stats={'fast':[],'fallback':slow_stats};components={}
 def component_boxes(site):
  sid=id(site)
  if sid in components:return components[sid]
  rs=site.forb;pending=set(range(len(rs)));out=[]
  while pending:
   k=pending.pop();ids=[k];todo=[k]
   while todo:
    u=rs[todo.pop()];hit=[i for i in pending if u[0]<=rs[i][2]and rs[i][0]<=u[2]and u[1]<=rs[i][3]and rs[i][1]<=u[3]]
    for i in hit:pending.remove(i);ids.append(i);todo.append(i)
   out.append((min(rs[i][0]for i in ids),min(rs[i][1]for i in ids),max(rs[i][2]for i in ids),max(rs[i][3]for i in ids)))
  components[sid]=out;return out
 def clean(poly):
  out=[]
  for p in map(tuple,poly):
   if out and p==out[-1]:continue
   if len(out)>=2 and ((out[-2][0]==out[-1][0]==p[0])or(out[-2][1]==out[-1][1]==p[1])):out[-1]=p
   else:out.append(p)
  return out
 def segment_clear(site,a,b):
  if a==b:return True
  x0,x1=sorted((a[0],b[0]));y0,y1=sorted((a[1],b[1]));indices=set()
  for i in range(math.floor(x0/site.b),math.floor(x1/site.b)+1):
   for j in range(math.floor(y0/site.b),math.floor(y1/site.b)+1):indices.update(site.idx.get((i,j),()))
  for k in indices:
   r=site.forb[k]
   if a[1]==b[1]:
    if r[1]<a[1]<r[3]and x0<r[2]and x1>r[0]:return False
   elif a[0]==b[0]:
    if r[0]<a[0]<r[2]and y0<r[3]and y1>r[1]:return False
   else:return False
  return True
 def route(site,a,b,step=5.4,margin=600.,turn_um=20.):
  a,b=tuple(a),tuple(b)
  if not site.legal(a)or not site.legal(b):return slow(site,a,b,step,margin,turn_um)
  polys=[[a,(b[0],a[1]),b],[a,(a[0],b[1]),b]]
  x0,x1=sorted((a[0],b[0]));y0,y1=sorted((a[1],b[1]));e=.6
  walls=[r for r in component_boxes(site)if r[0]<x1+step and r[2]>x0-step and r[1]<y1+step and r[3]>y0-step]
  for r in walls:
   xx=(r[0]-e,r[2]+e);yy=(r[1]-e,r[3]+e)
   for y in yy:polys.append([a,(a[0],y),(b[0],y),b])
   for x in xx:polys.append([a,(x,a[1]),(x,b[1]),b])
   # A neighbouring, disconnected bank wall may block the direct escape.
   # Try one corner of the connected wall before the other-axis escape.
   for x in xx:
    for y in yy:
     polys.append([a,(a[0],y),(x,y),(x,b[1]),b])
     polys.append([a,(x,a[1]),(x,y),(b[0],y),b])
  legal=[]
  for poly in polys:
   poly=clean(poly)
   if not all(site.legal(p)for p in poly):continue
   if not all(segment_clear(site,p,q)for p,q in zip(poly,poly[1:])):continue
   length=sum(D._man(p,q)for p,q in zip(poly,poly[1:]));legal.append((length+turn_um*max(len(poly)-2,0),length,poly))
  if legal:
   _,L,poly=min(legal,key=lambda t:(t[0],t[1],t[2]));stats['fast'].append({'a':a,'b':b,'wire_um':L,'corners':len(poly)-2});return poly
  return slow(site,a,b,step,margin,turn_um)
 D.legal_detour=route
 return stats
