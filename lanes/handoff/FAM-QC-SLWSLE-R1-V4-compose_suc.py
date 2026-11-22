#!/usr/bin/env python3
"""FAM-QC-SLWSLE-R1 V4 su_c compose: merge the su_delta CAP-2 rows (V2-based) onto a V3 plan.
usage: compose_suc.py V3_PLAN CAP_PLAN V2_BASE_PLAN OUT
Per type: internal_stations rows whose content changed CAP vs V2 base replace the V3 rows (same conn); relay_sites of those buses replaced; lanes sourced on a bus whose station count changed get fixed_cycles +d."""
import json,sys
v3p,cap_p,base_p,outp=sys.argv[1:5]
V3=json.load(open(v3p)); C=json.load(open(cap_p)); B=json.load(open(base_p))
TYPES=["sle_su_c","slw_su_c__cl92142dac","slw_su_c__cl19bb38ef"]
rep={}; DELTA={}
for tn in TYPES:
    t3=V3["partition_types"][tn]; tc=C["partition_types"][tn]; tb=B["partition_types"][tn]
    ic={e["conn"]:e for e in tc["internal_stations"]}; i3={e["conn"]:e for e in t3["internal_stations"]}; ib={e["conn"]:e for e in tb["internal_stations"]}
    changed=[c for c in ic if c in i3 and json.dumps(ic[c],sort_keys=True)!=json.dumps(ib.get(c),sort_keys=True)]
    rs3=t3.setdefault("relay_sites",{}); rsc=tc.get("relay_sites",{})
    for c in changed:
        n3=len(i3[c]["regs_um"]); i3[c].clear(); i3[c].update(ic[c]); d=len(i3[c]["regs_um"])-n3
        if c.startswith("bus:"):
            pre="u_ist_%s_"%c[4:]
            for k in [k for k in rs3 if k.startswith(pre)]: del rs3[k]
            for k,v in rsc.items():
                if k.startswith(pre): rs3[k]=v
            if d: DELTA[(tn,c[4:])]=d
    rep[tn]={"changed":changed,"d":{b:d for (t,b),d in DELTA.items() if t==tn}}
ptype={x["name"]:x["type"] for x in V3["partitions"]}
ports=V3["ports"] if isinstance(V3["ports"],dict) else {x["id"]:x for x in V3["ports"]}
lanes=[]
for l in V3["lanes"]:
    a=ports[l["ports"][0]].get("src") or {}
    d=DELTA.get((ptype.get(a.get("part")),a.get("bus")),0)
    if d:
        l["fixed_cycles"]=int(l.get("fixed_cycles",0))+d; r=V3["latency"]["lanes"][l["id"]]
        for k in ("fixed","cycles","natural"): r[k]=int(r[k])+d
        lanes.append([l["id"],d])
rep["lanes_raised"]=lanes
json.dump(V3,open(outp,"w"),separators=(",",":"))
print(json.dumps(rep)[:3000])
