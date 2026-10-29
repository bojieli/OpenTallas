#!/bin/bash
# DIE-KV-19 (= DIE-KV-15 r8_15.sh, plan/worktree changed) R8 regen on the first strict bind of the fishbone event (= DIE-KV-13 r8_13.sh) (DIE-KV-8 recipe: invariant split, pads --replica type
# --bus leaf, ECTL kreq/krsp exempt, check --strap-pads) + the KV write-group rule (r8_write_groups.py prep/check, COORD
# TOK-ALL-13r).  usage: r8_13.sh BIND_DIR OUT_DIR [PLAN]
set -u
cd /srv/opentallas-scratch2/claude/wt/die-kv-16
P=${3:-results/die_kv_19_1028/event/plan.json}; B=$1; O=$2; mkdir -p $O; K=physical/die_plan/qwen_kvsys/r8
python3 $K/r8_invariant_split.py $P $B/bus_groups.json $O/bg_split.json || exit 3
python3 $K/r8_write_groups.py prep $O/bg_split.json $O/bus_groups.json || exit 3
python3 tools/die_plan/r8.py pads $P $O/bus_groups.json --replica type --bus leaf --exempt '^kreq$' --exempt '^krsp$' --out $O > $O/pads.log 2>&1; echo PADS_RC $?
python3 tools/die_plan/r8.py check $P $O/bus_groups.json --replica type --bus leaf --exempt '^kreq$' --exempt '^krsp$' --landing $O/qwen_kvsys_r8_landing.json --strap-pads --json $O/check_strap.json > $O/check.log 2>&1; echo CHECK_RC $?
python3 $K/r8_write_groups.py check $O/qwen_kvsys_r8_landing.json > $O/write_groups.log 2>&1; echo WG_RC $?
python3 $K/r8_write_groups.py bindview $O/qwen_kvsys_r8_landing.json $O/qwen_kvsys_r8_landing_bind.json > $O/bindview.log 2>&1; echo BV_RC $?
tail -n 5 $O/pads.log $O/check.log $O/write_groups.log
