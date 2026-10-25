"""SCRATCH preview plan (NOT the adopted plan): main adopt178 + the two pending plan deltas the strict bind needs
(1) COORD gather ruling B: 11 attnh fold lanes full width 2133 b, beats 1 (S81-PLAN/FTCHAN owns the real delta)
(2) empty partition s_5N_x06 (type slice_station__t19: 0 buses/0 ft/0 contents) dropped (PORTFIX decision 5; S81-PORTS)
The 9 fault feeders (S81-PORTS faultfeed delta) are NOT previewed: they stay UNPLANNED (undriven) in this bind."""
import json,sys
f=sys.argv[1]; p=json.load(open(f))
ports={e["id"]:e for e in p["ports"]}
n=0
for L in p["lanes"]:
    if L["id"].startswith("attnh__"):
        for pid in L["ports"]: ports[pid]["width"]=2133
        L["beats"]=1; L.pop("word_bits",None)
        lat=p["latency"]["lanes"][L["id"]]; lat["beats"]=1; lat["word_cycles"]=lat["cycles"]
        n+=1
for tn,t in p["partition_types"].items():
    for b in t.get("buses",[]):
        if b["name"] in ("attnh_i0","attnh_o0"): b["width"]=2133
p["partitions"]=[x for x in p["partitions"] if x["name"]!="s_5N_x06"]
p["partition_types"].pop("slice_station__t19",None)
p["census"]=[c for c in p["census"] if "s_5N_x06" not in json.dumps(c)]
p["note"]="SCRATCH PREVIEW (TOK-DS/BIND 10-25): main adopt178 + attnh 2133 b (ruling B) + s_5N_x06 dropped. NOT an adopted plan."
json.dump(p,open(f,"w"),indent=1); print("attnh lanes",n,"parts",len(p["partitions"]),"types",len(p["partition_types"]))
