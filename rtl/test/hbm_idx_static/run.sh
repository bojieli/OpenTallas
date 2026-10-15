#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")"
out="${1:-/tmp/hbm-idx-static-proof}"
mkdir -p "$out"
for m in 0 1 2 3; do
  iverilog -g2012 -s tb_idx_vm_static -Ptb_idx_vm_static.MUT="$m" -o "$out/m$m.vvp" ot_hbm_idx_vm_static.sv ot_vms_bank_static.sv ot_sram_1r1w_1024x256_m2_r2c2.v tb_idx_vm_static.sv > "$out/build$m.log" 2>&1
  set +e
  vvp "$out/m$m.vvp" > "$out/run$m.log" 2>&1
  rc=$?
  set -e
  cat "$out/run$m.log"
  if [ "$m" = 0 ]; then test "$rc" = 0; else test "$rc" != 0; fi
done
