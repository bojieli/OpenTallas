#!/bin/bash
# HBMc/QHUB4 10-22: tb_hbm_hc_qhub_land (hub LAND form vs the c10 form, delayed per output class) on Verilator 5.050.
# Usage: run_qhub_land.sh OUT [LAND] [LMUT]   LAND 7 LMUT 0 -> "QHUB_LAND PASS"; LMUT 7 -> "QHUB_LAND FAIL" (must)
set -euo pipefail
root=$(cd "$(dirname "$0")/../../../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?OUT}"); land=${2:-7}; lmut=${3:-0}; mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
H=rtl/hbm_accel/generic/peers/static_hc
python3 tools/prepare_fp32_fan32_models.py --out "$out/cells.v" > "$out/fan32_models.log"
"$vl" --binary --timing -j "${HC_BUILD_JOBS:-16}" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
  --top-module tb_hbm_hc_qhub_land +define+LAND=$land +define+LMUT=$lmut -Mdir "$out/obj" -o Vqh \
  rtl/test/tb_hbm_hc_qhub_land.sv rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv \
  rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv $H/ot_hbm_hc_qcal_static.sv $H/ot_hgi_hc_residual_vm_static.sv \
  $H/ot_hgi_hc_result_vm_static.sv $H/ot_hgi_hc_gathered_mix_reader_static.sv $H/ot_hbm_hc_q_static.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  $H/ot_hbm_hc_qhub_static.sv $H/ot_hbm_hc_qcen_static.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fastfp.sv \
  rtl/hdc/ot_hdc_prefix.sv $H/ot_hbm_hc_qtree16_static.sv $H/ot_hc_rst_relay_k.sv $H/ot_hgi_hc_gathered_mix_reader_f32_static.sv \
  $H/ot_hgi_hc_result_vm_f32_static.sv rtl/hdc/ot_hdc_fp32_add_lat_fan32.sv rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native.v \
  "$out/cells.v" > "$out/build.log" 2>&1
set +e; "$out/obj/Vqh" > "$out/run.log" 2>&1; rc=$?; set -e
grep -E '^QHUB_LAND (activity|PASS|FAIL)' "$out/run.log"
grep -m 6 '^MISMATCH' "$out/run.log" || true
"$vl" --version
rm -rf "$out/obj"
grep -q "QHUB_LAND PASS" "$out/run.log"
