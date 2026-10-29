"""Estimate a physical boot packet chain in actual free bays (not a route/signoff claim).
Usage PLAN OUT. Retains actual hard-core and per-bit FT keepouts; all bays hold320 FF at <=60%fill.
"""
import heapq,json,math,sys,hashlib
from pathlib import Path
import numpy as np
def binary_dilation(a,iterations=1):
 p=np.pad(a,1);b=np.zeros_like(a)
 for dy in range(3):
  for dx in range(3):b|=p[dy:dy+a.shape[0],dx:dx+a.shape[1]]
 return b
G=17.28; MAX=20 #345.6um registered hop before pin/placement residual
p=json.load(open(sys.argv[1]));out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
ports=[v for v in p['ports'] if {v['src']['part'],v['dst']['part']}=={'NW_hub','root'}]
WINDOW=[9990.,10050.];Y=sum(WINDOW)/2
assert all(min(WINDOW[1],v['window_um'][1])<=max(WINDOW[0],v['window_um'][0]) for v in ports)

def lattice(t):
 w,h=t['outline_um'];a=np.ones((math.floor(h/G)+1,math.floor(w/G)+1),dtype=bool)
 def mark(x0,y0,x1,y1):
  xa=max(0,math.floor((x0-9.072)/G));xb=min(a.shape[1],math.ceil((x1+9.072)/G)+1)
  ya=max(0,math.floor((y0-9.18)/G));yb=min(a.shape[0],math.ceil((y1+9.18)/G)+1)
  a[ya:yb,xa:xb]=False
 for c in t['hard_cores']:
  x,y=c['origin_um'];dx,dy=c.get('track_offset_um',[0,0]);cw,ch=c['outline_um'];mark(x+dx-4.32,y+dy-4.32,x+dx+cw+4.32,y+dy+ch+4.32)
 f=np.zeros_like(a)
 for ft in t['ft_slots']:
  for stage in ft.get('bit_sites_um',[]):
   xy=np.asarray(stage)
   if not len(xy):continue
   xx=np.rint(xy[:,0]/G).astype(int);yy=np.rint(xy[:,1]/G).astype(int);good=(xx>=0)&(yy>=0)&(xx<a.shape[1])&(yy<a.shape[0]);f[yy[good],xx[good]]=True
 a&=~binary_dilation(f,iterations=1)
 a[:1,:]=False;a[-1:,:]=False;a[:,:1]=False;a[:,-1:]=False
 return a

def nearest(a,xy):
 x,y=xy;ys,xs=np.where(a);i=np.argmin(abs(xs*G-x)+abs(ys*G-y));q=(int(xs[i]),int(ys[i]));assert abs(q[0]*G-x)+abs(q[1]*G-y)<405,(xy,q);return q

D=[]
for dx in range(-MAX,MAX+1):
 for dy in range(-MAX,MAX+1):
  d=abs(dx)+abs(dy)
  if 0<d<=MAX and (d==MAX or dx==0 or dy==0 or d<=2):D.append((dx,dy,d))

def path(a,s,e,t):
 wire=np.ones_like(a)
 for c in t['hard_cores']:
  x,y=c['origin_um'];w,h=c['outline_um']
  xa=max(0,math.floor((x-4.32)/G));xb=min(wire.shape[1],math.ceil((x+w+4.32)/G)+1)
  ya=max(0,math.floor((y-4.32)/G));yb=min(wire.shape[0],math.ceil((y+h+4.32)/G)+1);wire[ya:yb,xa:xb]=False
 edge_cache={}
 def edge(v,z):
  key=tuple(sorted((v,z)))
  if key in edge_cache:return edge_cache[key]
  x0,y0=v;x1,y1=z;xa,xb=sorted((x0,x1));ya,yb=sorted((y0,y1))
  ok=(wire[y0,xa:xb+1].all() and wire[ya:yb+1,x1].all()) or (wire[ya:yb+1,x0].all() and wire[y1,xa:xb+1].all())
  edge_cache[key]=ok;return ok
 s=nearest(a,s);e=nearest(a,e);q=[(0,0,s)];best={s:0};prev={};visited=0
 while q:
  _,cost,v=heapq.heappop(q)
  if cost!=best[v]:continue
  visited+=1
  if v==e:
   chain=[v]
   while chain[-1]!=s:chain.append(prev[chain[-1]])
   chain.reverse();return [[round(x*G,4),round(y*G,4)] for x,y in chain],visited
  for dx,dy,d in D:
   x,y=v[0]+dx,v[1]+dy
   if x<0 or y<0 or x>=a.shape[1] or y>=a.shape[0] or not a[y,x]:continue
   z=(x,y)
   if not edge(v,z):continue
   nc=cost+d+2 # small stage cost prefers longest legal registered legs
   if nc<best.get(z,1e99):best[z]=nc;prev[z]=v;heapq.heappush(q,(nc+abs(e[0]-x)+abs(e[1]-y),nc,z))
 raise ValueError('no legal registered-bay graph path')

hn=p['partition_types']['q_hub_nw'];rt=p['partition_types']['root'];hl=next(c for c in hn['contents'] if c['inst']=='u_hleaf_Q');pg=next(c for c in rt['hard_cores'] if c['inst']=='u_mu_fused_program')
s=[hl['origin_um'][0]+hl['outline_um'][0]/2,hl['origin_um'][1]+hl['outline_um'][1]/2]
nwend=[hn['outline_um'][0]-17.28,Y-6065.28];rstart=[17.28,Y-4337.28];end=[pg['origin_um'][0]+pg['outline_um'][0]/2,pg['origin_um'][1]-17.28]
legs=[]
for tn,t,aa,bb in [('q_hub_nw',hn,s,nwend),('root',rt,rstart,end)]:
 a=lattice(t)
 if tn=='q_hub_nw':
  # Keep the packet bay outside the existing soft host-leaf placement lot.
  x,y=hl['origin_um'];w,h=hl['outline_um'];a[max(0,math.floor((y-9.18)/G)):math.ceil((y+h+9.18)/G)+1,max(0,math.floor((x-9.072)/G)):math.ceil((x+w+9.072)/G)+1]=False
 chain,vis=path(a,aa,bb,t);legs.append(dict(type=tn,start=aa,end=bb,stations_um=chain,visited=vis,max_hop_um=max(abs(v[0]-w[0])+abs(v[1]-w[1]) for v,w in zip(chain,chain[1:])),grid_um=G))
r={'status':'ANALYTIC PHYSICAL BAY ESTIMATE; clock/CA and actual source pin placement pending','source_sha256':hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest(),'port_window_die_um':WINDOW,'packet_bits':320,'bay_outline_um':[17.28,17.28],'bit_cell_um':[1.404,.27],'bay_cell_fill':320*1.404*.27/(17.28*17.28),'legs':legs,'station_count':sum(len(l['stations_um']) for l in legs),'cycles_basis':'one per named source-hop leaf including boundary stations; CA K separate from source-hop count; consumer samples nextedge'}
(out/'host_boot_estimate.json').write_text(json.dumps(r,indent=1));print(json.dumps(r,indent=1))
