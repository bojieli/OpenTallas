"""Obstacle-aware finite-grid path budget for the C4 uniform transport proposal; no placement or route credit."""
import json,math,heapq,argparse
from pathlib import Path

def run(gpath,place,out):
 g=json.loads(gpath.read_text());p=json.loads(place.read_text());w,h=g['outline_um'];step=8.64;nx=math.floor(w/step);ny=math.floor(h/step)
 base=[]
 for c in g['cores']:
  a,b=c['origin_um'];cw,ch=c['outline_um'];base.append((a,b,a+cw,b+ch,'core'))
 for r in g['reserved']:base.append((*r['rect_um'],'clock'))
 for f in g['ft']:
  for st in f.get('bit_sites_um',[]):
   xs=[q[0] for q in st];ys=[q[1] for q in st];# FT cells constrain register sites, not M4/M6 routing over ordinary cells.
   pass
 for m in p['macros']:base.append((*m['body_rect_um'],'newmacro'))
 logic=p['logic_region_um'];target=((logic[0]+logic[2])/2,(logic[1]+logic[3])/2);groups={}
 for bus,bit,layer,x,y,face in g['pins']:
  if bus in p['external_endpoint_relay_budget']:groups.setdefault(bus,[]).append((x,y))
 rows=[]
 for bus,pts in groups.items():
  bits=len(pts);half=bits*.048/2+2.16
  obs=[(a-half,b-half,c+half,d+half) for a,b,c,d,_ in base]
  blocked=set()
  for a,b,c,d in obs:
   for i in range(max(1,math.ceil(a/step)),min(nx-1,math.floor(c/step))+1):
    for j in range(max(1,math.ceil(b/step)),min(ny-1,math.floor(d/step))+1):blocked.add((i,j))
  def attach(pt):
   # Existing boundary point to a nearby legal corridor node; preserve its explicit stub price.
   cand=[]
   for i in range(max(1,round(pt[0]/step)-3),min(nx-1,round(pt[0]/step)+3)+1):
    for j in range(max(1,round(pt[1]/step)-3),min(ny-1,round(pt[1]/step)+3)+1):
     if (i,j) in blocked:continue
     x,y=i*step,j*step
     # Conservative two possible axis-aligned stub orientations.
     good=False
     for mid in [(x,pt[1]),(pt[0],y)]:
      okay=True
      for u,v in [(pt,mid),(mid,(x,y))]:
       x0,x1=sorted([u[0],v[0]]);y0,y1=sorted([u[1],v[1]])
       if any(x0<c and x1>a and y0<d and y1>b for a,b,c,d in obs):okay=False;break
      if okay:good=True;break
     if good:cand.append((abs(x-pt[0])+abs(y-pt[1]),(i,j)))
   return sorted(cand)[:1]
  ends=attach(target)
  if not ends:rows.append(dict(bus=bus,status='NO_TARGET_CORRIDOR',bits=bits,corridor_halfwidth_um=half));continue
  root=ends[0][1];dist={root:0};prev={};heap=[(0,root)]
  while heap:
   d,u=heapq.heappop(heap)
   if d!=dist[u]:continue
   for v in [(u[0]-1,u[1]),(u[0]+1,u[1]),(u[0],u[1]-1),(u[0],u[1]+1)]:
    if not(1<=v[0]<nx and 1<=v[1]<ny) or v in blocked:continue
    nd=d+step
    if nd<dist.get(v,float('inf')):dist[v]=nd;prev[v]=u;heapq.heappush(heap,(nd,v))
  worst=None;failed=0
  for pt in [min(pts),max(pts)]:
   a=attach(pt)
   if not a or a[0][1] not in dist:failed+=1;continue
   length=a[0][0]+dist[a[0][1]]+ends[0][0]
   if worst is None or length>worst['length_um']:
    node=a[0][1];path=[pt,(node[0]*step,node[1]*step)]
    while node!=root:node=prev[node];path.append((node[0]*step,node[1]*step))
    path.append(target);worst=dict(length_um=length,polyline_um=path)
  rows.append(dict(bus=bus,status='FAIL_PATH' if failed else 'PATH_FOUND_GEOMETRY_ONLY',failed_endpoint_extremes=failed,bits=bits,corridor_halfwidth_um=half,segments_380um=math.ceil(worst['length_um']/380) if worst else None,worst=worst))
 result=dict(schema='opentallas.qwen-kv-context-grid-path-budget.v1',state='ANALYTICAL_PATHS_ONLY_NOT_REGISTER_SITING',grid_um=step,endpoint_scope='two extremes of actual generated bus pinpoints; no actual mapped D/Q endpoints',target=target,obstacles='existing hard-core bodies, clock reservations, new SRAM bodies; per-bus channel inflation. Existing placement halos and ordinary FT cells remain register-site reservations, not metal walls.',rows=rows,claims=dict(route=False,timing=False,register_sites=False,complete_joint_channel_capacity=False),next='Any failure or >5 input/>3 output segments requires more uniform stages or a revised producer placement; do not build the4+2 hypothesis until resolved.')
 out.write_text(json.dumps(result,indent=1)+'\n');print([(r['bus'],r['status'],r.get('segments_380um'),r.get('worst',{}).get('length_um') if r.get('worst') else None) for r in rows])
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--geometry',type=Path,required=True);a.add_argument('--placement',type=Path,required=True);a.add_argument('--out',type=Path,required=True);p=a.parse_args();run(p.geometry,p.placement,p.out)
