import json,math
from pathlib import Path
import numpy as np
d=Path(__file__).parent
lines=(d/"vmdel_geo.txt").read_text().splitlines()
W,H=142.56,112.32
macros=[(30.24,8.64,125.064,49.704),(30.24,61.02,125.064,102.084)]
# Demand-planning slots only: 1.08x.54 pitch vs <=.81x.27 DFF body, <=37.5% FF fill.
slots=[]
for y in np.arange(4.32,H-4.32-.27,.54):
 for x in np.arange(4.32,W-4.32-.81,1.08):
  if any(x<r+4.32 and x+.81>l-4.32 and y<t+4.32 and y+.27>b-4.32 for l,b,r,t in macros):continue
  slots.append((round(float(x),3),round(float(y),3)))
pts=np.array(slots); taken=np.zeros(len(pts),bool)
out=[f"DIE 0 0 {W} {H}",f"CORE 4.32 4.32 {W-4.32} {H-4.32}","PIN ck 71.28 56.16"]
moves=[]
for line in lines:
 t=line.split()
 if t[0]=="SINK":
  old=np.array(list(map(float,t[1:3])));dist=((pts-old)**2).sum(axis=1);dist[taken]=np.inf;i=dist.argmin()
  if not np.isfinite(dist[i]):raise RuntimeError("demand slots exhausted")
  taken[i]=True;p=pts[i];t[1:3]=map(str,p);out.append(" ".join(t));moves.append({"inst":t[4],"old":old.tolist(),"planned":p.tolist(),"move_um":float(math.sqrt(dist[i]))})
 elif t[0]=="MACRO":
  idx=0 if "pc\\[0" in t[1] else 1
  l,b,r,u=macros[idx];t[3:7]=map(str,(l,b,r,u));t[8:10]=map(str,(l+.012,b+.78));out.append(" ".join(t))
out.append("ISLCOUNT 0")
(d/"vmdel_proposed_geo.txt").write_text("\n".join(out)+"\n")
(d/"candidate.json").write_text(json.dumps({"scope":"DEMAND MODEL ONLY, synthetic legal FF targets from actual identities; NOT actual placement; replay actual placement mandatory","outline":[W,H],"clock":[71.28,56.16],"macros":macros,"halo":4.32,"planned_ff":len(moves),"available_ff_slots":len(pts),"max_planned_move_um":max(m["move_um"] for m in moves),"pair_L1_geometric_bound_um":W+H,"moves":moves},indent=2))
