import json,collections,sys
K=int(sys.argv[1]); mode=sys.argv[2]
bg=json.load(open("bind_v7/bus_groups.json"))
ep=set(m["lane"] for g in bg["landing"] for m in g["members"])
X=json.load(open("qc_cross.json"))["rows"]
pp=collections.Counter(r["lane"] for r in X if r["lane"] in ep)
v4=json.load(open("/srv/opentallas-scratch2/claude/codex-qc-land-price-1026/slice_vertical_4_requirements.json"))
if mode=="all": add={l:K*n for l,n in pp.items()}
elif mode=="v4keep":  # 65 v4 lanes keep +3 per crossing as priced; every other crossing +K
  add={l:(3 if l in v4["lane_added_cycles"] else K)*n for l,n in pp.items()}
json.dump(dict(case=f"fallback_{mode}_k{K}",scope="FALLBACK-LAND every plan partition-boundary port landed, K per port",source_table_sha256="fallback-land-1026 qc_cross.json (plan 54a1aeb5 ports on v7 bind lanes)",crossings=sum(pp.values()),ports=sum(pp.values()),lane_added_cycles=add),open(f"req_{mode}_k{K}.json","w"))
print(mode,K,len(add),sum(pp.values()),sum(add.values()))
