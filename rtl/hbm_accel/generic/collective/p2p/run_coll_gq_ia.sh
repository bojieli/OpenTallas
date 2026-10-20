#!/usr/bin/env bash
# HBM-VMEARLY-COLL 10-19: ISSUE_AHEAD early VM read issue of the COLL gather master (tb_hgi_coll_gq_ia) on the GEN2-shaped
# read path (LANES 1, VM_RT 74, BANK_RT 72 = the HBM-BANKLAT-COLL budget), schedule from tools/hgi_sim/collq_gather_1018.py
# ia-bench (12 DS rows, row 3 dependent on row 2's landed words).
#   run_coll_gq_ia.sh OUT CASE
#     CASE ia0 | ia1 | ia2 | ia3 : schedule + RTL at ISSUE_AHEAD N: scenario 0 must PASS (bit-exact, compiled edges, exposure
#                                  = compiler); N > 0 also +fault=5 (slot reused while draining) must FAULT
#     CASE m7   : ISSUE_AHEAD 1, RTL MUT 7 (slot index ignored: live slot overwritten)          -> must FAIL
#     CASE dep  : ISSUE_AHEAD 1, compiler ignores RAW (row 3 reads before row 2's writes retire)  -> must FAIL (stale data)
#     CASE iaign: ISSUE_AHEAD 1 schedule, RTL built ISSUE_AHEAD 0 (parameter ignored)            -> must FAIL
# Verilator = the closure daemon's 5.050.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); CASE=$2; mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=rtl/hbm_accel/generic/collective/p2p
IA=1; GQIA=""; MUT=0; DEPM=""; MUTANT=1
case $CASE in
  ia0) IA=0; MUTANT=0;; ia1) IA=1; MUTANT=0;; ia2) IA=2; MUTANT=0;; ia3) IA=3; MUTANT=0;;
  m7) MUT=7;; dep) DEPM=--dep-mutant;; iaign) GQIA=0;;
  *) echo "unknown case $CASE" >&2; exit 2;;
esac
"$V" --version | tee "$OUT/verilator.version"
python3 tools/hgi_sim/collq_gather_1018.py --vm-rt 74 ia-check | tee "$OUT/ia_check.log"
python3 tools/hgi_sim/collq_gather_1018.py --vm-rt 74 ia-bench "$OUT/sched" $IA --lanes $DEPM | tee "$OUT/sched.log"
python3 tools/hgi_sim/collq_gather_1018.py vectors "$OUT/vec" > "$OUT/vec.log"
LIB=("$P/ot_hgi_coll_gq.sv" "$P/ot_hgi_coll_ring_ag.sv" "$P/ot_hgi_coll_ring_ag_lane.sv" "$P/ot_hgi_coll_ring_b_stop.sv"
     "$P/ot_hgi_coll_pring_static_state_capture.sv" "$P/ot_hgi_coll_pring_static.sv"
     rtl/hbm_accel/index/quad_1017/ot_hbm_idx_vm_share2_static.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
     rtl/lib/ot_rst_relay.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv
     rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv
     rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
sha256sum "$P/tb_hgi_coll_gq_ia.sv" "${LIB[@]}" tools/hgi_sim/collq_gather_1018.py > "$OUT/sources.sha256"
"$V" --binary --timing -O2 -j "${JOBS:-16}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP -Wno-TIMESCALEMOD \
  -Wno-MULTIDRIVEN -GLANES=1 -GVM_RT=74 -GBANK_RT=72 -GIA=$IA ${GQIA:+-GGQIA=$GQIA} -GMUT=$MUT -GROWS="\"$OUT/sched/rows.txt\"" \
  -GVEC="\"$OUT/vec\"" --top-module tb_hgi_coll_gq_ia --Mdir "$OUT/obj" "$P/tb_hgi_coll_gq_ia.sv" "${LIB[@]}" \
  > "$OUT/build.log" 2>&1 || { tail -40 "$OUT/build.log"; exit 2; }
"$OUT/obj/Vtb_hgi_coll_gq_ia" > "$OUT/s0.log" 2>&1 || true
grep 'COLLQ' "$OUT/s0.log" | tail -18
if [[ $MUTANT == 0 ]]; then
  grep -q '^COLLQ_IA PASS ' "$OUT/s0.log" || { echo "COLLQ_IA $CASE FAIL scenario 0"; exit 1; }
  if [[ $IA -gt 0 ]]; then
    "$OUT/obj/Vtb_hgi_coll_gq_ia" +fault=5 > "$OUT/f5.log" 2>&1 || true
    grep -q '^COLLQ FAULT PASS ' "$OUT/f5.log" || { echo "COLLQ_IA $CASE fault 5 ESCAPED"; tail -3 "$OUT/f5.log"; exit 1; }
    grep -h 'COLLQ FAULT PASS' "$OUT/f5.log"
  fi
  echo "COLLQ_IA_BENCH $CASE PASS"
else
  if grep -q '^COLLQ_IA PASS \|^COLLQ PASS ' "$OUT/s0.log"; then echo "COLLQ_IA MUTANT $CASE ESCAPED"; exit 1; fi
  echo "COLLQ_IA MUTANT $CASE REJECTED: $(grep -m1 'COLLQ' "$OUT/s0.log")"
fi
rm -rf "$OUT/obj"
