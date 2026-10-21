#!/bin/bash
# ELEM-GAPS/HBMB 2026-10-18: die-configuration bench of the HC ROOT ot_hbm_hc_root_static (d4g GEN1 instance hc_eng,
# l3_vm_hc_coll.py: QDRLY 2, XRD = XRU = 0) in the d4g U-ring form (hub DRLY 2, U relay b7->b0 XRLY 1; HBM-RTL5/hc 0fi):
# tb_hbm_hc_eng4_static (root + 4 x ot_hbm_hc_qeng_static) in lockstep with the single-block golden
# (tools/rtl_hbm_hc_eng_static_gate.py --split --rs 104, P1).  Same build/sources as run_hbm_hc_eng4_ring.sh + ot_hbm_rly.
# Usage: run_hbm_hc_root_uring.sh OUT [MUT [QDRLY [RAW0]]]
#   pass:    MUT 0 QDRLY 2 RAW0 167 -> HC_ENG PASS, HC_MIX_CYCLES 998
#   mutants: MUT 2 (root tail unit 0 pre-sigmoid eps dropped) -> HC_ENG FAIL (TAIL_MISMATCH)
#            QDRLY 1 (root not told about the hub relay: SYS_LAT one short) -> HC_ENG_FAULT ps=1
#            RAW0 165 (compiler keeps the ring-form RAW0) -> HC_ENG_FAULT core=1
# Every verdict line is printed (no head cut: chain_ring.sh 10-18 05:16 read a FAILED mutant as passing because the
# RUN_RC line fell outside a head -8 window).  Verilator 5.050 --hierarchical, ~50 GB RSS, ~25 min build.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd); cd "$root"
out=$(realpath -m "${1:?OUT}"); mut=${2:-0}; qd=${3:-2}; raw0=${4:-167}; mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
H=rtl/hbm_accel/generic/peers/static_hc
src=(rtl/test/tb_hbm_hc_eng4_static.sv $H/ot_hbm_hc_root_static.sv $H/ot_hbm_hc_qeng_static.sv $H/ot_hbm_hc_qcen_static.sv
 $H/ot_hbm_hc_bankq_static.sv $H/ot_hbm_hc_eng_seq_static.sv $H/ot_hbm_hc_bank_static.sv $H/ot_hbm_hc_tail_unit_static.sv
 $H/ot_hdc_v41x_hcp_sys1_static.sv $H/ot_hgi_hc_tail_static.sv $H/ot_hbm_hc_xw_rx_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv
 rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv
 rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sinkhorn_ce.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/lib/ot_rst_relay.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
python3 tools/rtl_hbm_hc_eng_static_gate.py --run "$out/case" --split --npos 1 --raw0 "$raw0" --rs 104 > "$out/vectors.log"
"$vl" --binary --timing --hierarchical -j "${HC_BUILD_JOBS:-16}" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
  --top-module tb_hbm_hc_eng4_static +define+MUT=$mut +define+OT_FP_DATA_NORST \
  +define+HC_DRLY=2 +define+HC_XRLY=1 +define+HC_QDRLY=$qd -Mdir "$out/obj" -o Vroot \
  rtl/test/tb_hbm_hc_eng4_static_hier.vlt "${src[@]}" > "$out/build.log" 2>&1
set +e; (cd "$out/case" && "$out/obj/Vroot" $(cat plus.txt)) > "$out/run.log" 2>&1; rc=$?; set -e
grep -E "HC_ENG_DONE|HC_ENG PASS|HC_ENG FAIL|HC_ENG_FAULT|MISMATCH" "$out/run.log" || true
echo "HC_ROOT_URING MUT=$mut QDRLY=$qd RAW0=$raw0 rc=$rc"
rm -rf "$out/obj"
exit $rc
