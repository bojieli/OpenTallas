#!/usr/bin/env bash
set -euo pipefail
# Remote component simulation, not a production inference/physical gate.
# Caller runs this through the host's unchanged admit.sh from a source snapshot.
test -f rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_prior_debt.sv
mkdir -p build
export NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
set +e
"${AMPERE_GATHER_VERILATOR:-verilator}" --binary --timing --threads 1 -j 16 -Wno-fatal \
  --top-module tb_hbm_gather_readback_fault_ampere --Mdir build \
  rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv \
  rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_prior_debt.sv \
  rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_sm0_borrow.sv \
  rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_gather_bridge.sv \
  rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_gather_owner.sv \
  rtl/test/hbm_accel/tb_hbm_gather_readback_fault_ampere.sv > compile.log 2>&1
compile_rc=$?
printf '%s\n' "$compile_rc" > compile.exit
if [[ "$compile_rc" != 0 ]]; then exit "$compile_rc"; fi
build/Vtb_hbm_gather_readback_fault_ampere > runtime.log 2>&1
runtime_rc=$?
printf '%s\n' "$runtime_rc" > runtime.exit
if [[ "$runtime_rc" != 0 ]]; then exit "$runtime_rc"; fi
grep -q '^PASS_GATHER_READBACK_FAULT ' runtime.log
