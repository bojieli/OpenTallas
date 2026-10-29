import json,collections
F="/srv/opentallas-scratch2/claude/die-qc34/reachfix"
plan=json.load(open(F+"/pg_candidate/access_plan.json"));grid=json.load(open(F+"/readback/pg_rects.json"))
print("dbu",plan["dbu"],plan.get("qualification"))
m9=collections.defaultdict(list)
for r in grid:
  if r[1]=="M9": m9[r[0]].append(r)
bad=0;ex=[]
for j,q in enumerate(plan["paths"]):
  x,y=q["m8"][2:]; ok=any(r[2]<=x/1000-.020 and x/1000+.020<=r[4] and r[3]<=y/1000-.020 and y/1000+.020<=r[5] for r in m9[q["net"]])
  if not ok:
    bad+=1
    if len(ex)<5:
      near=sorted(m9[q["net"]],key=lambda r:min(abs(r[2]-x/1000),abs(r[4]-x/1000)))[:2]; ex.append((j,q["net"],q["members"][:2],x,y,near))
print("paths",len(plan["paths"]),"bad",bad)
for e in ex: print(e)
xs=sorted(set((r[2],r[4]) for r in m9["VSS"]))[:5]; ys=sorted(set((r[3],r[5]) for r in m9["VSS"]))[:5]; print(xs,ys)
G={n:[[round(v*1000) for v in r[2:]] for r in m9[n]] for n in m9}
bad2=sum(1 for q in plan["paths"] if not any(r[0]<=q["m8"][2]-20 and q["m8"][2]+20<=r[2] and r[1]<=q["m8"][3]-20 and q["m8"][3]+20<=r[3] for r in G[q["net"]]))
print("bad_int_dbu",bad2)
