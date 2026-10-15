#!/usr/bin/env python3
"""Bounded one-core bottom-left packing of actual HC chain-column strips; geometry OPEN."""
import json,random,sys,math
from pathlib import Path
import candidates as C

def pack(order,dims,W):
 rs={}
 for n in order:
  w,h=dims[n];best=None
  xs={0.}|{r[0]+r[2]+21.6 for r in rs.values()}
  for x in xs:
   if x+w>W+1e-6:continue
   y=0.
   for r in sorted(rs.values(),key=lambda r:r[1]):
    if x<r[0]+r[2]+21.6 and x+w+21.6>r[0] and y<r[1]+r[3]+21.6 and y+h+21.6>r[1]:y=r[1]+r[3]+21.6
   key=(y+h,y,x)
   if best is None or key<best[0]:best=(key,[x,y,w,h])
  if best is None:return 1e20,{}
  rs[n]=best[1]
 return max(r[1]+r[3] for r in rs.values()),rs

def main():
 g=json.loads(Path('results/arch/s81_globalfp_1015/graph.json').read_text());base=C.base_rects(g)
 dims={n:base[n][2:] for n in C.MOVABLE if n not in ('sp_hc_s','sp_hc_t')};dims['sp_vm']=[1965.6,9828.];dims['mix4']=[1613.5,1542.2];dims['sp_pq'][0]=1728.
 for parent,growth in [('sp_hc_s',194.4),('sp_hc_t',233.28)]:
  for col in range(3):dims[parent+'_chain'+str(col)]=[base[parent][2]/3,base[parent][3]+growth]
 rng=random.Random(811015);out=[]
 for rw in [432.,648.,864.]:
  W=5097.6-rw;best=(1e20,None);order=list(dims)
  for restart in range(5):
   rng.shuffle(order);cur,_=pack(order,dims,W)
   for i in range(1200):
    nxt=order[:];a,b=rng.sample(range(len(order)),2);nxt[a],nxt[b]=nxt[b],nxt[a];hh,rs=pack(nxt,dims,W)
    if hh<best[0]:best=(hh,rs)
    temp=1000*(.005**(i/1200))
    if hh<cur or rng.random()<math.exp(min(0,(cur-hh)/temp)):order,cur=nxt,hh
  H,rs=best
  print(rw,H,'available20312.1',flush=True)
  translated={n:[r[0]+13942.8,r[1]+1807.9,r[2],r[3]] for n,r in rs.items()}
  out.append(dict(road_width=rw,packed_height=H,available_height=20312.1,fit=H<=20312.1,rectangles=translated,road=[19040.4-rw,1807.9,rw,21824.1],corridor=[13942.8,1807.9+H+21.6,5097.6,1512.],fatal=['VM is incomplete current lower bound','HC split needs actual hierarchy/child-pin/clock mapping and shared-control physical lanes','No full incident road allocation or GRT/STA proof']))
 Path(sys.argv[1]).write_text(json.dumps(dict(scope='STRUCTURAL_HC_CHAIN_SPLIT_GEOMETRY_OPEN_NOT_ADOPTED',seed=811015,iterations_per_width=6000,halo=21.6,results=out),indent=1))
if __name__=='__main__':main()
