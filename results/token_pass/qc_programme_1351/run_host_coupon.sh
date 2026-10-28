#!/bin/bash
set -eu
E=/srv/opentallas-scratch2/claude/codex-qc-programme-1351
B=/srv/opentallas-scratch2/claude/codex-qc-bind-1027/fresh_v6
cd "$E"
python3 coupon/host_path_coupon.py "$B" source coupon/host_generated
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
for m in 0 1 2; do
 "$V" --binary --timing -j 1 -Wno-fatal -Wno-lint -Wno-style --top-module tb coupon/tb_host_path.sv coupon/host_generated/host_path_m$m.sv coupon/host_generated/bind_st.sv coupon/generated/dut_m0.sv -Mdir "$E/coupon/host_obj_m$m" > "$E/coupon/host_build_m$m.log" 2>&1
 set +e
 "$E/coupon/host_obj_m$m/Vtb" > "$E/coupon/host_run_m$m.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "$E/coupon/host_exit_m$m"
 if test "$m" = 0; then test "$rc" = 0; grep -q HOST_PATH_PASS "$E/coupon/host_run_m$m.log"; else test "$rc" != 0; grep -q HOST_PATH_FAIL "$E/coupon/host_run_m$m.log"; fi
 cat "$E/coupon/host_run_m$m.log"
done
