#!/bin/bash
# DIE-KV-13 R8 regen on the first strict bind of the inverter event (DIE-KV-8 recipe: invariant split, pads --replica type
# --bus leaf, ECTL kreq/krsp exempt, check --strap-pads).  usage: r8_13.sh BIND_DIR OUT_DIR
set -u
cd /srv/opentallas-scratch2/claude/wt/die-kv-6
P=results/die_kv_13_1028/event/plan.json; B=$1; O=$2; mkdir -p $O
python3 physical/die_plan/qwen_kvsys/r8/r8_invariant_split.py $P $B/bus_groups.json $O/bus_groups.json || exit 3
python3 tools/die_plan/r8.py pads $P $O/bus_groups.json --replica type --bus leaf --exempt '^kreq$' --exempt '^krsp$' --out $O > $O/pads.log 2>&1; echo PADS_RC $?
python3 tools/die_plan/r8.py check $P $O/bus_groups.json --replica type --bus leaf --exempt '^kreq$' --exempt '^krsp$' --landing $O/qwen_kvsys_r8_landing.json --strap-pads --json $O/check_strap.json > $O/check.log 2>&1; echo CHECK_RC $?
tail -5 $O/pads.log $O/check.log
