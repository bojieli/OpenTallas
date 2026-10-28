#!/bin/bash
set -eu
E=/srv/opentallas-scratch2/claude/codex-qc-programme-1351
cd "$E"
python3 coupon/native_prepare_coupon.py source coupon/generated
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
for m in 0 1 2; do
 "$V" --binary --timing -j 1 -Wno-fatal -Wno-lint -Wno-style --top-module tb coupon/tb_native_prepare.sv coupon/generated/dut_m$m.sv -Mdir "$E/coupon/obj_m$m" > "$E/coupon/build_m$m.log" 2>&1
 set +e
 "$E/coupon/obj_m$m/Vtb" > "$E/coupon/run_m$m.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "$E/coupon/exit_m$m"
 if test "$m" = 0; then test "$rc" = 0; grep -q PREP_PASS "$E/coupon/run_m$m.log"; else test "$rc" != 0; grep -q PREP_FAIL "$E/coupon/run_m$m.log"; fi
 cat "$E/coupon/run_m$m.log"
done
