#!/usr/bin/env bash
# VEH-FMT-SM2 (10-19): fleet driver of the SM.MATVEC unit pre-check (sm_mv_unit.py) on the d4g die SM master.
#   run_sm_mv_unit.sh REV SMWROOT BUNDLE OUTROOT "smoke" | "L00 L02 head" [extra args for the positive runs]
# fixtures = the committed results/rtl/hbm_ds_layer_tput_1018/fixtures of REV (archived with the tools).
# smoke: L00 k4 (wq_a) die-0 SM-0 block positive + the two mutant witnesses (wbit: arithmetic, nopkt: schedule).
# Archives REV's tools + bench into OUTROOT/src on ot-epyc5 (the host holding SMWROOT and BUNDLE), builds once
# (work/obj_mv, -GMAXC=262144) and runs, per layer: positive (every captured rank-0 SM.MATVEC record, ops sm0 + all rows;
# must PASS).
set -uo pipefail
REV=$1; SMW=$2; BUNDLE=$3; OUT=$4; LAYERS=${5:-smoke}; HOST=${HOST:-ot-epyc5}; FIX=$OUT/src/results/rtl/hbm_ds_layer_tput_1018/fixtures
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
SHA=$(git -C "$WT" rev-parse "$REV")
ssh "$HOST" "mkdir -p $OUT/src $OUT/out $OUT/work && rm -rf $OUT/src/*" || exit 2
git -C "$WT" archive "$SHA" tools/hbm_layer_vehicle tools/hdc_golden_v41.py tools/hdc_golden.py tools/rtl_gpu_sm_exact.py \
  tools/rtl_hdc_v41_blockdot_campaign.py rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv results/rtl/hbm_ds_layer_tput_1018/fixtures/L00 \
  results/rtl/hbm_ds_layer_tput_1018/fixtures/L02 results/rtl/hbm_ds_layer_tput_1018/fixtures/L14 \
  results/rtl/hbm_ds_layer_tput_1018/fixtures/head | ssh "$HOST" "tar -x -C $OUT/src" || exit 2
echo "$SHA" | ssh "$HOST" "cat > $OUT/src/REV"
VL='VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
T="cd $OUT/src && $VL HDC_V41_ARITH=chunk8 python3 tools/hbm_layer_vehicle/sm_mv_unit.py run --bundle $BUNDLE --work $OUT/work"
if [ "$LAYERS" = smoke ]; then
J="$T --fixtures $FIX/L00 --weights $SMW/L00 --recs 4 --sm0-only --out $OUT/out/smoke.json > $OUT/out/smoke.log 2>&1; echo SMOKE_RC \$?; tail -n 2 $OUT/out/smoke.log"
J="$J; $T --fixtures $FIX/L00 --weights $SMW/L00 --recs 4 --sm0-only --mut wbit --out $OUT/out/mut_wbit.json > $OUT/out/mut_wbit.log 2>&1; echo MUT_WBIT_RC \$?; $T --fixtures $FIX/L00 --weights $SMW/L00 --recs 4 --sm0-only --mut nopkt --out $OUT/out/mut_nopkt.json > $OUT/out/mut_nopkt.log 2>&1; echo MUT_NOPKT_RC \$?"
else J="true"; for L in $LAYERS; do
  J="$J; $T --fixtures $FIX/$L --weights $SMW/$L ${6:-} --out $OUT/out/$L.json > $OUT/out/$L.log 2>&1; echo ${L}_RC \$?; tail -n 1 $OUT/out/$L.log"
done; fi
/home/ubuntu/bin/ot-run --mem ${MEM:-64} --threads 16 --dir "$OUT" -- bash -c "$J"
echo "SM_MV_UNIT_DONE"
