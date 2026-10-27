import sys,json,numpy as np
P=json.load(open(sys.argv[1]+"/die_plan.json"))
for tn in ("q_hub_nw","q_hub_ne"):
  t=P["partition_types"][tn]; W,H=t["outline_um"]; pts={}
  for s in t["internal_stations"]:
    for p in (s["from_um"],s["to_um"]):
      if p[1]<=.5 or p[1]>=H-.5:
        k=("S" if p[1]<=.5 else "N",round(p[0],3)); pts[k]=max(pts.get(k,0),s.get("bits_parallel",s["bits"]))
  res=[]
  for f in "NS":
    for cap in (6.0,3.0):
      d=np.zeros(int(W)+2)
      for (ff,x),b in pts.items():
        if ff!=f: continue
        a=x-b/cap/2; c=x+b/cap/2
        i0=max(0,int(np.floor(a))); i1=min(len(d),int(np.ceil(c)))
        d[i0:i1]+=cap
      g=np.convolve(d,np.ones(4)/4,"same")
      res.append(f"{f}@{cap:.0f}: max {g.max():.1f}/um, um>6: {(g>6.01).sum()}")
  print(tn," | ".join(res))
