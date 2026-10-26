import json,sys,collections
d=sys.argv[1]; spec=json.load(open(sys.argv[2]))
holes={(round(i["die_hole_um"][0],2),round(i["die_hole_um"][1],2)):i for i in spec["instances"]}
C=json.load(open(d+"/place.json"))
cnt=collections.Counter(); kinds=collections.Counter(); out=collections.Counter(); rl=collections.defaultdict(float)
W={"BUFx24_ASAP7_75t_R":1.62}
for n,c in C.items():
    k=(round((c["x"]+0.81)//8.64*8.64,2), round((c["y"]+0.135)//8.64*8.64,2))
    if k in holes: cnt[k]+=1; kinds[c["kind"]]+=1; rl[k]+=1.62
    else: out[c["kind"]]+=1
print(json.dumps(dict(cells_in_holes=sum(cnt.values()), holes_used=len(cnt), holes=len(holes), max_cells_per_hole=max(cnt.values()),
  max_bufx24_row_um_per_hole=round(max(rl.values()),2), hole_rows=32, hole_row_um=8.64, demand_budget_row_um=spec["demand_row_len_um"],
  hist=sorted(collections.Counter(cnt.values()).items()), kinds_in_holes=kinds, die_clock_cells_outside_holes=out)))
