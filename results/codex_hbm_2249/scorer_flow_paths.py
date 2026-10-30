#!/usr/bin/env python3
"""Capacity-driven finite path construction for actual 2176+570b row1 hub-source graph; no P&R claim."""
import sys,json,copy,heapq,time,math
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import lane_add as L
src,out=map(Path,sys.argv[2:4]);out.mkdir(parents=True,exist_ok=False);r=json.loads((src/'die_plan.json').read_text())
def can_alloc(B,a,b,w):
 q=B.alloc(a,b,w)
 if not q:return False
 f,win,_=q;B.taken[(a,f)].remove(tuple(win));B.taken[(b,L.OPP[f])].remove(tuple(win));return True
def paths(B,w,src='NW_hub',dst='NW_b102'):
 cap={};heap=[(0.,(src,))];n=0
 while heap:
  cost,ch=heapq.heappop(heap);u=ch[-1]
  if u==dst:
   yield list(ch);n+=1
   if n==12:return
   continue
  if len(ch)>=17:continue
  for v in B.neighbours(u):
   if v in ch or not v.startswith('NW_')or any(v.startswith('NW_'+x)for x in ('sm','io','spb')):continue
   if len(ch)>1 and L.shared_edge(B.P,u,ch[-2])[0]==L.shared_edge(B.P,u,v)[0]:continue
   edge=tuple(sorted((u,v)))
   if edge not in cap:cap[edge]=can_alloc(B,u,v,w)
   if not cap[edge]:continue
   a,b=L.centre(B.P,u),L.centre(B.P,v);d=abs(a[0]-b[0])+abs(a[1]-b[1]);heapq.heappush(heap,(cost+d,ch+(v,)))
report=[]
for name,widths in [('three_source_groups',[1088,1088,570]),('split_key_halves',[544,544,544,544,570]),('small_coherent_slices',[272]*8+[285,285])]:
 B=L.Builder(copy.deepcopy(r),near_um=20000,max_hops=16,require_cycle_match=False,first_id=900);B.shared=set();rows=[]
 for num,w in enumerate(widths):
  attempts=[];solved=None
  for chain in paths(B,w):
   t=time.time();got=B.build_one('NW_hub','NW_b102',w,chain,'path',None,record=False)
   attempts.append(dict(chain=chain,why=None if got else B._why,seconds=round(time.time()-t,3)))
   if got:solved=got;break
  row=dict(group=num,bits=w,result=solved,attempts=attempts);rows.append(row);print(name,json.dumps(row),flush=True)
  if not solved:break
 ok=len(rows)==len(widths)and all(x['result']for x in rows)
 report.append(dict(variant=name,all_solved=ok,rows=rows))
 if ok:
  d=out/name;d.mkdir();(d/'die_plan.json').write_text(json.dumps(B.raw,indent=1)+'\n')
(out/'flow_paths_report.json').write_text(json.dumps(report,indent=1)+'\n')
