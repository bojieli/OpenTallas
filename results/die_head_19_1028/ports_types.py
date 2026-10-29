import json,sys,collections
sta=json.load(open(sys.argv[1])); plan=json.load(open(sys.argv[2])); bind=json.load(open(sys.argv[3]))
pt={p["name"]:p["type"] for p in plan["partitions"]}
reg2types=collections.defaultdict(set)
for p,v in bind["parts"].items():
    if isinstance(v,dict) and v.get("region"): reg2types[v["region"]].add(pt.get(p,"?"))
multi={r:t for r,t in reg2types.items() if len(t)>1}
print("regions",len(reg2types),"multi-type regions",len(multi), list(multi.items())[:5])
out=[]
for C in ("TT","FF"):
    for r in sta["count_aligned"][C]["rows"]:
        b=bind["ports"][r["port"]]
        ts="/".join(sorted(reg2types[b["src"]])); td="/".join(sorted(reg2types[b["dst"]]))
        out.append(dict(C=C,port=r["port"],src=b["src"],dst=b["dst"],ts=ts,td=td,D=r["depth"],ml=r["margin_lo_ps"],mh=r["margin_hi_ps"],
                        Llo=r["L_lo_ps"],Lhi=r["L_hi_ps"],ring=r.get("ring"),tree=r["tree"],K=b.get("K"),sched=b.get("sched_lat")))
json.dump(out,open(sys.argv[4],"w"),indent=0)
c=collections.Counter((o["C"],o["ring"],o["ts"],o["td"]) for o in out if o["C"]=="TT")
for k,v in sorted(c.items(),key=lambda x:(x[0][1],-x[1])): print(v,k)
