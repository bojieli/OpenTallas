"""finalize.py BASE_PLAN NEW_PLAN OUT [--types-from EV.json ...] : die-owned points never move with a core.
core_place carries every point that lies inside a core in the base plan; the type clock tap (clock.tap_um, the die
H-tree sink of the tile lattice), the reset tap and edge clocks are die geometry: restore them to the base value and
check that the restored point is free (>= 8.64 um off every core) in the new layout.  Only types that differ are touched."""
import json,sys
B=json.load(open(sys.argv[1])); N=json.load(open(sys.argv[2])); bad=0; n=0; nct=0
for tn,t in N["partition_types"].items():
    b=B["partition_types"].get(tn)
    if b is None or not tn.startswith("col_h"): continue
    if json.dumps(t["hard_cores"],sort_keys=True)==json.dumps(b["hard_cores"],sort_keys=True): continue
    R=[(c["origin_um"][0],c["origin_um"][1],c["origin_um"][0]+c["outline_um"][0],c["origin_um"][1]+c["outline_um"][1]) for c in t["hard_cores"]]
    def free(p): return not any(r[0]-8.64<p[0]<r[2]+8.64 and r[1]-8.64<p[1]<r[3]+8.64 for r in R)
    for sec,key in (("clock","tap_um"),("reset","tap_um")):
        if isinstance((b.get(sec) or {}).get(key),list) and t[sec].get(key)!=b[sec][key]:
            t[sec][key]=list(b[sec][key]); n+=1
            if not free(t[sec][key]): bad+=1; print("NOT FREE",tn,sec,key,t[sec][key])
    # core taps (kind "core") sit at their core's clock pin: base xy + the core's displacement, exactly once
    co={c["inst"]:c["origin_um"] for c in t["hard_cores"]}; cb={c["inst"]:c["origin_um"] for c in b["hard_cores"]}
    tb={a_["name"]:a_ for a_ in (b["clock"].get("taps") or []) if isinstance(a_,dict)}
    for a_ in t["clock"].get("taps") or []:
        if isinstance(a_,dict) and a_.get("kind")=="core" and a_["name"] in tb:
            own=[k for k in co if a_["name"].startswith(k+".")]
            if own:
                k=max(own,key=len); o=tb[a_["name"]]["xy"]
                a_["xy"]=[round(o[0]+co[k][0]-cb[k][0],4),round(o[1]+co[k][1]-cb[k][1],4)]; nct+=1
    eb=(b.get("clock") or {}).get("edge_clocks") or []
    for i,e in enumerate((t.get("clock") or {}).get("edge_clocks") or []):
        if isinstance(e,dict) and i<len(eb) and e.get("tap_um")!=eb[i].get("tap_um"):
            e["tap_um"]=list(eb[i]["tap_um"]); n+=1
            if not free(e["tap_um"]): bad+=1; print("NOT FREE",tn,"edge_clock",i,e["tap_um"])
json.dump(N,open(sys.argv[3],"w"),indent=1); print("restored",n,"not free",bad,"core taps set",nct)
