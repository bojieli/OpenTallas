#!/bin/bash
set -u
Q=/srv/opentallas-scratch3/claude/type-safe-3b/qc
cd $Q/src
R=physical/die_plan/qwen_compute/qc_start_1106/runtime
mkdir -p $Q/r8
prlimit --as=48000000000 python3 -I -B tools/die_plan/r8.py pads ../plan/plan_qc53v4n_ts3.json ../bind_new/bus_groups.json --out $Q/r8 --landing $Q/r8/r8_ts3.json > $Q/r8/pads.log 2>&1; echo PADS rc=$?
tail -n 5 $Q/r8/pads.log | cut -c1-400
ls -la $Q/r8 | cut -c30-
python3 -I - <<P
import json
from collections import Counter
o=json.load(open("$R/r8_reach.json"));n=json.load(open("$Q/r8/r8_ts3.json"))
print(list(o.keys())[:12])
om={m["id"]:m for m in o["members"]};nm={m["id"]:m for m in n["members"]}
print(len(om),len(nm),"only_old",len(set(om)-set(nm)),"only_new",len(set(nm)-set(om)))
keys=[k for k in next(iter(nm.values())) if k not in("id",)]
print(keys)
ch=[(i,om[i],nm[i]) for i in om if i in nm and om[i]!=nm[i]]
print("changed",len(ch))
c=Counter()
for i,a,b in ch:
    for k in keys:
        if a.get(k)!=b.get(k) and not isinstance(a.get(k),(list,dict)): c[(k,(b.get(k) or 0)-(a.get(k) or 0) if isinstance(b.get(k),(int,float)) else 'x')]+=1
print(c.most_common(20))
for i,a,b in ch[:3]: print(i,{k:(a.get(k),b.get(k)) for k in keys if a.get(k)!=b.get(k) and not isinstance(a.get(k),(list,dict))})
P
