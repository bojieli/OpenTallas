#!/usr/bin/env bash
# IDX read-group share (4 bank-pair leaves) gate: MUT0 PASS, MUT1 (owner one edge short) and MUT2 (double booking passed) FAIL.
set -eu
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-share}"); mkdir -p "$out"; rc_all=0
src=(rtl/hbm_accel/index/ot_hbm_idx_vm_share_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v rtl/test/hbm_idx_static/tb_idx_vm_share_static.sv)
for m in 0 1 2; do
  iverilog -g2012 -s tb_idx_vm_share_static -Ptb_idx_vm_share_static.MUT=$m -o "$out/m$m.vvp" "${src[@]}" > "$out/build$m.log" 2>&1
  set +e; vvp "$out/m$m.vvp" > "$out/run$m.log" 2>&1; rc=$?; set -e
  grep IDX_VM_SHARE "$out/run$m.log" || tail -3 "$out/run$m.log"
  if [ $m = 0 ]; then [ $rc = 0 ] || rc_all=1; else [ $rc != 0 ] || { echo "MUT$m NOT KILLED"; rc_all=1; }; fi
done
sha256sum "${src[@]}" > "$out/sources.sha256"
[ $rc_all = 0 ] && echo "IDX_VM_SHARE GATE PASS" || { echo "IDX_VM_SHARE GATE FAIL"; exit 1; }
