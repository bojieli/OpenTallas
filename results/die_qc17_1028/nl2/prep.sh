#!/bin/bash
# DIE-QC-17 nl2: re-cluster nl glue (<=110 um box, <=400 regs) -> cluster CTS -> TT/FF arrivals -> clins -> a0k5 pin db
set -u; N=/srv/opentallas-scratch2/claude/die-qc17-1028/nl2; P=/srv/opentallas-scratch2/claude/qc-a0-kits-3-1028/parent/nl; cd $N
python3 -I clusters.py sinks_nl.txt cl_nl.json 110 400 > clusters.log || exit 1
python3 - <<"PY"
import json
G=json.load(open("cl_nl.json")); o={}
for l in open("sinks_nl.txt"):
    p=l.split()
    if p[0]=="MACRO": o[p[1]]=p[7]
for k in G["kids"]: k["orient"]=o[k["inst"]]
json.dump(G,open("cl_nl.json","w"))
print("kids",len(G["kids"]),"clusters",len(G["clusters"]),"max n",max(c["n"] for c in G["clusters"]))
PY
python3 -I mkcltcl.py cl_nl.json cl_nl.tcl
docker run --rm --name qc17-nl2-cts --cpus=4 --memory=12g -v $P:/p:ro -v $N:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=TT ODB=/p/run/results/asap7/a0_nl_1ck/base/3_place.odb CLTCL=/w/cl_nl.tcl OUT=/w/cl_nl.odb openroad -exit /w/cts_cl.tcl" > cts_cl_nl.log 2>&1; echo "cts rc $?"
for C in TT FF; do docker run --rm --name qc17-nl2-meas-$C --cpus=2 --memory=8g -v $P:/p:ro -v $N:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=$C ODB=/w/cl_nl.odb OUT=/w/arr_cl_nl_$C.txt openroad -exit /w/meas.tcl" > meas_cl_nl_$C.log 2>&1 & done; wait
python3 -I clins.py > clins.log
docker run --rm --cpus=2 --memory=8g -v $P:/p:ro -v $N:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/wdef.tcl && openroad -exit /w/relef.tcl" > relef.log 2>&1; echo "relef rc $?"
echo "prep done $(date)"
