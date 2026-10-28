import json,collections,os,sys
P=json.load(open(sys.argv[1])); repo=sys.argv[2]
ts=P["partition_types"]; ts = ts if isinstance(ts,dict) else {t["name"]:t for t in ts}
parts=collections.Counter(p["type"] for p in P["partitions"])
mods=collections.defaultdict(lambda: dict(inst=0,types=set(),viewed=0,outlines=set(),pins=set()))
for tn,t in ts.items():
    n=parts.get(tn,0)
    for c in t.get("hard_cores") or []:
        m=c.get("module") or c["inst"]; d=mods[m]
        d["inst"]+=n; d["types"].add(tn)
        ok = bool(c.get("lef") and c.get("lib") and os.path.isfile(os.path.join(repo,c["lef"])) and os.path.isfile(os.path.join(repo,c["lib"])))
        d["viewed"]+= n if ok else 0
        d["outlines"].add(tuple(c.get("outline_um") or c.get("size_um") or ())); d["pins"].add(c.get("pins_file"))
out=[]
for m,d in sorted(mods.items()):
    out.append(dict(module=m,inst=d["inst"],viewed_inst=d["viewed"],status="VIEWED" if d["viewed"]==d["inst"] else ("PARTIAL" if d["viewed"] else "NO-VIEW"),types=sorted(d["types"]),outlines=sorted(map(list,d["outlines"])),pins_files=sorted(x for x in d["pins"] if x)))
nv=[o for o in out if o["status"]!="VIEWED"]
print("modules",len(out),"inst",sum(o["inst"] for o in out),"noview modules",len(nv),"inst",sum(o["inst"]-o["viewed_inst"] for o in nv))
json.dump(out,open(sys.argv[3],"w"),indent=1)
