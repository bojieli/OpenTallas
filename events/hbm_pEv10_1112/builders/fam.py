import json,sys
for p in sys.argv[2:]:
    d=json.load(open(f"plans/{p}/die_plan.json")); P={x["id"]:x for x in d["ports"]}; parts=d["partitions"]; parts=parts if isinstance(parts,dict) else {x["name"]:x for x in parts}; T=d["partition_types"]
    for lid in sys.argv[1].split(","):
        L=next(x for x in d["lanes"] if x["id"]==lid); out=[]
        for q in L["ports"]:
            s=P[q]["src"]; part=s["part"]
            if part not in parts: out.append(part); continue
            t=T[parts[part]["type"]]; b=s["bus"]; slot=b[:-2]
            fs=[f for f in t.get("ft_slots",[]) if slot in (f.get("name"),f.get("id"))]
            n=fs[0].get("stations") if fs else "-"
            ist=[len(e["regs_um"]) for e in t.get("internal_stations",[]) if e.get("conn")=="bus:"+b]
            out.append(f"{part}:{slot}:{n}" + (f"/ist{ist}" if ist else ""))
        print(p,lid,d["latency"]["lanes"][lid]["stations"]," ".join(out))
