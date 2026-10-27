import json,sys,collections
sys.path.insert(0,sys.argv[2]); import die_clock as DC, schema as S
B=sys.argv[1]; P=S.Plan(S.load(f"{B}/plan.json")); M=json.load(open(f"{B}/mesh.json"))
ko=DC.keepouts(P)
def hit(x,y): return [r for r in ko if r[0]<=x<=r[2] and r[1]<=y<=r[3]]
pts=[("drv",dv["ideal"]) for dv in M["drivers"].values() if dv["move_um"]>0]
# nodes: reconstruct ideal from b + move along any axis that hits
for h in M["htree"]:
    d=h.get("node_move_um") or 0
    if d>0:
        bx,by=h["b"]
        for c in ((bx+d,by),(bx-d,by),(bx,by+d),(bx,by-d)):
            if hit(*c): pts.append(("node",c)); break
per=collections.defaultdict(lambda: collections.defaultdict(set))
inst_of_type=collections.defaultdict(set)
for role,(x,y) in pts:
    for r in hit(x,y):
        part,core=r[4].split("/",1); t=P.parts[part]["type"]
        # local coordinate within the core rect, normalised by orientation via rect lower-left (orientation ignored: report mirrored too)
        lx,ly=round(x-r[0],2),round(y-r[1],2); w,hh=r[2]-r[0],r[3]-r[1]
        key=(t.split("_v")[0],core.split("__")[-1],round(w,2),round(hh,2))
        canon=min((lx,ly),(round(w-lx,2),ly),(lx,round(hh-ly,2)),(round(w-lx,2),round(hh-ly,2)))
        per[key][r[4]].add((role,canon))
for key,inst in sorted(per.items()):
    sets=[frozenset(v) for v in inst.values()]; u=set().union(*sets)
    print(key,"inst",len(inst),"pts/inst",sorted(len(s) for s in sets)[:3],"..",max(len(s) for s in sets),"union",len(u),"identical",len(set(sets))==1)
