"""HBM-CLKLOC-1 estimate: per region, in-region tree reach from the B (d44f street_body) region root, and the
12.4a b1 OCV pessimism of a balanced tree of that reach (clk_aocv g021 table, class Ainv, shared droop = same region)."""
import json,sys,collections,math
B,W,OUT=sys.argv[1],sys.argv[2],sys.argv[3]
sys.path.insert(0,W+"/tools/die_plan")
import clk_aocv as CA
T=CA.load(W+"/tools/die_plan/clk_aocv_table_g021.json")
rm=json.load(open(B+"/street_part_region.json"))["part_region"]
t=json.load(open(B+"/k1/kit/clock/tree.json")); a=json.load(open(B+"/proof/tap_arrivals_TT.json"))
arr={x["port"]:x for x in a["taps"]}
sites=t["sites"]; nodes=t["nodes"]
rootbuf={}
for i,nd in nodes.items():
    if nd.get("region_root") is not None and nd.get("feed"):
        rootbuf.setdefault(nd["region_root"],[]).append("b"+str(i))
V=float(sys.argv[4]) if len(sys.argv)>4 else 280.0
DF=float(sys.argv[5]) if len(sys.argv)>5 else 0.0   # >0: street tree reach = DF x Manhattan reach (instead of routed B reach)
SPS=float(sys.argv[6]) if len(sys.argv)>6 else 44.0      # ps/mm routed inv2 1x incl. cells (regB late/path)
R=collections.defaultdict(list)
for tp in t["taps"]:
    rg=rm.get(tp["part"]); rb=set(rootbuf.get(rg,[]))
    idx=max([k for k,c in enumerate(tp["path"]) if c in rb],default=None)
    if idx is None: continue
    L=0; prev=None
    for c in tp["path"][idx:]:
        xy=sites.get(c)
        if xy is None: continue
        if prev: L+=abs(xy[0]-prev[0])+abs(xy[1]-prev[1])
        prev=xy
    L+=abs(tp["xy"][0]-prev[0])+abs(tp["xy"][1]-prev[1])
    rx=sites[tp["path"][idx]]
    R[rg].append(dict(L=L,man=abs(tp["xy"][0]-rx[0])+abs(tp["xy"][1]-rx[1]),xy=tp["xy"],late=arr.get(tp["port"],{}).get("late_ps")))
res=[]
for rg,ts in sorted(R.items()):
    xs=[x["xy"][0] for x in ts]; ys=[x["xy"][1] for x in ts]
    w,h=max(xs)-min(xs),max(ys)-min(ys)
    Lmax=max(x["L"] for x in ts); Lmin=min(x["L"] for x in ts); Mmax=max(x["man"] for x in ts)
    # balanced-tree reach: the routed reach of the longest tap (detours included) is the insertion every tap gets
    Lmax = DF*Mmax if DF>0 else Lmax
    U=V*Lmax/1000.0                       # ps, unshared per side for a pair that splits at the region root
    st=max(1,round(U/SPS))               # inv stages (44 ps/stage measured on B: late/stages)
    br=dict(cell_ps=U*0.6248,net_ps=U*(1-0.6248),stages={"Ainv":st})
    core=dict(cell_ps=250*0.879,net_ps=250*0.121,stages={"B":7})
    d=math.hypot(w,h)
    p_clk=CA.branch_pessimism(T,"TT",br,br,d,True,"setup")
    p_core=CA.branch_pessimism(T,"TT",core,core,d,True,"setup")
    res.append(dict(region=rg,parts=sorted(set(p for p,r in rm.items() if r==rg)),taps=len(ts),bbox_mm=[round(w/1e3,2),round(h/1e3,2)],
                    reach_routed_mm=round(Lmax/1e3,2),reach_min_mm=round(Lmin/1e3,2),reach_manhattan_mm=round(Mmax/1e3,2),
                    detour_x=round(Lmax/max(Mmax,1),2),insertion_ps=round(U),stages=st,ocv_clk_ps=round(p_clk,1),ocv_core_ps=round(p_core,1),
                    ocv_total_ps=round(p_clk+p_core,1),nominal_budget_ps=round(150-p_clk-p_core,1)))
json.dump(res,open(OUT,"w"),indent=0)
print("region parts taps bbox reach(routed/manh mm) detour ins_ps stages ocv(clk+core) nominal_budget")
for r in sorted(res,key=lambda r:r["nominal_budget_ps"]):
    print(r["region"],",".join(r["parts"])[:34].ljust(34),r["taps"],r["bbox_mm"],r["reach_routed_mm"],r["reach_manhattan_mm"],r["detour_x"],r["insertion_ps"],r["stages"],r["ocv_clk_ps"],r["ocv_core_ps"],r["nominal_budget_ps"])
