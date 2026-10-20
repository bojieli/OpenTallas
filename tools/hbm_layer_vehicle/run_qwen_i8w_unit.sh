#!/usr/bin/env bash
# HBM-QINT8B (10-20): fleet driver of the WIDE INT8 front (ot_hbm_sm_i8w_front, INT8W 1, command mode 3) SM-unit bench.
#   run_qwen_i8w_unit.sh REV KVDIR BUNDLE OUTROOT [L=0]     (ot-epyc5: Qwen3-8B L0 capture + the GEN2b bundle)
# Two unpinned ot-run jobs (Verilator 5.050), --dir OUTROOT (data locality):
#   pos  every captured record (qkv / o / gu / down) of layer L, SM-0 block, wide front (must PASS bit-exact);
#        + narrow regression: the same tags through the ENABLE_INT8 path with this tree's INT8W=0 front_static (PASS,
#        cycles == the SMB-INT8 baseline 3206 / 2161 / 12422 / 6278)
#   mut  compiler wbit / halfswap / nopkt / late / tag and RTL sign / noswap / half -- all must FAIL (qkv)
set -uo pipefail
VL='VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
REV=$1; KV=$2; BUNDLE=$3; OUT=$4; L=${5:-0}; HOST=${HOST:-ot-epyc5}
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel); SHA=$(git -C "$WT" rev-parse "$REV")
ssh "$HOST" "mkdir -p $OUT/src $OUT/out && rm -rf $OUT/src/*" || exit 2
git -C "$WT" archive "$SHA" tools/hbm_layer_vehicle tools/hgi_sim tools/hdc_golden_v41.py tools/hdc_golden.py \
  tools/rtl_gpu_sm_exact.py tools/rtl_hdc_v41_blockdot_campaign.py rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv \
  rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_front_static.sv \
  rtl/hbm_accel/sm/attn/ot_hbm_sm_i8w_front.sv rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv \
  rtl/hbm_accel/sm/static/ot_smh_static_int8.sv rtl/hbm_accel/sm/static/ot_smh_int8_tile.sv | ssh "$HOST" "tar -x -C $OUT/src" || exit 2
echo "$SHA" | ssh "$HOST" "cat > $OUT/src/REV"
T="cd $OUT/src && $VL HDC_V41_ARITH=chunk8 python3 tools/hbm_layer_vehicle/qwen_sm_mv_unit.py run --kv $KV --L $L --bundle $BUNDLE"
/home/ubuntu/bin/ot-run --mem ${MEM:-48} --threads 16 --dir "$OUT" -- bash -c "\
  $T --i8w --work $OUT/work --out $OUT/out/L${L}_i8w_pos.json > $OUT/out/L${L}_i8w_pos.log 2>&1; echo POS_RC \$?; \
  $T --work $OUT/work --out $OUT/out/L${L}_narrow_reg.json > $OUT/out/L${L}_narrow_reg.log 2>&1; echo NARROW_RC \$?; \
  tail -n 1 $OUT/out/L${L}_i8w_pos.log $OUT/out/L${L}_narrow_reg.log" > /tmp/i8w_pos_$$.log 2>&1 &
P1=$!
/home/ubuntu/bin/ot-run --mem ${MEM:-48} --threads 16 --dir "$OUT" -- bash -c "\
  for M in wbit halfswap nopkt late tag sign noswap half; do $T --i8w --tags qkv --work $OUT/work_mut --mut \$M \
    --out $OUT/out/mut_\$M.json > $OUT/out/mut_\$M.log 2>&1; echo MUT_\${M}_RC \$?; done" > /tmp/i8w_mut_$$.log 2>&1 &
P2=$!
wait $P1; echo "POS_JOB_RC $?"; cat /tmp/i8w_pos_$$.log
wait $P2; echo "MUT_JOB_RC $?"; cat /tmp/i8w_mut_$$.log
echo "QWEN_I8W_UNIT_DONE"
