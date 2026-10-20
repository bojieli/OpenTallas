#!/usr/bin/env bash
# HBM-AGSM8 10-20: DS expert-intermediate gather TRAIN -> w2 x-load static GO chain (tb_agsm8_chain.sv), production shape:
# 7 x 2304-word QBG segments, 4 quadrant gather masters at VM_RT 74 on the GEN2 read path (LANES 1, BANK_RT 72).
#   run_agsm8_chain.sh OUT CASE     CASE: pass  (scenario 0 must PASS bit-exact; gq faults 1..4 must still fault)
#                                         goe   (segment 4 GO one edge early: MUST FAIL)
#                                         swap  (w2 slots 2 / 3 swapped vs the landing order: MUST FAIL)
#                                         overlap (SP = SP_min - 1: descriptor overlap, MUST FAIL)
# Verilator = the closure daemon's 5.050 (fleet via ot-run).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); CASE=$2; mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=rtl/hbm_accel/generic/collective/p2p
VEC="$OUT/vec"
python3 tools/hgi_sim/agsm8_chain_vectors_1020.py "$VEC" --vm-rt 74 > "$OUT/vec.log"
SPM=$(python3 -c "import json;print(json.load(open('$VEC/meta.json'))['sp_min'])")
SPAN=$(python3 -c "import json;print(json.load(open('$VEC/meta.json'))['span_fire_to_last_write'])")
G="-GLANES=1 -GVM_RT=74 -GBANK_RT=72 -GSPAN=$SPAN"
case $CASE in
  pass)    G="$G -GSP=$SPM";;
  goe)     G="$G -GSP=$SPM -GGOE=1 -GGOSEG=4";;
  swap)    G="$G -GSP=$SPM -GSWAP=1";;
  overlap) G="$G -GSP=$((SPM - 1))";;
  *) echo "unknown case $CASE" >&2; exit 2;;
esac
"$V" --version | tee "$OUT/verilator.version"
LIB=("$P/ot_hgi_coll_gq.sv" "$P/ot_hgi_coll_seg_go.sv" "$P/ot_hgi_coll_ring_ag.sv" "$P/ot_hgi_coll_ring_ag_lane.sv" "$P/ot_hgi_coll_ring_b_stop.sv"
     "$P/ot_hgi_coll_pring_static_state_capture.sv" "$P/ot_hgi_coll_pring_static.sv"
     rtl/hbm_accel/index/quad_1017/ot_hbm_idx_vm_share2_static.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
     rtl/lib/ot_rst_relay.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv
     rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv
     rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
sha256sum "$P/tb_agsm8_chain.sv" "$0" "${LIB[@]}" tools/hgi_sim/agsm8_chain_vectors_1020.py tools/hgi_sim/collq_gather_1018.py \
  tools/hdc_golden_v41.py tools/hdc_golden.py > "$OUT/sources.sha256"
echo "$CASE $G" > "$OUT/config.txt"
"$V" --binary --timing -O2 -j "${JOBS:-16}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP -Wno-TIMESCALEMOD \
  -Wno-MULTIDRIVEN $G -GVEC="\"$VEC\"" --top-module tb_agsm8_chain --Mdir "$OUT/obj" "$P/tb_agsm8_chain.sv" "${LIB[@]}" \
  > "$OUT/build.log" 2>&1 || { tail -40 "$OUT/build.log"; echo "AGSM8_CHAIN $CASE BUILD FAIL"; exit 2; }
"$OUT/obj/Vtb_agsm8_chain" > "$OUT/s0.log" 2>&1 || true
grep -E '^AGSM8' "$OUT/s0.log" | tail -14
if [[ $CASE == pass ]]; then
  grep -q '^AGSM8 PASS ' "$OUT/s0.log" || { echo "AGSM8_CHAIN pass FAIL scenario 0"; exit 1; }
  for s in 1 2 3 4; do
    "$OUT/obj/Vtb_agsm8_chain" +fault=$s > "$OUT/f$s.log" 2>&1 || true
    grep -q '^AGSM8 FAULT PASS ' "$OUT/f$s.log" || { echo "AGSM8_CHAIN fault $s ESCAPED"; tail -3 "$OUT/f$s.log"; exit 1; }
  done
  echo "AGSM8_CHAIN pass PASS (scenario 0 bit-exact + faults 1..4 caught)"
else
  if grep -q '^AGSM8 PASS ' "$OUT/s0.log"; then echo "AGSM8_CHAIN $CASE MUTANT ESCAPED"; exit 1; fi
  echo "AGSM8_CHAIN $CASE MUTANT FAILS (as required)"
fi
