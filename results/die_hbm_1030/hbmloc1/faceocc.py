import json,sys
sys.path.insert(0,sys.argv[1])
import schema as S, lane_add as LA
raw=json.load(open(sys.argv[2])); P=S.Plan(raw)
B=LA.Builder(raw, near_um=1e9, max_hops=6, require_cycle_match=False)
print("reach",B.reach,"smax",B.smax,"guard",B.guard)
for a,b in [x.split(":") for x in sys.argv[3].split(",")]:
    se=LA.shared_edge(P,a,b)
    if not se: print(a,b,"no edge"); continue
    f=se[0]
    occ=sorted(LA.face_intervals(P,a,f)+LA.face_intervals(P,b,LA.OPP[f]))
    occ=[(round(x0),round(x1)) for x0,x1 in occ if x1>se[1] and x0<se[2]]
    used=sum(min(x1,se[2])-max(x0,se[1]) for x0,x1 in occ)
    # largest free gap
    pts=[se[1]]+[v for o in occ for v in o]+[se[2]]
    gaps=[]; cur=se[1]
    for x0,x1 in sorted(occ):
        if x0>cur: gaps.append(round(x0-cur))
        cur=max(cur,x1)
    if se[2]>cur: gaps.append(round(se[2]-cur))
    print(a,b,f,round(se[1]),round(se[2]),"used",round(used),"maxgap",max(gaps or [0]),"n",len(occ))
