#!/bin/bash
# HBM-HCROOT6 10-20: lockstep bench of the HC tail child vs the released tail unit (tb_hbm_hc_tail_child_eq, Verilator 5.050).
# Usage: run_hbm_hc_tail_child_eq.sh OUT MUT [N] [SEED] [NATIVE_V CELLS_V]   (NATIVE: the gate-cloned child netlist + cell models)
#   MUT 0 -> TAILC PASS ; MUT 1 (p3 row-max operand off by one group) -> TAILC FAIL
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd); cd "$root"
out=$(realpath -m "${1:?OUT}"); mut=${2:?MUT}; n=${3:-48}; seed=${4:-1}; mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
"$vl" --version
H=rtl/hbm_accel/generic/peers/static_hc
nat=(); if [ -n "${5:-}" ]; then child=("$(realpath "$5")" "$(realpath "$6")"); nat=(+define+NATIVE_DUT); else child=($H/ot_hbm_hc_tail_child_static.sv $H/ot_hgi_hc_tail_os_static.sv); fi
src=(rtl/test/tb_hbm_hc_tail_child_eq.sv "${child[@]}" $H/ot_hbm_hc_tail_unit_static.sv $H/ot_hgi_hc_tail_static.sv
 rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv
 rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sinkhorn_ce.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv
 rtl/lib/ot_rst_relay.sv)
"$vl" --binary --timing -j "${BUILD_JOBS:-8}" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_hbm_hc_tail_child_eq \
  +define+MUT=$mut "${nat[@]}" +define+OT_FP_DATA_NORST -Mdir "$out/obj" -o Vtc "${src[@]}" > "$out/build.log" 2>&1 || { tail -30 "$out/build.log"; exit 3; }
set +e; "$out/obj/Vtc" +N=$n +SEED=$seed > "$out/run.log" 2>&1; rc=$?; set -e
grep -E "TAILC" "$out/run.log" | head -20 || true
grep -E "^TAILC (PASS|FAIL)" "$out/run.log" | tail -1 || true   # HBM-HCROOT8: the verdict line even after >20 ERR lines
echo "HC_TAIL_CHILD_EQ MUT=$mut N=$n SEED=$seed rc=$rc"
rm -rf "$out/obj"
