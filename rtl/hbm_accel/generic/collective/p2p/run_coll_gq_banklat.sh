#!/usr/bin/env bash
# HBM-BANKLAT-COLL 10-19: gather master + read share on the GEN2-shaped VM read path (tb_hgi_coll_gq LANES=1: faces bank
# pin +1, unequal per-bank rq/rr lanes summing to LT=65 (request side padded), gq<->share lanes 4+4).
# Budget values: share BANK_RT 72 (= 6 + 1 + 65), gq VM_RT 74 (= 72 - 6 + 8); SREG 1 (registered share leaf) VM_RT 76.
#   run_coll_gq_banklat.sh OUT CASE      CASE: pass | sreg (scenario 0 + faults 1..4 must PASS)
#                                              old_vm | old_bank | off_vm | off_bank (scenario 0 must FAIL)
# Verilator = the closure daemon's 5.050.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); CASE=$2; mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=rtl/hbm_accel/generic/collective/p2p
case $CASE in
  pass)     G="-GLANES=1 -GVM_RT=74 -GBANK_RT=72";;
  sreg)     G="-GLANES=1 -GVM_RT=76 -GBANK_RT=72 -GSREG=1";;
  old_vm)   G="-GLANES=1 -GVM_RT=0 -GBANK_RT=72";;      # gather master at today's n+8 capture
  old_bank) G="-GLANES=1 -GVM_RT=74 -GBANK_RT=6";;      # share owner tap at today's own[6]
  off_vm)   G="-GLANES=1 -GVM_RT=73 -GBANK_RT=72";;     # one edge short
  off_bank) G="-GLANES=1 -GVM_RT=74 -GBANK_RT=71";;
  *) echo "unknown case $CASE" >&2; exit 2;;
esac
"$V" --version | tee "$OUT/verilator.version"
python3 tools/hgi_sim/collq_gather_1018.py vectors "$OUT/vec" > "$OUT/vec.log"
LIB=("$P/ot_hgi_coll_gq.sv" "$P/ot_hgi_coll_ring_ag.sv" "$P/ot_hgi_coll_ring_ag_lane.sv" "$P/ot_hgi_coll_ring_b_stop.sv"
     "$P/ot_hgi_coll_pring_static_state_capture.sv" "$P/ot_hgi_coll_pring_static.sv"
     rtl/hbm_accel/index/quad_1017/ot_hbm_idx_vm_share2_static.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
     rtl/lib/ot_rst_relay.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv
     rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv
     rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
sha256sum "$P/tb_hgi_coll_gq.sv" "${LIB[@]}" tools/hgi_sim/collq_gather_1018.py > "$OUT/sources.sha256"
"$V" --binary --timing -O2 -j "${JOBS:-16}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP -Wno-TIMESCALEMOD \
  -Wno-MULTIDRIVEN $G -GVEC="\"$OUT/vec\"" --top-module tb_hgi_coll_gq --Mdir "$OUT/obj" "$P/tb_hgi_coll_gq.sv" "${LIB[@]}" \
  > "$OUT/build.log" 2>&1 || { tail -40 "$OUT/build.log"; exit 2; }
"$OUT/obj/Vtb_hgi_coll_gq" > "$OUT/s0.log" 2>&1 || true
grep 'COLLQ' "$OUT/s0.log" | tail -4
if [[ $CASE == pass || $CASE == sreg ]]; then
  grep -q '^COLLQ PASS ' "$OUT/s0.log" || { echo "COLLQ_BANKLAT $CASE FAIL scenario 0"; exit 1; }
  for s in 1 2 3 4; do
    "$OUT/obj/Vtb_hgi_coll_gq" +fault=$s > "$OUT/f$s.log" 2>&1 || true
    grep -q '^COLLQ FAULT PASS ' "$OUT/f$s.log" || { echo "COLLQ_BANKLAT $CASE fault $s ESCAPED"; tail -3 "$OUT/f$s.log"; exit 1; }
    grep -h 'COLLQ FAULT PASS' "$OUT/f$s.log"
  done
  echo "COLLQ_BANKLAT $CASE PASS"
else
  if grep -q '^COLLQ PASS ' "$OUT/s0.log"; then echo "COLLQ_BANKLAT MUTANT $CASE ESCAPED"; exit 1; fi
  echo "COLLQ_BANKLAT MUTANT $CASE REJECTED: $(grep -m1 'COLLQ' "$OUT/s0.log")"
fi
rm -rf "$OUT/obj"
