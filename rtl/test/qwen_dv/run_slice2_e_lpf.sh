#!/usr/bin/env bash
# OWN-QWEN/SLICE-E 10-18: benches of the landed E slice parent (run on the FLEET from the repository root; Verilator 5.050).
#   eq  M     lockstep qfd_dv_slice2_e (SU_LT 1, HD_W130 1) vs the wires-only re-cut qfd_dv_slice2_e_lpf
#             (M = 0: must print LPF_EQ PASS; M = 1/2/3: +define+OT_LPF_MUT<M>, must print LPF_EQ FAIL)
#   lp  M     lockstep qfd_dv_slice2_e_lpf (flat) vs the generated landed parent qfd_dv_slice2_e_lpf_lp, lp.py MUT M
#             (0 PASS; 1 landing bypassed, 2 landing read K+1, 3 pad short, 4 core reset run long: FAIL)
#   audit     lp.py region audit of the generated RTL (+ the unland mutant must FAIL it)
#   bash rtl/test/qwen_dv/run_slice2_e_lpf.sh OUTDIR eq|lp|audit [M]
set -u
OUT=$1; KIND=$2; M=${3:-0}; mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
SIM="rtl/qwen_dv/qfd_dv_vm.sv rtl/qwen_dv/qfd_dv_stream.sv rtl/qwen_dv/qfd_dv_su8_entries.sv rtl/hdc/ot_hdc_vstream_lane.sv
 rtl/hdc/ot_hdc_vreduce.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/physical/ot_hdc_vred_pending_guard.sv
 rtl/test/full_sm_service/sram_models.sv rtl/test/hbm_rf_visibility/scale_sram_model.sv rtl/qwen_dv/qfd_dv_heads.sv
 rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/lib/ot_rst_pipe.sv rtl/qwen_dv/qfd_dv_slice2.sv rtl/qwen_dv/qfd_dv_redstn2.sv
 rtl/qwen_dv/qfd_dv_scalar2.sv rtl/qwen_dv/qfd_dv_su_lane.sv rtl/hdc/ot_hdc_vstream_lane_t.sv rtl/hdc/ot_hdc_vstream_sfu_t.sv
 rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/physical/ot_hdc_vstream_lane_clock_entries_candidate.sv
 rtl/qwen_dv/qfd_dv_slice2_faces.sv rtl/qwen_dv/qfd_dv_slice2_lpf_parts.sv rtl/qwen_dv/qfd_dv_slice2_e_lpf.sv"
VF="--binary -O2 -j ${VJOBS:-16} -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0"
case $KIND in
  eq)
    D=""; [ "$M" != 0 ] && D="+define+OT_LPF_MUT$M"
    "$V" $VF $D --top-module tb_qfd_dv_slice2_e_lpf $SIM rtl/test/qwen_dv/tb_qfd_dv_slice2_e_lpf.sv -Mdir "$OUT/obj_eq$M" \
      > "$OUT/build_eq$M.log" 2>&1 && "$OUT/obj_eq$M/Vtb_qfd_dv_slice2_e_lpf" > "$OUT/eq$M.log" 2>&1
    r=$(grep -o 'LPF_EQ [A-Z]*' "$OUT/eq$M.log" 2>/dev/null | head -1); grep -m3 LPF_MISMATCH "$OUT/eq$M.log"
    echo "EQ MUT=$M: ${r:-NO_RESULT (see $OUT/build_eq$M.log)}"; tail -3 "$OUT/build_eq$M.log";;
  lp)
    "$V" $VF -GMUT=$M --top-module tb_qfd_dv_slice2_e_lpf_lp $SIM rtl/common/landed_parent/ot_pl_land.sv \
      rtl/qwen_dv/lp/qfd_dv_slice2_e_lpf_lp.sv rtl/qwen_dv/lp/tb_qfd_dv_slice2_e_lpf_lp.sv -Mdir "$OUT/obj_lp$M" \
      > "$OUT/build_lp$M.log" 2>&1 && "$OUT/obj_lp$M/Vtb_qfd_dv_slice2_e_lpf_lp" > "$OUT/lp$M.log" 2>&1
    r=$(grep -o 'LP_LOCKSTEP [A-Z]*' "$OUT/lp$M.log" 2>/dev/null | head -1); grep -m3 LP_MISMATCH "$OUT/lp$M.log"
    echo "LP MUT=$M: ${r:-NO_RESULT (see $OUT/build_lp$M.log)}"; tail -3 "$OUT/build_lp$M.log";;
  audit)
    python3 tools/landed_parent/lp.py audit tools/landed_parent/specs/qfd_dv_slice2_e_lpf.json > "$OUT/audit.log" 2>&1 && echo "AUDIT PASS" || echo "AUDIT FAIL"
    python3 tools/landed_parent/lp.py audit tools/landed_parent/specs/qfd_dv_slice2_e_lpf.json --rtl "$OUT/unland.sv" --make-unland \
      > "$OUT/audit_unland.log" 2>&1 && echo "AUDIT-UNLAND PASSED (should FAIL)" || echo "AUDIT-UNLAND FAIL (expected)";;
esac
