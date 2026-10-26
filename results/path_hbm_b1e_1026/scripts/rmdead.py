"""b1e step 2: remove the 78 dead (unbound, 0 refs both ends) NW/NE lanes: lanes, their ports, type buses, ft_slots, latency rows."""
import json,sys,re,collections,hashlib
src,unb,dst,rep=sys.argv[1:5]
p=json.load(open(src)); dead=set(json.load(open(unb)))
rx=re.compile(r"^(" + "|".join(sorted(map(re.escape,dead),key=len,reverse=True)) + r")(?:_[io]|x\d+)$")
lanes={l["id"]:l for l in p["lanes"]}
dpid={x for d in dead for x in lanes[d]["ports"]}
dbus=collections.defaultdict(set)
ptype={x["name"]:x["type"] for x in p["partitions"]}
for q in p["ports"]:
    if q["id"] in dpid:
        for e in ("src","dst"): dbus[ptype[q[e]["part"]]].add(q[e]["bus"])
livebus=collections.defaultdict(set)
for q in p["ports"]:
    if q["id"] not in dpid:
        for e in ("src","dst"): livebus[ptype[q[e]["part"]]].add(q[e]["bus"])
clash={t:sorted(dbus[t]&livebus[t]) for t in dbus if dbus[t]&livebus[t]}
assert not clash, clash
n=collections.Counter(); bits=0
for q in p["ports"]:
    if q["id"] in dpid: bits+=q["width"]
p["lanes"]=[l for l in p["lanes"] if l["id"] not in dead]; n["lanes"]=len(dead)
before=len(p["ports"]); p["ports"]=[q for q in p["ports"] if q["id"] not in dpid]; n["ports"]=before-len(p["ports"])
for tn,t in p["partition_types"].items():
    b=len(t.get("buses",[])); t["buses"]=[x for x in t.get("buses",[]) if x["name"] not in dbus.get(tn,())]; n["buses"]+=b-len(t["buses"])
    # every remaining bus named like a dead lane must have been removed
    assert not [x["name"] for x in t["buses"] if rx.match(x["name"])], tn
    if "ft_slots" in t:
        f=len(t["ft_slots"]); t["ft_slots"]=[x for x in t["ft_slots"] if not rx.match(x["name"])]; n["ft_slots"]+=f-len(t["ft_slots"])
for d in dead:
    if d in p["latency"]["lanes"]: del p["latency"]["lanes"][d]; n["latency"]+=1
p["note"]=p["note"]+" | b1e (PATH-HBM-B1E 10-26): 78 dead NW/NE lanes removed (unbound, 0 core/soft/station refs both ends; lanes+ports+type buses+ft_slots+latency rows)"
s=json.dumps(p,indent=1); open(dst,"w").write(s)
out=dict(removed=dict(n), bits=bits, lanes=sorted(dead), type_buses={t:sorted(v) for t,v in dbus.items()},
         src_sha256=hashlib.sha256(open(src,"rb").read()).hexdigest(), dst_sha256=hashlib.sha256(s.encode()).hexdigest(),
         kept_text_refs="root clock: 'L150 corridor' site label (geometry text only, corridor space unchanged)")
json.dump(out,open(rep,"w"),indent=1); print(json.dumps({k:out[k] for k in ("removed","bits","dst_sha256")}))
