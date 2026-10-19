#!/usr/bin/env bash
# Run only on an admitted fleet host. Execute in a source-pinned input directory.
set -eu
sources=(tb_component.sv qkd_d2d_firstepoch_component.sv qkd_d2d_cal_seq_pin_bc_fe.sv ot_qwen_d2d_cal_sf_fe.sv qkd_static_kv_boot_dispatch.sv qkd_d2d_cal_seq_bootcfg.sv ot_qwen_d2d_cal_seq.sv ot_qwen_d2d_cal_seq_dies_mu.sv current_safe_fo.sv)
sha256sum "${sources[@]}" d2d_cal_image_mu.svh > source.sha256
iverilog -V > iverilog_version.log 2>&1
verilator --version > verilator_version.log
iverilog -g2012 -s tb_component -I . -o bench "${sources[@]}" > compile.log 2>&1
failure=0
for m in 0 1 2 3 4 5 6 7 8 9 11 12 13 14 15 17; do
 set +e
 vvp bench +MODE="$m" > "mode$m.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "mode$m.rc"
 if ((rc)); then failure=1; fi
 tail -5 "mode$m.log"
done
verilator --binary --timing --top-module tb_component -Wno-fatal -j 2 -I. --Mdir obj_binary "${sources[@]}" > binary_compile.log 2>&1
for m in 0 1 2 3 4 5 6 7 8 9 11 13 14 15 16 17; do
 set +e
 obj_binary/Vtb_component +MODE="$m" > "binary_mode$m.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "binary_mode$m.rc"
 if ((rc)); then failure=1; fi
 tail -5 "binary_mode$m.log"
done
exit "$failure"
