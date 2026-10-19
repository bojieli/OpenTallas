#!/usr/bin/env bash
# VEH-ATT3 (10-19): fleet driver of the Qwen D4G8 attention unit pre-check (qwen_att_unit.py run) on the die SM master.
#   run_qwen_att_unit.sh REV KVDIR BUNDLE OUTROOT ["L0:0 chain:1"]
# KVDIR = qwen_att_kv.py output (<stage>/att_kv.{json,npz}) on HOST; archives REV's tools + bench into OUTROOT/src on HOST
# (default ot-epyc5, the host holding the GEN2b BUNDLE), then two ot-run jobs (Verilator 5.050):
#   pos   every SM's QK (probe-calibrated landing window) + every block's PV, each stage:L in turn (must PASS), then the
#         'early' QK publish schedule mutant on SM 0 (must FAIL)
#   mut   KVMUT 4 (h128 QK beat takes its 4 rows in reverse sub-row order) on QK SM 0, then KVMUT 2 (h128 PV beat half
#         swapped) on PV block 0 (both must FAIL)
set -uo pipefail
REV=$1; KV=$2; BUNDLE=$3; OUT=$4; SL=${5:-"L0:0 chain:1"}; HOST=${HOST:-ot-epyc5}
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
SHA=$(git -C "$WT" rev-parse "$REV")
ssh "$HOST" "mkdir -p $OUT/src $OUT/out && rm -rf $OUT/src/*" || exit 2
git -C "$WT" archive "$SHA" tools/hbm_layer_vehicle tools/hbm_sm_attention tools/hgi_sim tools/hdc_golden_v41.py \
  tools/hdc_golden.py tools/hbm_svc_packed136_image.py rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv | ssh "$HOST" "tar -x -C $OUT/src" || exit 2
echo "$SHA" | ssh "$HOST" "cat > $OUT/src/REV"
VL='VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
T="cd $OUT/src && $VL HDC_V41_ARITH=chunk8 python3 tools/hbm_layer_vehicle/qwen_att_unit.py run --kv $KV --bundle $BUNDLE"
POS=""
for x in $SL; do S=${x%%:*}; L=${x##*:}
  POS="$POS $T --stage $S --L $L --work $OUT/work_pos --out $OUT/out/${S}_L${L}_pos.json > $OUT/out/${S}_L${L}_pos.log 2>&1; echo POS_${S}_L${L}_RC \$?;"
done
S0=${SL%%:*}; S0=${S0%% *}; L0=${SL#*:}; L0=${L0%% *}
/home/ubuntu/bin/ot-run --mem ${MEM:-64} --threads 16 --dir "$OUT" -- bash -c "$POS \
  $T --stage $S0 --L $L0 --work $OUT/work_pos --calib $OUT/work_pos/calib_${S0}_L${L0}.json --smut early --sms 0 --kinds qk \
  --out $OUT/out/${S0}_L${L0}_mut_early.json > $OUT/out/${S0}_L${L0}_mut_early.log 2>&1; echo EARLY_RC \$?; tail -n 1 $OUT/out/*_pos.log" &
P1=$!
/home/ubuntu/bin/ot-run --mem ${MEM:-64} --threads 16 --dir "$OUT" -- bash -c "$T --stage $S0 --L $L0 --work $OUT/work_kv4 --dmut 4 --sms 0 --kinds qk \
  --out $OUT/out/${S0}_L${L0}_mut_kv4.json > $OUT/out/${S0}_L${L0}_mut_kv4.log 2>&1; echo KV4_RC \$?; \
  $T --stage $S0 --L $L0 --work $OUT/work_kv2 --dmut 2 --sms 0 --kinds pv --blocks 0 \
  --out $OUT/out/${S0}_L${L0}_mut_kv2.json > $OUT/out/${S0}_L${L0}_mut_kv2.log 2>&1; echo KV2_RC \$?" &
P2=$!
wait $P1; R1=$?; wait $P2
echo "QWEN_ATT_UNIT_DONE pos_rc=$R1"
