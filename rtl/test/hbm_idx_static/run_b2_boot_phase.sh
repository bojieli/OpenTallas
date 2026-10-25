#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.."&&pwd);cd "$root"
out=$(realpath -m "${1:?out}");mkdir -p "$out"
for m in 0 1 2;do
 iverilog -g2012 -s tb_hbm_b2_boot_phase -Ptb_hbm_b2_boot_phase.MUT=$m -o "$out/m$m.vvp" rtl/hbm_accel/loader/service_native/ot_hbm_b2_boot_phase.sv rtl/test/hbm_idx_static/tb_hbm_b2_boot_phase.sv > "$out/build$m.log" 2>&1
 set +e
 vvp "$out/m$m.vvp" > "$out/run$m.log" 2>&1;rc=$?
 set -e
 if [ "$m" = 0 ];then [ "$rc" = 0 ] || { cat "$out/run$m.log";exit 1; };else [ "$rc" != 0 ] || { echo "MUTANT_NOT_CAUGHT $m";exit 1; };fi
 tail -2 "$out/run$m.log"
done
echo 'B2_BOOT_PHASE_GATE PASS'
