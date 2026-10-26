#!/bin/bash
# TYPE-REDUCE-3/HBM: regenerate the OLD constant-variant kits (gold RTL for the per-variant LEC), same gen args as the
# strap master kits.  usage: gen_old.sh WT OUT MASTER   (variants from results/type_reduce3_1025/hbm/variants.json)
WT=$1; OUT=$2; M=$3
cd "$WT/physical/die_plan/hbm_arch_cores" || exit 9
mkdir -p "$OUT/old" "$OUT/logs"
python3 -c "import json;[print(v['old_view']) for v in json.load(open('$WT/results/type_reduce3_1025/hbm/variants.json'))['$M']]" |
  xargs -P 4 -I{} sh -c 'v={}; python3 -E -s gen_core_kit_hbm.py --views views_b2n.json --view "$v" --out '"$OUT"'/old --hold-margin 0 --face-shell on --face-shell-drop off --core-insertion none --clock-taps density > '"$OUT"'/logs/genold_${v%@*}.log 2>&1; echo "$v rc=$?"'
