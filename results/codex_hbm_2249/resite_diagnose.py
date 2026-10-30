#!/usr/bin/env python3
import sys,json
from pathlib import Path
import numpy as np
sys.path.insert(0,sys.argv[1]);import lane_add as L;import station_resite as SR;import schema as S
r=json.load(open(sys.argv[2]));B=L.Builder(r,near_um=20000,max_hops=16,require_cycle_match=False);B.shared=set()
chain=['NW_hub','NW_b000','NW_b010','NW_b001','NW_b011','NW_b002','NW_b012','NW_b003','NW_b103','NW_b102']
orig=B.resite
records=[]
def resite(chain,slots,start,end):
 capture=[];route0=SR.route
 def hook(f,a,b,n,reach):
  regs=route0(f,a,b,n,reach);capture.append(dict(regs=regs,shape=f.shape,free=int(f.sum()),a=a,b=b,n=n,reach=reach));return regs
 SR.route=hook
 try:got=orig(chain,slots,start,end)
 finally:SR.route=route0
 row=dict(chain=chain,start=start,end=end,result=got,capture=capture)
 if capture and capture[-1]['regs']:
  rects=[B.P.rect(sl[0])for sl in slots];X0=min(x[0]for x in rects);Y0=min(x[1]for x in rects);owned=[]
  for x,y in capture[-1]['regs']:
   x+=X0;y+=Y0;owner=[k for k,(a,b,c,d)in enumerate(rects)if a+SR.HALO<x<c-SR.HALO and b+SR.HALO<y<d-SR.HALO];owned.append(owner)
  row['owners']=owned;counts=[sum(k in o for o in owned)for k in range(len(slots))];row['slots']=[dict(part=sl[0],nst=sl[8],route_length=sl[10],actual_count=cnt,r3_ratio=None if not cnt else sl[10]/cnt)for sl,cnt in zip(slots,counts)]
 records.append(row);return got
B.resite=resite
got=B.build_one(chain[0],chain[-1],1088,chain,'path',None,record=False)
print(json.dumps(dict(result=got,why=None if got else B._why,records=records),indent=1))
