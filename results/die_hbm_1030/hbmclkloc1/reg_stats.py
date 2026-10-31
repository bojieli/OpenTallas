"""HBM-CLKLOC-1: per-region routed stats of the d44f street_body clock (DIE-HBM-45 B)."""
import json,sys,collections,math
B=sys.argv[1]
rm=json.load(open(B+"/street_part_region.json"))["part_region"]
a=json.load(open(B+"/proof/tap_arrivals_TT.json"))
t=json.load(open(B+"/k1/kit/clock/tree.json"))
sites=t["sites"]
plen={}
for tp in t["taps"]:
    L=0; prev=None
    for c in tp["path"]:
        xy=sites.get(c) or sites.get(c+"_r")
        if xy is None: continue
        if prev: L+=abs(xy[0]-prev[0])+abs(xy[1]-prev[1])
        prev=xy
    L+=abs(tp["xy"][0]-prev[0])+abs(tp["xy"][1]-prev[1])
    plen[tp["port"]]=L
R=collections.defaultdict(list)
for tp in a["taps"]:
    R[rm.get(tp["part"],"?")].append(tp)
out=[]
for r,ts in sorted(R.items()):
    xs=[x["xy_um"][0] for x in ts]; ys=[x["xy_um"][1] for x in ts]
    late=[x["late_ps"] for x in ts]; st=[x["stages_from_root"] for x in ts]
    pl=[plen.get(x["port"],0) for x in ts]
    parts=sorted(set(x["part"] for x in ts))
    out.append(dict(region=r,parts=parts,taps=len(ts),w=max(xs)-min(xs),h=max(ys)-min(ys),late_min=min(late),late_max=max(late),
                    spread=max(late)-min(late),st=(min(st),max(st)),path_mm=(min(pl)/1e3,max(pl)/1e3)))
json.dump(out,open(sys.argv[2],"w"),indent=0)
for o in sorted(out,key=lambda o:-o["spread"]):
    print(f'{o["region"]} {",".join(o["parts"])[:40]:40s} n{o["taps"]:4d} bbox {o["w"]/1e3:5.2f}x{o["h"]/1e3:5.2f} late {o["late_min"]:7.0f}-{o["late_max"]:7.0f} spread {o["spread"]:6.0f} st {o["st"]} path {o["path_mm"][0]:6.2f}-{o["path_mm"][1]:6.2f} mm')
