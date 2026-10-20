#!/bin/bash
# KV-CTL3: pre-gate native census chain for one kit: synth gate (no CTS) -> tools/ref_tile/native_census.py on the gate's
# mapped netlist (loaded ASAP7 TT Liberty + ctl SRAM TT lib) -> only on census PASS: the --cts layout gate.
k=$1; W=/home/ubuntu/wt/kv-ctl3-1020; S=/home/ubuntu/scratch/kv-ctl3; K=physical/ref_tile/qkd_kvs_ctl_$k
cd $W || exit 2
echo "CHAIN $k start $(date +%T)"
timeout 7200 python3 tools/ref_tile/pre_route_gate.py $K --remote auto --mem 32 --json $S/syn_$k.json > $S/syn_$k.log 2>&1
echo "CHAIN $k synth gate rc $? $(grep -m1 -o 'PRE_ROUTE_GATE: [A-Z]*.*' $S/syn_$k.log)"
HD=$(grep -m1 -o 'host dir ot-[a-z0-9]*:[^ ;]*' $S/syn_$k.log | sed 's/host dir //')
H=${HD%%:*}; G=${HD#*:}
[ -n "$G" ] || { echo "CHAIN $k no remote dir"; exit 3; }
echo "CHAIN $k remote $H:$G"
timeout 120 rsync -t /home/ubuntu/scratch/kv-ctl3/census.sh $H:$G/census.sh; timeout 3600 /home/ubuntu/bin/ot-run --mem 16 --threads 2 --dir $G -- bash $G/census.sh $G > $S/census_$k.log 2>&1
crc=$?
echo "CHAIN $k census rc $crc: $(grep -m1 '^CENSUS' $S/census_$k.log)"
timeout 120 rsync -rt $H:$G/census/native_census.json $S/native_census_$k.json 2>/dev/null
if [ $crc -ne 0 ]; then echo "CHAIN $k STOP: census not PASS -> no layout gate"; exit 1; fi
timeout 30000 python3 tools/ref_tile/pre_route_gate.py $K --cts --remote auto --mem 32 --json $S/gate_$k.json > $S/gate_$k.log 2>&1
echo "CHAIN $k cts gate rc $? $(grep -m1 -o 'PRE_ROUTE_GATE: [A-Z]*.*' $S/gate_$k.log) $(date +%T)"
