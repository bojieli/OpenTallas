import json,statistics as st,collections
T=json.load(open("/srv/opentallas-scratch2/claude/die-qc8-1028/trial6/clock/tree.json"))
m=T["meta"];print({k:v for k,v in m.items() if k not in("site_legal","link_feed")})
sl=m.get("site_legal",{});print({k:(v if k!="balance" else {kk:vv for kk,vv in v.items() if kk!="region_dme"}) for k,v in sl.items() if k!="illegal"}, "illegal",len(sl.get("illegal",{})))
rd=sl.get("balance",{}).get("region_dme") or m.get("region_dme") or {}
print("dme regions",len(rd))
ers=[r for v in rd.values() for r in v.get("early_taps",[])]
print("early taps",len(ers))
by=collections.defaultdict(list)
for r in ers: by[round(r["early_model_ps"],1)].append(r["miss_ps"])
for k,v in sorted(by.items()): print(" early",k,"n",len(v),"miss med/min/max",round(st.median(v),1),min(v),max(v))
sp=[v["spread"] for k,v in rd.items() if v.get("spread") is not None]
print("dme model spread ps med/max",st.median(sp),max(sp))
print("taps",len(T["taps"]),"cells",len(T["sites"]))
