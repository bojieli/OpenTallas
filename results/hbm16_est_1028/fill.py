import json,sys
d=json.load(open(sys.argv[1]))
T=d["partition_types"]
for n,t in sorted(T.items()):
  w,h=t["outline_um"]; A=w*h
  hc=t.get("hard_cores") or []
  ha=sum(c["outline_um"][0]*c["outline_um"][1] for c in hc)
  cells=t.get("cells",0)
  soft=sum((c.get("cells") or 0) for c in (t.get("contents") or []))
  ist=t.get("internal_stations") or []
  print("%-12s %6.2f mm2 hard %3d fill %.2f cells %s soft %s ist %d" % (n,A/1e6,len(hc),ha/A,cells,soft,len(ist)))
