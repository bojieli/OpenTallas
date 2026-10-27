import json,collections,re
F={"B5":"path-s81-ftA/die_B5i50/src/physical/die_plan/s81/die_plan.json","g0fix":"path-s81-taps-1026/src/physical/die_plan/s81/die_plan_phyfit_g0fix.json","pd2cand":"codex-s81-pd2-2000/b2_candidate/die_plan_pd2_b2_candidate.json"}
for k,f in F.items():
    P=json.load(open(f)); T=P["partition_types"]; c=collections.Counter()
    for p in P["partitions"]:
        for s in T[p["type"]].get("ft_slots",[]) or []:
            fam=re.sub(r"\d+","#",p["name"].split("_")[0]); c[fam+"<-"+re.sub(r"[\d_]+$","",s.get("chain",s.get("name","?")))[:18]]+=s.get("width",1)
    print(k,"ft bits total",sum(c.values()),c.most_common(8))
