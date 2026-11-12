#!/bin/bash
# VL2QC-SC: route_supply (edge_outline, s25 tools) + gates for plan $1 in planq25 (own gt dir sc/gt)
cd /srv/opentallas-scratch2/claude/vislayout2-qc
P=$1
( cd src25 && nice -n 19 python3 -I -B tools/die_plan/route_supply.py ../planq25/$P.json --die qwen_compute --repo . --match "_sc_" --grt-halving edge_outline --out ../sc/rs/$P > ../sc/rs/$P.log 2>&1 ) &
sed "s#\$W/gt/#\$W/sc/gt/#g" gates.sh > sc/gates_sc.sh
S=$PWD/src25 PQ=planq25 bash sc/gates_sc.sh $P > sc/gt/gates_$P.log 2>&1
wait
echo SCOREDONE $P
