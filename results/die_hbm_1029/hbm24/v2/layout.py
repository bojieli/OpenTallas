import json,sys
P=json.load(open(sys.argv[1]+"/die_plan.json"))
print("die",P["die"]["outline_um"])
T=P["partition_types"]
for p in sorted(P["partitions"],key=lambda p:(-p["origin_um"][1],p["origin_um"][0])):
    t=T[p["type"]]; print(f'{p["name"]:10s} {p["type"]:22s} o=({p["origin_um"][0]:.0f},{p["origin_um"][1]:.0f}) sz=({t["outline_um"][0]:.0f},{t["outline_um"][1]:.0f}) hc={len(t.get("hard_cores",[]))}')
r=json.load(open(sys.argv[2]))
far=r["phase2"]["far"]
for f in far: print("FAR",f["src"],f["dst"],f["bits"],f["gap_um"])
for f in r["phase2"]["failed"]: print("FAILED",f["id"],f["src"],f["dst"],f["bits"],f["why"][:80])
