#!/usr/bin/env python3
"""DIE-HBM-6 estimate: x-cut DP on hub residual soft cells (Codex safe405 partial banks) choosing LOW-crossing cut lines.
cells(x) = soft contents + 1.3 x unbanked station bits (bank-retained bits removed at bank x); crossing(x) from cut_orient."""
import json,sys,math,collections
p=json.load(open(sys.argv[1]));co=json.load(open(sys.argv[2]));sb=json.load(open(sys.argv[3]));CAP=float(sys.argv[4]) if len(sys.argv)>4 else 360000
step=43.2;out={}
for tn in ("q_hub_nw","q_hub_ne"):
  t=p["partition_types"][tn];W,H=t["outline_um"];n=int(W/step)+1
  cells=[0.0]*n
  hc={h["inst"] for h in t["hard_cores"]}
  for c in t["contents"]:
    if any(h==c["inst"] or h.startswith(c["inst"]+"_") or h.startswith(c["inst"]+".") for h in hc):continue
    cells[min(n-1,int((c["origin_um"][0]+c["outline_um"][0]/2)//step))]+=c["cells"]
  for s in t["internal_stations"]:
    for r in s["regs_um"]: cells[min(n-1,int(r[0]//step))]+=1.3*s["bits"]
  for b in sb["banks"][tn]:
    sx=b["site"][0]*34.56; cells[min(n-1,int(sx//step))]-=1.3*b["used"]
  cross={round(x/step):v for x,v in co[tn]["vcut_profile_full"]} if "vcut_profile_full" in co[tn] else None
  # rebuild crossing at step from profile (cut_orient step=43.2)
  cr=dict((round(x/step),v) for x,v in co[tn]["hcut_profile"][:0])
  prof=co[tn]["vcut_full"]
  cr={i:v for i,v in prof}
  hard=[(h["origin_um"][0],h["origin_um"][0]+h["outline_um"][0],h["outline_um"][1]) for h in t["hard_cores"]]
  def body_len(x): return sum(hh for a,b,hh in hard if a<x<b)
  facecap={i:6*max(0.0,H-body_len(i*step)) for i in range(1,n)}
  pre=[0.0]
  for v in cells: pre.append(pre[-1]+v)
  # DP over cut indices: minimise max crossing/cap ratio, parts <= CAP
  INF=1e18;best={0:(0,0.0,None)}  # idx -> (nparts, worst_ratio, prev)
  idxs=[0]+list(range(1,n))+[n]
  order=sorted(set(idxs))
  dp={0:(0.0,0,None)}
  for j in order[1:]:
    cand=None
    for i in dp:
      if i>=j: continue
      if pre[j]-pre[i]>CAP: continue
      w=dp[i][0]
      if j<n:
        w=max(w,cr.get(j,0)/max(1.0,facecap[j]))
      k=dp[i][1]+1
      key=(w,k)
      if cand is None or key<(cand[0],cand[1]): cand=(w,k,i)
    if cand: dp[j]=cand
  if n not in dp: out[tn]="NO_SOLUTION";print(tn,"NO SOLUTION");continue
  cuts=[];j=n
  while dp[j][2] is not None:
    i=dp[j][2]
    if i>0: cuts.append(i)
    j=i
  cuts=sorted(cuts);bounds=[0]+cuts+[n]
  parts=[round(pre[b]-pre[a]) for a,b in zip(bounds,bounds[1:])]
  cl=[dict(x_um=round(c*step,2),crossing_bits=cr.get(c,0),face_cap_6um=round(facecap[c]),ratio=round(cr.get(c,0)/max(1,facecap[c]),3),bodies_cut=sum(1 for a,b,hh in hard if a<c*step<b)) for c in cuts]
  out[tn]=dict(total_cells=round(pre[n]),parts=parts,cuts=cl,worst_ratio=round(dp[n][0],3))
  print(tn,json.dumps(out[tn]))
json.dump(out,open(sys.argv[5] if len(sys.argv)>5 else "dp_cuts.json","w"),indent=1)
