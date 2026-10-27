#!/usr/bin/env bash
# TOK-QK-6: R8 landing on hm_r26q2 vs hm_r26q3 with the same kv44 bind bus groups (plan's own R8 chain).
set -euo pipefail
W=${W:-/srv/opentallas-scratch2/claude/wt/kv-plan-q3-1027}; T=$W/tools/die_plan
R8=/srv/opentallas-scratch2/claude/kv-plan-q3-1027/pd/r8
O=/srv/opentallas-scratch2/claude/tok-qk-6-1027; mkdir -p $O
export PYTHONPATH=$T
declare -A PL=([q2]=/srv/opentallas-scratch2/claude/kv-kits-6-1027/pd/hm_r26q2.json [q3]=/srv/opentallas-scratch2/claude/kv-plan-q3-1027/pd/hm_r26q3.json)
gzip -dc $R8/kv44_bus_groups.json.gz > $O/bg_kv44.json
gzip -dc $R8/kv44_bind_latency.json.gz > $O/bl_kv44.json
python3 $R8/r8_fault_exempt.py $O/bg_kv44.json $O/bg_fx.json
for k in q2 q3; do
  P=${PL[$k]}; sha256sum $P > $O/$k.plan.sha256
  python3 $R8/r8_invariant_split.py $P $O/bg_fx.json $O/bg_split_$k.json
  python3 $T/gen.py latency $P --out $O/lat_$k --groups $O/bg_split_$k.json --rebase-bind $O/bl_kv44.json --bus leaf --replica type --fold-r8 > $O/lat_$k.log 2>&1
  tail -2 $O/lat_$k.log
done
