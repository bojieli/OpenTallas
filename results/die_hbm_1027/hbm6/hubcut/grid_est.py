#!/usr/bin/env python3
"""DIE-HBM-6 estimate: hub regional grids (nx x ny): crossing bits per internal face vs 6/um x free face length,
residual soft cells per region (Codex safe405 banks removed), and chain-corridor overlap census."""
import json,sys,math,collections
p=json.load(open(sys.argv[1]));sb=json.load(open(sys.argv[2]));out={}
for tn in ("q_hub_nw","q_hub_ne"):
  t=p["partition_types"][tn];W,H=t["outline_um"];hard=t["hard_cores"]
  banked=collections.Counter()
  for b in sb["banks"][tn]: banked[(b["site"][0],b["site"][1])]+=b["used"]
  res={}
  for nx,ny in ((3,2),(4,2),(2,3),(6,1),(3,3),(4,3)):
    xs=[W*i/nx for i in range(1,nx)];ys=[H*j/ny for j in range(1,ny)]
    cells=collections.Counter();face=collections.Counter()
    def reg(x,y): return (min(nx-1,int(x/(W/nx))),min(ny-1,int(y/(H/ny))))
    hc={h["inst"] for h in hard}
    for c in t["contents"]:
      if any(h==c["inst"] or h.startswith(c["inst"]+"_") or h.startswith(c["inst"]+".") for h in hc):continue
      cells[reg(c["origin_um"][0]+c["outline_um"][0]/2,c["origin_um"][1]+c["outline_um"][1]/2)]+=c["cells"]
    for s in t["internal_stations"]:
      pts=[s["from_um"]]+s["regs_um"]+[s["to_um"]];b=s["bits"]
      for r in s["regs_um"]: cells[reg(*r)]+=1.3*b
      for a,c in zip(pts,pts[1:]):
        ra,rc=reg(*a),reg(*c)
        if ra==rc: continue
        # Manhattan L: x first then y
        for i,x in enumerate(xs):
          if min(a[0],c[0])<x<=max(a[0],c[0]): face[("v",i,reg(x,a[1])[1])]+=b
        for j,y in enumerate(ys):
          if min(a[1],c[1])<y<=max(a[1],c[1]): face[("h",j,reg(c[0],y)[0])]+=b
    for b in sb["banks"][tn]:
      cells[reg(b["site"][0]*34.56,b["site"][1]*34.56)]-=1.3*b["used"]
    worst=0;rows=[]
    for k,v in face.items():
      L=(H/ny) if k[0]=="v" else (W/nx)
      cap=6*L; worst=max(worst,v/cap); rows.append((k,v,round(cap)))
    res[f"{nx}x{ny}"]=dict(max_region_cells=round(max(cells.values())),regions_over_360k=sum(v>360000 for v in cells.values()),
                          worst_face_ratio=round(worst,2),faces_over=sum(v>c for _,v,c in rows),faces=len(rows),
                          max_face_bits=max(v for _,v,_ in rows))
  out[tn]=res;print(tn,json.dumps(res))
json.dump(out,open(sys.argv[3],"w"),indent=1)
