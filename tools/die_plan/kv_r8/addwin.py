# DIAGNOSTIC (CLOCK-KV-R8): declare a planned in-core island window (12.2a1 pushdown) around every pushdown clock cell of a
# build so the combo GRT predicts the equal-leg tree. NOT adoptable until the named cores are rebuilt with these islands.
import json,sys
sys.path.insert(0,sys.argv[2]); import die_clock as DC, schema as S
d=sys.argv[1]; P=S.Plan(S.load(d+"/plan.json")); M=json.load(open(d+"/mesh.json")); C=json.load(open(d+"/place.json"))
ko=DC.keepouts(P); W=[]
for n,c in C.items():
    x0,y0=c["x"],c["y"]; x1=x0+1.62*(1 if c.get("kind")!="stub" else 0.3)+0.2; y1=y0+0.27
    hit=[r for r in ko if not(x1<=r[0] or x0>=r[2] or y1<=r[1] or y0>=r[3])]
    for r in hit: W.append([round(x0-0.108,4),round(y0-0.001,4),round(x1+0.108,4),round(y1+0.001,4),r[4]])
M["island_windows"]=M.get("island_windows",[])+W; M["meta"]["diag_planned_islands"]=len(W)
json.dump(M,open(d+"/mesh.json","w")); print("windows",len(W))
