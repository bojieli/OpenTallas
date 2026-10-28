"""DIE-HEAD-2 PROVISIONAL count-aligned margins per crossing (MESO-COUNT-2 K fix NOT landed).
K for EVERY crossing (tree edges included, all 39 clean) from the derated lag (NC 20:47 fix (1)):
L in K*T + [d - p_dn - w, d + p_up + w] (TT+FF union, w = 5% unshared), gate window [0.5T+ap, (D-0.5)T-ap], ap=T/8.
K = smallest with low margin >= 100 (gate); D = 4 if high >= 100 else 8. Also reports min-K (tool rule) margins."""
import json,math,sys
from collections import Counter
ocv,tab,ca,out=sys.argv[1:5]
T=833.0;ap=T/8;lo_win=0.5*T+ap
d=json.load(open(ocv));ports={r["port"] for r in json.load(open(tab))["ports"]}
cs=["TT_droop-regions_corelat250","FF_droop-regions_corelat202.5"]
rows={r["port"]:dict(r) for r in d["corners"][cs[0]]["all"] if r["port"] in ports}
for r0 in d["corners"][cs[1]]["all"]:
    if r0["port"] not in rows:continue
    r=rows[r0["port"]];lo=min(r["d_ps"]-r["p_dn_ps"],r0["d_ps"]-r0["p_dn_ps"]);hi=max(r["d_ps"]+r["p_up_ps"],r0["d_ps"]+r0["p_up_ps"])
    r["p_dn_ps"],r["p_up_ps"]=r["d_ps"]-lo,hi-r["d_ps"]
    for k in ("unshared_a_ps","unshared_b_ps"):r[k]=max(r.get(k,0.0),r0.get(k,0.0))
assert len(rows)==len(ports)==94,(len(rows),len(ports))
cap={c["port"]:c for c in json.load(open(ca))["crossings"]}
res=[]
for p,r in sorted(rows.items()):
    w=0.05*max(r.get("unshared_a_ps",0),r.get("unshared_b_ps",0))
    a,b=r["d_ps"]-r["p_dn_ps"]-w,r["d_ps"]+r["p_up_ps"]+w
    assert abs(r["d_ps"]-cap[p]["d_ps"])<0.01
    k0=math.ceil((lo_win-a)/T);kg=math.ceil((lo_win+100-a)/T)
    def m(k):
        lo=k*T+a-lo_win
        for D in (4,8):
            hi=(D-0.5)*T-ap-(k*T+b)
            if hi>=100:return lo,hi,D
        return lo,hi,None
    lo0,hi0,D0=m(k0);lo,hi,D=m(kg)
    res.append(dict(port=p,src=cap[p]["src"],dst=cap[p]["dst"],kind=cap[p]["kind"],d_ps=r["d_ps"],L_lo=round(k0*T+a,1),L_hi=round(k0*T+b,1),
        minK_low=round(lo0,1),minK_high=round(hi0,1),gateK_low=round(lo,1),gateK_high=round(hi,1),depth=D,lat_cycles=kg+1,lat_minK=k0+1,
        tool_lat=cap[p]["lat_cycles"],passes=lo>=100 and hi>=100 and D is not None))
s=dict(crossings=len(res),pass_=sum(x["passes"] for x in res),fail=sum(not x["passes"] for x in res),
  worst_low=min(x["gateK_low"] for x in res),worst_high=min(x["gateK_high"] for x in res),
  minK_worst_low=min(x["minK_low"] for x in res),minK_below100=sum(x["minK_low"]<100 for x in res),
  minK_tree_below100=sum(x["minK_low"]<100 and x["kind"]=="tree" for x in res),
  depth=dict(Counter(x["depth"] for x in res)),lat_hist=dict(Counter(x["lat_cycles"] for x in res)),
  lat_minK_hist=dict(Counter(x["lat_minK"] for x in res)),tool_lat_hist=dict(Counter(x["tool_lat"] for x in res)),
  lat_changed_vs_tool=sum(x["lat_cycles"]!=x["tool_lat"] for x in res),
  label="PROVISIONAL/UNCHECKED: MESO-COUNT-2 K fix not landed; K from derated lag incl. tree edges",
  worst_low_port=min(res,key=lambda x:x["gateK_low"])["port"],worst_high_port=min(res,key=lambda x:x["gateK_high"])["port"])
json.dump(dict(summary=s,crossings=res),open(out,"w"),indent=0);print(json.dumps(s,indent=1))
