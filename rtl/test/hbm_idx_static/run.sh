#!/usr/bin/env bash
set -eu
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out="${1:-/tmp/hbm-idx-static-proof}"
mkdir -p "$out"
for m in 0 1 2 3; do
  iverilog -g2012 -s tb_idx_vm_static -Ptb_idx_vm_static.MUT="$m" -o "$out/m$m.vvp" rtl/hbm_accel/index/ot_hbm_idx_vm_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v rtl/test/hbm_idx_static/tb_idx_vm_static.sv > "$out/build$m.log" 2>&1
  set +e
  vvp "$out/m$m.vvp" > "$out/run$m.log" 2>&1
  rc=$?
  set -e
  cat "$out/run$m.log"
  if [ "$m" = 0 ]; then test "$rc" = 0; else test "$rc" != 0; fi
done
