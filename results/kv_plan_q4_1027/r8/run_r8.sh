#!/usr/bin/env bash
# KV-PLAN-DELTA-2 task 3: R8 landing regen on PLAN (recipe pd/run_v39f.sh R8 block, no plan edit)
set -euo pipefail
PLAN=$1; O=$2
D=/srv/opentallas-scratch2/claude/kv-plan-q3-1027/pd; T=/srv/opentallas-scratch2/claude/wt/kv-plan-q3-1027/tools/die_plan
export PYTHONPATH=/srv/opentallas-scratch2/claude/kv-cores-pv3/pylib:$T
ulimit -v 48000000
mkdir -p $O/r8 $O/lat; cp $PLAN $O/die_plan.json
gzip -dc $D/r8/kv44_bus_groups.json.gz > $O/r8/bg_kv44.json
python3 $D/r8/r8_fault_exempt.py $O/r8/bg_kv44.json $O/r8/bg_fx.json
python3 $D/r8/r8_invariant_split.py $O/die_plan.json $O/r8/bg_fx.json $O/r8/bg_split.json
python3 $D/r8/r8_row_publish.py $O/die_plan.json $O/r8/bg_split.json $O/r8/bg_pub.json --family kv3_hg,kv3_hg_v1,kv3_hg_v3
python3 $D/r8/r8_rebase.py $O/die_plan.json $O/r8/bg_pub.json $D/r8/kv44_bind_latency.json.gz $O/r8/bus_groups.json
rm $O/r8/bg_kv44.json $O/r8/bg_fx.json $O/r8/bg_split.json $O/r8/bg_pub.json
python3 $T/gen.py latency $O/die_plan.json --out $O/lat --groups $O/r8/bus_groups.json --bus leaf --replica type --fold-r8
