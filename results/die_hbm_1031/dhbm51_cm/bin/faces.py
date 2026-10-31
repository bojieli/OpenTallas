import sys,json,collections
from pathlib import Path
for kd in sys.argv[1:]:
    kd=Path(kd); ps=json.load(open(kd/"pins.json"))
    d=collections.defaultdict(list)
    for p in ps: d[p["face"]].append(p["y"] if p["face"] in "EW" else p["x"])
    print(kd.name, {f:(len(v),round(min(v),1),round(max(v),1)) for f,v in sorted(d.items())})
