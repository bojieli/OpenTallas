#!/bin/bash
# PATH-KV-BIND 10-25: reproduce the b3 KV plan + bind recipe from the parent commit's die_plan.json (run at repo root).
# 1 dead/narrow cleanup (b7 evidence; the cfg daisy kept), 2 explicit N/S + hg_v1 position splits (+ plan cells),
# 3 narrow the split types' live widths (daisy per position),
# 4 recipe.  The head-eighth clock-pin merge (head_clk_merge.py) is applied separately to cores/ + the compose spec.
set -euo pipefail
D=physical/die_plan/qwen_kvsys; K=$D/bind/kvbind1025; T=$(mktemp -d)
P0=${1:-$D/die_plan.json}
python3 -I $K/live_width_cleanup.py $P0 $K/b7_bind_latency.json.gz $T/a.json $K/live_width_cleanup_report.json --keep o_kvs_hroot_Q_o_cN
python3 -I $K/explicit_split.py $T/a.json $T/b.json $K/explicit_split_report.json --plan-cells $D/bind/kv45/plan_cells_1309.json $K/plan_cells_b3.json
python3 -I $K/live_width_cleanup.py $T/b.json $K/b7_bind_latency.json.gz $D/die_plan.json $K/live_width_cleanup_report2.json
python3 -I $K/mk_recipe_b3.py $D/die_plan.json $D/bind/kvtok1025/recipe_b2.json $K/recipe_b3.json
rm -rf $T
