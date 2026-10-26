import json,sys,re,collections
plan,cc,unb=sys.argv[1:4]
p=json.load(open(plan)); dead=set(json.load(open(unb)))
lanes={l["id"]:l for l in p["lanes"]}
ports={q["id"]:q for q in p["ports"]}
print("lanes",len(lanes),"ports",len(ports),"dead",len(dead),"dead in plan",len(dead&set(lanes)))
dports=[ports[x] for d in dead if d in lanes for x in lanes[d]["ports"]]
print("dead ports",len(dports), "bits",sum(q["width"] for q in dports))
# bus names used by dead ports per (part,bus)
busref=collections.Counter()
for q in dports:
    for e in ("src","dst"): busref[(q[e]["part"],q[e]["bus"])]+=1
# are those buses shared with live ports?
live=collections.Counter()
for q in p["ports"]:
    l=None
for l in p["lanes"]:
    if l["id"] in dead: continue
    for x in l["ports"]:
        q=ports[x]
        for e in ("src","dst"):
            if (q[e]["part"],q[e]["bus"]) in busref: live[(q[e]["part"],q[e]["bus"])]+=1
print("dead buses also used by live lanes:",len(live), list(live)[:5])
# references in types (anything except buses/ft_slots) and core_conns
ptype={x["name"]:x["type"] for x in p["partitions"]}
dbus={b for (_,b) in busref}
txt_hits=collections.Counter()
for tn,t in p["partition_types"].items():
    for k,v in t.items():
        if k in ("buses",): continue
        s=json.dumps(v)
        for b in dbus:
            if re.search(r'\b'+re.escape(b)+r'\b',s): txt_hits[(tn,k,b)]+=1
print("type-content refs to dead bus names:",len(txt_hits), list(txt_hits)[:12])
c=open(cc).read()
ch=[b for b in dbus if re.search(r'\b'+re.escape(b)+r'\b',c)]
print("core_conns refs:",len(ch),ch[:10])
# latency lanes refs
lat=json.dumps(p.get("latency"))
print("latency refs:",sum(1 for d in dead if re.search(r'"'+re.escape(d)+r'"',lat)))
