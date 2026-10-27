import json,sys,collections
sys.path.insert(0,sys.argv[2]); import die_clock as DC, schema as S
B=sys.argv[1]; P=S.Plan(S.load(f"{B}/plan.json")); M=json.load(open(f"{B}/mesh.json"))
ko=DC.keepouts(P)
def hits(x,y): return [r[4] for r in ko if r[0]-0.5<=x<=r[2]+0.5 and r[1]-0.5<=y<=r[3]+0.5]
cnt=collections.Counter()
for h in M["htree"]:
    d=h.get("node_move_um") or 0
    if d<=0 or h["level"]<7: continue
    bx,by=h["b"]; found=None
    for cx,cy in ((bx+d,by),(bx-d,by),(bx,by+d),(bx,by-d)):
        hh=hits(cx,cy)
        if hh: found=hh; break
    key=(h["level"],round(d,1),tuple(sorted(set(x.split("/")[1].split("__")[-1] if "/" in x else x for x in (found or ["?"])))))
    cnt[key]+=1
for k,v in sorted(cnt.items()): print(v,k)
# drivers moved
dc=collections.Counter()
for k,dv in M["drivers"].items():
    if dv["move_um"]>0:
        hh=hits(*dv["ideal"]); dc[tuple(sorted(set(x.split("/")[-1].split("__")[-1] for x in hh)))]+=1
print("drivers moved",sum(dc.values()),"of",len(M["drivers"])); 
for k,v in dc.most_common(12): print(" ",v,k)
