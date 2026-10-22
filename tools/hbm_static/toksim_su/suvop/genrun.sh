#!/usr/bin/env bash
# usage: genrun.sh TAG rec1 rec2 ...   (in bundle dir) -> vec_TAG/<rec>/ + one summary line each
cd "$(dirname "$0")"; tag=$1; shift
for r in "$@"; do
 ( d=vec_$tag/$r; rm -rf $d; mkdir -p $d
   python3 tools/hbm_static/toksim_su/suvop/prod_compile.py $d $r --rr 12 --wr 10 ${XARGS:-} > $d/compile.txt 2>&1 || { echo "== $r COMPILE_FAIL $(tail -2 $d/compile.txt|tr '\n' ' ')"; exit; }
   bash run_toksim_su.sh run mr10 $d > /dev/null 2>&1
   echo "== $r $(grep -E 'SU_TOP (PASS|FAIL)' $d/sim_mr10.log | head -1 | cut -c1-120) | $(grep -m3 'SU_TOP ERROR' $d/sim_mr10.log | cut -c1-140 | tr '\n' ';') | ser=$(python3 -c "import json;print(json.load(open('$d/programme.json'))['cycles_serial'])" 2>/dev/null)" ) &
 while [ $(jobs -r | wc -l) -ge ${PAR:-6} ]; do sleep 1; done
done; wait
