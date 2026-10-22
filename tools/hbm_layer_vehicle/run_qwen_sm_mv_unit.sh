#!/usr/bin/env bash
# SMB-INT8 (10-19): fleet driver of the Qwen D4G8 INT8 SM.MATVEC unit pre-check on the die SM master (opt-in INT8 path).
#   run_qwen_sm_mv_unit.sh capture REV OUTROOT [STAGE=L0]         (ot-pve1: Qwen3-8B snapshot; qwen_sm_mv_kv.py)
#   run_qwen_sm_mv_unit.sh unit    REV KVDIR BUNDLE OUTROOT [L=0]   (ot-epyc5: the GEN2b bundle; qwen_sm_mv_unit.py)
# unit = two ot-run jobs (Verilator 5.050):
#   pos  every captured record (qkv / o / gu / down) of layer L: SM-0 block (must PASS), then --all (every row, coverage)
#   mut  wbit (arithmetic: a code bit of the first packed line), sign (arithmetic: converter OT_INT8_MUT_SIGN build),
#        nopkt (schedule: one packed line + its mark withheld), late (schedule: one packed line a cycle late) -- all FAIL;
#        then regress: sm_mv_unit.py smoke (DS L00 k4) with this tree's ot_hbm_accel_smh_attn at DEFAULT parameters (PASS)
set -uo pipefail
MODE=$1; shift
VL='VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
if [ "$MODE" = capture ]; then
  REV=$1; OUT=$2; STAGE=${3:-L0}; HOST=${HOST:-ot-pve1}
  SNAP=${SNAP:-/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218}
  IMG=${IMG:-/srv/opentallas-scratch/claude/veh-att3/qcap/img}
  WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel); SHA=$(git -C "$WT" rev-parse "$REV")
  ssh "$HOST" "mkdir -p $OUT/src $OUT/out && rm -rf $OUT/src/*" || exit 2
  git -C "$WT" archive "$SHA" tools compiler results/arch/hbm_generic_iface_20261009 \
    results/rtl/hbm_qwen_layer_tput_1018/static_schedule.json | ssh "$HOST" "tar -x -C $OUT/src" || exit 2
  echo "$SHA" | ssh "$HOST" "cat > $OUT/src/REV"
  /home/ubuntu/bin/ot-run --mem ${MEM:-24} --threads 2 --dir "$OUT" -- bash -c "cd $OUT/src && \
    python3 tools/hbm_layer_vehicle/qwen_sm_mv_kv.py --snapshot $SNAP --cache $IMG --stage $STAGE --ranks 0 --out $OUT/out \
    > $OUT/out/capture_$STAGE.log 2>&1; rc=\$?; tail -n 1 $OUT/out/capture_$STAGE.log; exit \$rc"
  exit $?
fi
REV=$1; KV=$2; BUNDLE=$3; OUT=$4; L=${5:-0}; HOST=${HOST:-ot-epyc5}
DSFIX=${DSFIX:-}; DSSMW=${DSSMW:-}
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel); SHA=$(git -C "$WT" rev-parse "$REV")
ssh "$HOST" "mkdir -p $OUT/src $OUT/out && rm -rf $OUT/src/*" || exit 2
git -C "$WT" archive "$SHA" tools/hbm_layer_vehicle tools/hgi_sim tools/hdc_golden_v41.py tools/hdc_golden.py \
  tools/rtl_gpu_sm_exact.py tools/rtl_hdc_v41_blockdot_campaign.py rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv \
  rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv \
  rtl/hbm_accel/sm/static/ot_smh_static_int8.sv rtl/hbm_accel/sm/static/ot_smh_int8_tile.sv results/rtl/hbm_ds_layer_tput_1018/fixtures/L00 \
  | ssh "$HOST" "tar -x -C $OUT/src" || exit 2
echo "$SHA" | ssh "$HOST" "cat > $OUT/src/REV"
T="cd $OUT/src && $VL HDC_V41_ARITH=chunk8 python3 tools/hbm_layer_vehicle/qwen_sm_mv_unit.py run --kv $KV --L $L --bundle $BUNDLE"
/home/ubuntu/bin/ot-run --mem ${MEM:-64} --threads 16 --dir "$OUT" -- bash -c "\
  $T --work $OUT/work --out $OUT/out/L${L}_pos.json > $OUT/out/L${L}_pos.log 2>&1; echo POS_RC \$?; \
  $T --work $OUT/work --all --out $OUT/out/L${L}_all.json > $OUT/out/L${L}_all.log 2>&1; echo ALL_RC \$?; \
  tail -n 1 $OUT/out/L${L}_pos.log $OUT/out/L${L}_all.log" &
P1=$!
REG="true"
if [ -n "$DSFIX" ] && [ -n "$DSSMW" ]; then
  REG="cd $OUT/src && $VL HDC_V41_ARITH=chunk8 python3 tools/hbm_layer_vehicle/qwen_sm_mv_unit.py regress --fixtures $DSFIX \
    --weights $DSSMW --bundle $BUNDLE --work $OUT/work_reg --recs 4 --sm0-only --out $OUT/out/regress_default.json \
    > $OUT/out/regress_default.log 2>&1; echo REGRESS_RC \$?"
fi
/home/ubuntu/bin/ot-run --mem ${MEM:-64} --threads 16 --dir "$OUT" -- bash -c "\
  for M in wbit nopkt late; do $T --tags qkv --work $OUT/work_mut --mut \$M --out $OUT/out/mut_\$M.json \
    > $OUT/out/mut_\$M.log 2>&1; echo MUT_\${M}_RC \$?; done; \
  $T --tags qkv --work $OUT/work_mut --mut sign --out $OUT/out/mut_sign.json > $OUT/out/mut_sign.log 2>&1; echo MUT_sign_RC \$?; \
  $REG" &
P2=$!
wait $P1; wait $P2
echo "QWEN_SM_MV_UNIT_DONE"
