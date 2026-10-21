#!/usr/bin/env bash
# HBM-NSFIX/SHARE2 10-18: lockstep of the pin-registered share2 (REG 1) vs the zero-latency share2 shifted +1 rq / +2 rr / +1 fault.
# usage: run_vm_share2_r.sh OUT_DIR MUT   (MUT 0 must PASS; 1..5 must FAIL). Verilator = the closure daemon's 5.050.
set -eu
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-share2r}"); m=${2:-0}; mkdir -p "$out"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
src=(rtl/hbm_accel/index/quad_1017/ot_hbm_idx_vm_share2_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v rtl/test/hbm_idx_static/tb_idx_vm_share2_r_lockstep.sv)
"$VL" --version
"$VL" --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module tb_idx_vm_share2_r_lockstep \
  -GMUT=$m -Mdir "$out/obj$m" -o sim "${src[@]}" > "$out/build$m.log" 2>&1 || { tail -30 "$out/build$m.log"; exit 3; }
set +e; "$out/obj$m/sim" > "$out/run$m.log" 2>&1; rc=$?; set -e
sha256sum "${src[@]}" > "$out/sources.sha256"
grep IDX_VM_SHARE2R "$out/run$m.log" || tail -5 "$out/run$m.log"
exit $rc
