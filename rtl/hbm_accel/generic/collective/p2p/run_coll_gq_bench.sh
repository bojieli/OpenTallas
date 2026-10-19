#!/usr/bin/env bash
# HBM-COLLQ gather-master bench (tb_hgi_coll_gq): 4 quadrants x (ot_hgi_coll_gq + ring A ot_hgi_coll_ring_ag + ring B
# ot_hgi_coll_ring_b_stop + read/kq static shares + VM model). Scenario 0 = bit-exact reference gather (plain + QBG vs
# hdc_golden_v41.quant_fp8) at the compiled VM edges; faults 1..4 must fault; mutants m1..m5 (core) and kq1 (share)
# must FAIL; m7 = quantiser element line (ot_hdc_delay_hc) one bank short. The full run also runs the closed tree13 exact bench
# (tb_aq_tree13, 1,024 blocks vs ot_hdc_actquant) on ot_hgi_coll_aq13.   Usage: run_coll_gq_bench.sh OUT [m1..m6|kq1]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); ONE=${2:-}; mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-verilator}
P=rtl/hbm_accel/generic/collective/p2p
python3 tools/hgi_sim/collq_gather_1018.py check | tee "$OUT/schedule_check.log"
python3 tools/hgi_sim/collq_gather_1018.py vectors "$OUT/vec" > "$OUT/vec.log"
LIB=("$P/ot_hgi_coll_gq.sv" "$P/ot_hgi_coll_gq_target16.sv" "$P/ot_hgi_coll_ring_ag.sv" "$P/ot_hgi_coll_ring_ag_lane.sv" "$P/ot_hgi_coll_ring_b_stop.sv"
     "$P/ot_hgi_coll_pring_static_state_capture.sv" "$P/ot_hgi_coll_pring_static.sv"
     rtl/hbm_accel/index/quad_1017/ot_hbm_idx_vm_share2_static.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
     rtl/lib/ot_rst_relay.sv "$P/ot_hgi_coll_aq13.sv" "$P/ot_hgi_coll_aq_scale13r.sv"
     rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv
     rtl/hdc/ot_hdc_delay_hc.sv rtl/hdc/ot_hdc_cg.sv
     rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
MEM=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
LIB+=("$MEM")
FL=(-DOT_COLLQ_SRAM --binary --timing -O2 -j "${JOBS:-16}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN)
build(){ "$V" "${FL[@]}" -GMUT=$2 -GKQMUT=$3 -GVEC="\"$OUT/vec\"" --top-module tb_hgi_coll_gq --Mdir "$OUT/$1" "$P/tb_hgi_coll_gq.sv" "${LIB[@]}" > "$OUT/$1.build.log" 2>&1 || { tail -40 "$OUT/$1.build.log"; exit 2; }; }
mut(){ case $1 in m[1-7]) echo "${1#m} 0";; kq1) echo "0 1";; *) echo "unknown mutant $1" >&2; exit 2;; esac; }
runmut(){ # $1 name -> log; m* run scenario 0, kq1 runs fault 3
  local a=""; [[ $1 == kq1 ]] && a="+fault=3"; [[ $1 == m6 ]] && a="+fault=4"
  "$OUT/mut_$1/Vtb_hgi_coll_gq" $a > "$OUT/mut_$1.log" 2>&1 || true
  if grep -q '^COLLQ PASS \|^COLLQ FAULT PASS ' "$OUT/mut_$1.log"; then echo "COLLQ MUTANT $1 ESCAPED"; return 1; fi
  echo "COLLQ MUTANT $1 REJECTED: $(grep -m1 'COLLQ' "$OUT/mut_$1.log")"; grep 'COLLQ' "$OUT/mut_$1.log" | tail -2; }
if [[ -n "$ONE" ]]; then build mut_$ONE $(mut $ONE); runmut $ONE && exit 1 || exit 0; fi
build gq 0 0
"$OUT/gq/Vtb_hgi_coll_gq" > "$OUT/gq.s0.log" 2>&1 || true
grep 'COLLQ' "$OUT/gq.s0.log" | tail -5
grep -q '^COLLQ PASS ' "$OUT/gq.s0.log" || { echo "COLLQ BENCH FAIL scenario 0"; exit 1; }
for s in 1 2 3 4; do
 "$OUT/gq/Vtb_hgi_coll_gq" +fault=$s > "$OUT/gq.f$s.log" 2>&1 || true
 grep -q '^COLLQ FAULT PASS ' "$OUT/gq.f$s.log" || { echo "COLLQ fault $s ESCAPED"; cat "$OUT/gq.f$s.log" | tail -3; exit 1; }
 grep -h 'COLLQ FAULT PASS' "$OUT/gq.f$s.log"
done
echo "COLLQ FAULTS PASS 4"
# closed tree13 exact bench on the gather master's quantiser copy (same tb, candidate module renamed)
sed 's/ot_hbm_xp_aq_tree13 #/ot_hgi_coll_aq13 #/' physical/hbm_xp_aq_tree13_1014/tb_aq_tree13.sv > "$OUT/tb_aq13.sv"
"$V" -DOT_COLLQ_SRAM --binary --timing -j "${JOBS:-16}" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb --Mdir "$OUT/aq13" "$OUT/tb_aq13.sv" \
  "$P/ot_hgi_coll_aq13.sv" "$P/ot_hgi_coll_aq_scale13r.sv" rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv \
  rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_hc.sv rtl/hdc/ot_hdc_cg.sv "$MEM" > "$OUT/aq13.build.log" 2>&1 || { tail -40 "$OUT/aq13.build.log"; exit 2; }
"$OUT/aq13/Vtb" > "$OUT/aq13.log" 2>&1 || true
grep -q '^AQ_TREE13_EXACT_PASS blocks1024 ' "$OUT/aq13.log" || { echo "COLLQ AQ13 FAIL"; tail -3 "$OUT/aq13.log"; exit 1; }
echo "COLLQ AQ13 $(grep -m1 AQ_TREE13_EXACT_PASS "$OUT/aq13.log")"
# r4: rebalanced scale multiply vs the closed ot_hbm_xp_aq_scale13 (every a exponent field, both coefficients)
"$V" -DOT_COLLQ_SRAM --binary --timing -j "${JOBS:-16}" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_aq_scale13r_eq --Mdir "$OUT/sc13r" \
  "$P/tb_aq_scale13r_eq.sv" "$P/ot_hgi_coll_aq_scale13r.sv" physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv > "$OUT/sc13r.build.log" 2>&1 || { tail -40 "$OUT/sc13r.build.log"; exit 2; }
"$OUT/sc13r/Vtb_aq_scale13r_eq" > "$OUT/sc13r.log" 2>&1 || true
grep -q '^SCALE13R_EQ PASS ' "$OUT/sc13r.log" || { echo "COLLQ SCALE13R FAIL"; tail -5 "$OUT/sc13r.log"; exit 1; }
echo "COLLQ $(grep -m1 SCALE13R_EQ "$OUT/sc13r.log")"
nm=0
for m in m1 m2 m3 m4 m5 m6 m7 kq1; do build mut_$m $(mut $m); runmut $m || exit 1; nm=$((nm+1)); done
echo "COLLQ BENCH PASS mutants_rejected=$nm"
