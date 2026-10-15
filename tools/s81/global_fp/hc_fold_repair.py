#!/usr/bin/env python3
"""Explicit 64 HC row placement screen; unplaced control and VM geometry keep status OPEN."""
import json,random,math,sys
from pathlib import Path
import candidates as C
from hc_strip_repair import pack

def main():
 g=json.loads(Path('results/arch/s81_globalfp_1015/graph.json').read_text());base=C.base_rects(g)
 dims={n:base[n][2:] for n in C.MOVABLE if n not in ('sp_hc_s','sp_hc_t')};dims['sp_vm']=[1965.6,9828.];dims['mix4']=[1613.5,1542.2];dims['sp_pq'][0]=1728.
 soft={}
 for par,nrows,growth in [('sp_hc_s',10,388.8),('sp_hc_t',12,466.56)]:
  for c in range(3):
   for r in range(nrows if par=='sp_hc_s' or c!=1 else 10):dims[f'{par}_c{c}_row{r}']=[576.72,810.]
  residual=base[par][2]*(base[par][3]+growth)-(3*nrows if par=='sp_hc_s' else 34)*576.72*810.
  assert residual>0
  for c in range(3):
   name=f'{par}_UNMAPPED_control_reserve{c}';dims[name]=[605.512,residual/(3*605.512)];soft[name]=dims[name]
 rng=random.Random(660810);allresults=[]
 for roadw in [432.,648.]:
  W=5097.6-roadw;best=(1e20,None);fixed=['sp_su_s','sp_vm'];tail=[n for n in dims if n not in fixed]
  for restart in range(2):
   rng.shuffle(tail);order=fixed+tail;cur,_=pack(order,dims,W)
   for i in range(250):
    nxt=order[:];a,b=rng.sample(range(2,len(order)),2);nxt[a],nxt[b]=nxt[b],nxt[a];hh,rs=pack(nxt,dims,W)
    if hh<best[0]:best=(hh,rs)
    temp=200*(.01**(i/250))
    if hh<cur or rng.random()<math.exp(min(0,(cur-hh)/temp)):order,cur=nxt,hh
  h,rs=best;rr={n:[r[0]+13942.8,r[1]+1807.9,r[2],r[3]] for n,r in rs.items()}
  chains=[]
  for par,nrows in [('sp_hc_s',10),('sp_hc_t',12)]:
   for c in range(3):
    count=nrows if par=='sp_hc_s' or c!=1 else 10;seq=[rr[f'{par}_c{c}_row{r}'] for r in range(count)];hops=[]
    for p,q in zip(seq,seq[1:]):
     L=abs(p[0]-q[0])+abs(p[1]+p[3]-q[1]);hops.append(dict(distance_um=L,minimum_extra_relay_stages=max(0,math.ceil(L/500)-1)))
    chains.append(dict(parent=par,chain=c,rows=count,source_stage_indices=list(range((0,22,42)[c],(0,22,42)[c]+10)) if par=='sp_hc_s' else list(range((10,32,52)[c],(10,32,52)[c]+count)),hops=hops,total_minimum_extra_cycles=sum(t['minimum_extra_relay_stages'] for t in hops)))
  allresults.append(dict(road_width=roadw,packed_height=h,free_vertical_margin=21824.1-h-21.6-799.2,limit_height=21824.1-799.2,fit=h+21.6+799.2<=21824.1,fit_with1512=h+21.6+1512<=21824.1,rectangles=rr,soft_unmapped_control_reserves=soft,road=[19040.4-roadw,1807.9,roadw,21824.1],corridor=[13942.8,1807.9+h+21.6,5097.6,799.2],chains=chains))
  print(roadw,h,flush=True)
 Path(sys.argv[1]).write_text(json.dumps(dict(scope='HC_ROW_REPARTITION_SCREEN_GEOMETRY_OPEN',source_rows='3 chains times10head; tail12/10/12rows,64total; contract_v23_hc_budget and parent NORM810 correction pending',source_vm='Partial1965.6x9828 body only; incomplete currentinventory',fatal=['Control reserves preserve aggregate area only, not source-native control shapes or pin topology','Rows arbitrarily reordered physically; actual paired3056/2164 buses, registered turns, clocks, TT/FF/DRC and static compiler stage ages unproven','New BF x2 adds538 onEbroadcast: baseline peak5324 becomes5862 ifcoincident, road432share0.643FAIL; baseline21.09375capacity excludesclock/PG' ],results=allresults),indent=1))
if __name__=='__main__':main()
