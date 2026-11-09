#!/bin/bash
# DIE-QC-95: pass 2 of the VM write landing event: re-derive R8 from pass-1 bus_groups, strict bind.
set -u
D=/srv/opentallas-scratch2/claude/dq95/vmwland; S=$D/src; P=$D/plan/plan_qc53v4w_mem9_vml.json
R=physical/die_plan/qwen_compute/qc_start_1106/runtime
cd $S; mkdir -p $D/r8 $D/bind_out2; date
prlimit --as=48000000000 python3 -I -B tools/die_plan/r8.py pads $P $D/bind_out/bus_groups.json --out $D/r8 > $D/r8/pads.log 2>&1; echo "PADS rc=$?"
tail -n 4 $D/r8/pads.log | cut -c1-300
test -e $R/r8_vml.json && { echo "r8_vml exists"; exit 9; }
cp $D/r8/qwen_compute_r8_landing.json $R/r8_vml.json
python3 -I - <<PY
import json
from collections import Counter
o=json.load(open("$R/r8_reach.json"));n=json.load(open("$R/r8_vml.json"))
om={m["id"]:m for m in o["members"]};nm={m["id"]:m for m in n["members"]}
print("members",len(om),len(nm),"only_old",len(set(om)-set(nm)),"only_new",len(set(nm)-set(om)))
c=Counter();ex={}
for i,b in nm.items():
    a=om.get(i)
    if not a: continue
    k=(b["bound"]-a["bound"],b["pad"]-a["pad"],b["landed"]-a["landed"])
    if k!=(0,0,0):
        c[k]+=1; p=i.split("<-")[1].split(".")[3] if "<-" in i and i.count(".")>3 else "?"; ex.setdefault(k,i)
print("(dbound,dpad,dlanded)",c.most_common()); print({str(k):v[:150] for k,v in ex.items()})
d=json.load(open("$R/asbuilt_reach.json")); d["land_r8"]="$R/r8_vml.json"; d["land_r8_note"]=d.get("land_r8_note","")+" | DIE-QC-95 11-08: r8_vml.json = r8.py pads on the VM write landing event bus_groups"
json.dump(d,open("$R/asbuilt_vml.json","w"),indent=1)
PY
date
python3 -B tools/die_plan/bind.py elab $P --out $D/bind_out2 --asbuilt $S/$R/asbuilt_vml.json > $D/elab2.log 2>&1; echo "ELAB2 rc $?" >> $D/elab2.log; tail -1 $D/elab2.log
python3 -B tools/die_plan/bind.py bind $P --out $D/bind_out2 --strict --asbuilt $S/$R/asbuilt_vml.json > $D/bind2.log 2>&1; echo "BIND2 rc $?" >> $D/bind2.log; tail -3 $D/bind2.log | cut -c1-300; date
echo BIND2-DONE
