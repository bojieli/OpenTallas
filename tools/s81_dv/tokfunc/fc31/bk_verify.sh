#!/usr/bin/env bash
# TOK-DS 10-24: BK drain sink canonical verification (COORD ruling 18:55).
#   usage: bk_verify.sh <tree> <out> canon|legacy|cross
#   canon : tree = sink RTL (dsdv_bk_g BK_DRAIN_SINK default 1), canonical expectations; m0 must PASS, m1..4 must FAIL;
#           lower_bk layer bench L2/L14/L20 topk_local+topk_final PASS, corrupt/early mutants FAIL.
#   legacy: tree = main 9721734fee RTL (default 0) + new benches, +define+OT_DSDV_BK_LEGACY_FWD / OT_BK_LEGACY_FWD=1:
#           the old record must reproduce (same PASS/FAIL pattern).
#   cross : negative controls: canonical expectations on legacy RTL and legacy expectations on sink RTL must FAIL (m0 sel/col + L2 layer).
set -u
T=$(realpath $1); OUT=$2; MODE=$3; FX=/srv/opentallas-scratch/claude/stw-s81d-tok/layers/fix
mkdir -p $OUT; OUT=$(realpath $OUT); cd $T
export PATH=$HOME/.local/opentallas-tools/bin:$PATH JOBS=6 J=12
DEF=""; LEG=0
[ $MODE = legacy ] && { DEF=+define+OT_DSDV_BK_LEGACY_FWD; LEG=1; }
[ "${XEXP:-}" = legacy ] && { DEF=+define+OT_DSDV_BK_LEGACY_FWD; LEG=1; }
MUTS=${MUTS:-"0 1 2 3 4"}
for u in sel col; do for m in $MUTS; do
  ( BK_DEFS=$DEF bash rtl/dsrom_sys/s81_dv/unit/bk/test/run_bk_bench.sh $u $OUT/unit $m > $OUT/unit_${u}_m$m.txt 2>&1; echo "exit $?" >> $OUT/unit_${u}_m$m.txt ) &
done; done
# layer-job bench (lower_bk gen -> tb_bk_layer on dsdv_bk_sel exactly as die.v u_bk_sel)
LAY=${LAYS:-"L2 L14 L20"}; dirs=""; mkdir -p $OUT/layer
for L in $LAY; do for j in topk_local topk_final; do
  OT_BK_LEGACY_FWD=$LEG python3 tools/s81_dv/layer_prog/lower_bk.py gen --fixtures $FX/$L --job $j --out $OUT/layer/${L}_$j > $OUT/layer/gen_${L}_$j.json 2>&1
  dirs="$dirs $OUT/layer/${L}_$j"
done; done
if [ $MODE != cross ]; then for j in topk_local topk_final; do for mu in corrupt early; do
  OT_BK_LEGACY_FWD=$LEG python3 tools/s81_dv/layer_prog/lower_bk.py gen --fixtures $FX/L2 --job $j --mutant $mu --out $OUT/layer/m_${mu}_L2_$j > $OUT/layer/gen_m_${mu}_L2_$j.json 2>&1
  mdirs="${mdirs:-} $OUT/layer/m_${mu}_L2_$j"
done; done; fi
( OT_BK_LEGACY_FWD=$LEG bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh $OUT/layer/build $dirs > $OUT/layer_gold.txt 2>&1; echo "exit $?" >> $OUT/layer_gold.txt
  [ -n "${mdirs:-}" ] && for d in $mdirs; do OT_BK_LEGACY_FWD=$LEG bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh $OUT/layer/build $d > $d.txt 2>&1; echo "exit $?" >> $d.txt; done ) &
wait
echo BK_VERIFY_DONE $MODE
