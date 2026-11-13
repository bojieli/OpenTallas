"""park_taps.py PLAN SEED OUT : move non-core clock taps (taps / added_taps) that the seeded cores would cover (+12.96 um)
to the nearest free 4.32-lattice point of the seeded layout (same names, same count).  Report per type."""
import json,sys
G=4.32; CL=12.96
P=json.load(open(sys.argv[1])); SD=json.load(open(sys.argv[2])); n=0; nc=0
for tn,sd in SD.items():
    t=P["partition_types"][tn]; W,H=t["outline_um"]
    R=[]
    for c in t["hard_cores"]:
        x,y=sd.get(c["inst"],{}).get("origin_um",c["origin_um"]); w,h=c["outline_um"]; R.append((x,y,x+w,y+h))
    def bad(p):
        if not (CL<=p[0]<=W-CL and CL<=p[1]<=H-CL): return True
        return any(r[0]-CL<p[0]<r[2]+CL and r[1]-CL<p[1]<r[3]+CL for r in R)
    def inside_base(p):
        return any(c["origin_um"][0]-0.01<=p[0]<=c["origin_um"][0]+c["outline_um"][0]+0.01 and c["origin_um"][1]-0.01<=p[1]<=c["origin_um"][1]+c["outline_um"][1]+0.01 for c in t["hard_cores"])
    ck=t["clock"]; used=[]
    for tp in (ck.get("taps") or [])+(ck.get("added_taps") or []):
        if not isinstance(tp,dict) or not tp.get("xy") or tp.get("kind")=="core": continue
        p=tp["xy"]
        if inside_base(p): continue          # rides on its core
        if not bad(p): used.append(tuple(p)); continue
        best=None
        for r in range(1,120):
            for dx in range(-r,r+1):
                for dy in ((-r,r) if abs(dx)!=r else range(-r,r+1)):
                    q=(round(round((p[0]+dx*G)/G)*G,3),round(round((p[1]+dy*G)/G)*G,3))
                    if not bad(q) and all(abs(q[0]-u[0])+abs(q[1]-u[1])>=43.2 for u in used):
                        d=abs(q[0]-p[0])+abs(q[1]-p[1])
                        if best is None or d<best[0]: best=(d,q)
            if best: break
        tp["xy"]=list(best[1]); used.append(best[1]); n+=1
json.dump(P,open(sys.argv[3],"w"),indent=1); print("taps moved",n,"core taps carried",nc)
