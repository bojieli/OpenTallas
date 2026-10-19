#!/usr/bin/env bash
# VEH-ATT (10-19): fleet driver of the attention unit pre-check (att_images.py unit) on the die SM master.
#   run_att_unit.sh REV KVDIR BUNDLE OUTROOT [LAYER=2]
# Archives REV's tools + bench into OUTROOT/src on ot-epyc5 (the host holding KVDIR and BUNDLE), then three ot-run jobs:
#   pos   all SMs' QK + PV on the real fixture rows (must PASS) and the 'early' publish schedule mutant (must FAIL)
#   kv2   ot_hbm_sm_kv_line converter mutant 2 (KVMUT: wrong beat) on one KV8 and one KV4 SM (must FAIL)
set -uo pipefail
REV=$1; KV=$2; BUNDLE=$3; OUT=$4; L=${5:-2}; HOST=${HOST:-ot-epyc5}
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
SHA=$(git -C "$WT" rev-parse "$REV")
ssh "$HOST" "mkdir -p $OUT/src $OUT/out && rm -rf $OUT/src/*" || exit 2
git -C "$WT" archive "$SHA" tools/hbm_layer_vehicle tools/hbm_sm_attention tools/hgi_sim tools/hdc_golden_v41.py \
  tools/hdc_golden.py rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv | ssh "$HOST" "tar -x -C $OUT/src" || exit 2
echo "$SHA" | ssh "$HOST" "cat > $OUT/src/REV"
VL='VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
T="cd $OUT/src && $VL HDC_V41_ARITH=chunk8 python3 tools/hbm_layer_vehicle/att_images.py unit --kv $KV --layer $L --bundle $BUNDLE"
/home/ubuntu/bin/ot-run --mem ${MEM:-64} --threads 16 --dir "$OUT" -- bash -c "$T --work $OUT/work_pos --out $OUT/out/L${L}_pos.json \
  > $OUT/out/L${L}_pos.log 2>&1; rc=\$?; $T --work $OUT/work_pos --smut early --sms 0 --kinds qk --out $OUT/out/L${L}_mut_early.json \
  > $OUT/out/L${L}_mut_early.log 2>&1; echo POS_RC \$rc EARLY_RC \$?; tail -n 2 $OUT/out/L${L}_pos.log; exit \$rc" &
P1=$!
/home/ubuntu/bin/ot-run --mem ${MEM:-64} --threads 16 --dir "$OUT" -- bash -c "$T --work $OUT/work_kv2 --dmut 2 --sms 0,2 \
  --out $OUT/out/L${L}_mut_kv2.json > $OUT/out/L${L}_mut_kv2.log 2>&1; echo KV2_RC \$?; tail -n 1 $OUT/out/L${L}_mut_kv2.log" &
P2=$!
wait $P1; R1=$?; wait $P2
echo "ATT_UNIT_DONE pos_rc=$R1"
