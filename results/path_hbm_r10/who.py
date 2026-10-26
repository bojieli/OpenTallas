import json,sys,collections
P=json.load(open(sys.argv[1]+"/die_plan.json")); tn=sys.argv[2]; X=float(sys.argv[3])
t=P["partition_types"][tn]; hc={h["inst"]:h for h in t["hard_cores"]}
def inst(lbl): return lbl.split(".")[0] if lbl else "?"
mod=lambda i: hc[i]["module"][:28] if i in hc else i[:20]
src=collections.defaultdict(list)
for s in t["internal_stations"]: src[(s.get("launch"),tuple(s["from_um"]))].append(s)
c=collections.Counter(); tot=0
for (l,f),ss in src.items():
  m=0; who=None
  for s in ss:
    if min(f[0],s["to_um"][0])<X<max(f[0],s["to_um"][0]) and s["bits"]>m: m=s["bits"]; who=s
  if who:
    tot+=m; c[(mod(inst(l)) if not str(l).startswith("face") else "FACE", mod(inst(who["capture"])), "ser" if who.get("serial_k") else "")]+=m
print(tn,"x",X,"bits",tot)
for k,v in c.most_common(18): print("  ",k,v)
