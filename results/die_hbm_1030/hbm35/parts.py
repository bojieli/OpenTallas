import json,sys
p=json.load(open(sys.argv[1]))
T=p["partition_types"]
d=p["die"]; print({k:v for k,v in d.items() if not isinstance(v,(list,dict))} if isinstance(d,dict) else d)
for n,x in sorted(((x["name"],x) for x in p["partitions"]), key=lambda kv:(kv[1]["origin_um"][1],kv[1]["origin_um"][0])):
    if n.startswith("NW_"): continue
    w,h=T[x["type"]]["outline_um"]; o=x["origin_um"]
    if "90" in x["orient"] or "270" in x["orient"]: w,h=h,w
    t=x["type"]
    print(f"{n:10s} {t:24s} {x['orient']:4s} x {o[0]:9.2f}-{o[0]+w:9.2f} y {o[1]:9.2f}-{o[1]+h:9.2f} cells {T[t].get('cells')}")
