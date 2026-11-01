#!/usr/bin/env python3
"""DIE-HBM-57: station bit-site cells / clump regs inside partition contents or hard_cores boxes (probe blockages that
check.py geometry does not see: it checks placed_macro_boxes only). cbox.py PLAN [types...]"""
import json,sys,numpy as np,collections
d=json.load(open(sys.argv[1])); only=set(sys.argv[2:])
tot=collections.Counter()
for tn,t in d["partition_types"].items():
  if only and tn not in only: continue
  B=[(c.get("inst"),c["origin_um"][0],c["origin_um"][1],c["origin_um"][0]+c["outline_um"][0],c["origin_um"][1]+c["outline_um"][1])
     for c in [c for c in (t.get("contents") or []) if c.get("status")=="reuse"]+(t.get("hard_cores") or []) if c.get("origin_um") and c.get("outline_um")]
  if not B: continue
  for s in t.get("ft_slots",[]):
    if s.get("bit_sites_um"):
      w,h=s["bit_site_cell_um"]
      for j,b in enumerate(s["bit_sites_um"]):
        b=np.array(b,float)
        for nm,x0,y0,x1,y1 in B:
          hit=((np.minimum(b[:,0]+w,x1)-np.maximum(b[:,0],x0))>1e-3)&((np.minimum(b[:,1]+h,y1)-np.maximum(b[:,1],y0))>1e-3)
          if hit.any(): tot[(tn,s["name"],j+1,nm)]+=int(hit.sum())
    else:
      for j,(x,y) in enumerate(s.get("regs_um") or []):
        for nm,x0,y0,x1,y1 in B:
          if x0+1e-3<x<x1-1e-3 and y0+1e-3<y<y1-1e-3: tot[(tn,s["name"],j,nm+"(clump)")]+=1
for k,v in sorted(tot.items()): print(v,*k)
print("TOTAL slot-stage hits",len(tot),"types",len({k[0] for k in tot}))
