import json,collections,sys
p=json.load(open(sys.argv[1]))
c=collections.Counter(x["type"] for x in p["partitions"])
for k,v in p["partition_types"].items():
  hc=v.get("hard_cores",[])
  nl=sum(1 for h in hc if h.get("lef"))
  print(f'{k:12s} n{c[k]} cells {v.get("cells")} hc {len(hc)} lef {nl} {v["outline_um"]}', sorted(set(h["module"] for h in hc if h.get("lef")))[:5])
h=[h for v in p["partition_types"].values() for h in v.get("hard_cores",[]) if h.get("lef")][0]; print(h["lef"],h["lib"])
