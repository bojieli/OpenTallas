"""DIE-HEAD-3 PROVISIONAL count-aligned margins per crossing of any region table (generalises DIE-HEAD-2 ca_margin.py;
MESO-COUNT-2 K fix not landed).  Arrivals spice-scaled x SCALE (OSS-CLOCK-2 ruling 21:10: plan-time margins x1.05):
d, p_dn, p_up, unshared all x SCALE.  K per crossing from the derated lag: L in K*T + [d - p_dn - w, d + p_up + w]
(TT+FF union, w = 5% unshared), gate window [0.5T+ap, (D-0.5)T-ap], ap=T/8; K = smallest with low >= 100; D = 4 if
high >= 100 else 8.  usage: ca3.py LANDED_OCV.json REGIONS_TABLE.json OUT.json [--scale 1.05]"""
import json,math,sys
from collections import Counter
ocv,tab,out=sys.argv[1:4]
SC=float(sys.argv[sys.argv.index("--scale")+1]) if "--scale" in sys.argv else 1.05
T=833.333;ap=T/8;lo_win=0.5*T+ap
d=json.load(open(ocv));tp={r["port"]:r for r in json.load(open(tab))["ports"]}
cs=[k for k in d["corners"] if k.startswith("TT_droop-regions") and d["corners"][k].get("all")][:1]+[k for k in d["corners"] if k.startswith("FF_droop-regions") and d["corners"][k].get("all")][:1]
rows={r["port"]:dict(r) for r in d["corners"][cs[0]]["all"] if r["port"] in tp}
for r0 in d["corners"][cs[1]]["all"]:
    if r0["port"] not in rows:continue
    r=rows[r0["port"]];lo=min(r["d_ps"]-r["p_dn_ps"],r0["d_ps"]-r0["p_dn_ps"]);hi=max(r["d_ps"]+r["p_up_ps"],r0["d_ps"]+r0["p_up_ps"])
    r["p_dn_ps"],r["p_up_ps"]=r["d_ps"]-lo,hi-r["d_ps"]
    for k in ("unshared_a_ps","unshared_b_ps"):r[k]=max(r.get(k,0.0),r0.get(k,0.0))
missing=sorted(set(tp)-set(rows))
res=[]
for p,r in sorted(rows.items()):
    w=0.05*SC*max(r.get("unshared_a_ps",0),r.get("unshared_b_ps",0))
    a,b=SC*(r["d_ps"]-r["p_dn_ps"])-w,SC*(r["d_ps"]+r["p_up_ps"])+w
    kg=math.ceil((lo_win+100-a)/T)
    lo=kg*T+a-lo_win;D=None
    for DD in (4,8):
        hi=(DD-0.5)*T-ap-(kg*T+b)
        if hi>=100:D=DD;break
    res.append(dict(port=p,src=tp[p]["src"],dst=tp[p]["dst"],width=tp[p]["width"],d_ps=round(SC*r["d_ps"],1),K=kg,low=round(lo,1),high=round(hi,1),depth=D,
                    lat_cycles=kg+1,passes=lo>=100 and hi>=100 and D is not None))
sig=Counter((x["K"],x["depth"]) for x in res)
s=dict(scale=SC,crossings=len(res),missing_in_ocv=missing,pass_=sum(x["passes"] for x in res),fail=sum(not x["passes"] for x in res),
  worst_low=min(x["low"] for x in res),worst_high=min(x["high"] for x in res),depth=dict(Counter(x["depth"] for x in res)),
  lat_hist=dict(Counter(x["lat_cycles"] for x in res)),K_depth_signatures={f"K{k}D{d}":n for (k,d),n in sig.items()},
  worst_low_port=min(res,key=lambda x:x["low"])["port"],worst_high_port=min(res,key=lambda x:x["high"])["port"],
  label="PROVISIONAL/UNCHECKED: MESO-COUNT-2 K fix not landed; K from derated lag, spice-scaled arrivals")
json.dump(dict(summary=s,crossings=res),open(out,"w"),indent=0);print(json.dumps(s,indent=1))
