#!/bin/bash
set -euo pipefail
O=${1:?};mkdir -p "$O"
S=rtl/hbm_accel/host_static_20261015/ot_hbm_static_cfg_collar_idx256r_r2048.sv
for c in fan0 fan1 badrole reserved;do
 fan=1;mut=0;case "$c" in fan0)fan=0;;badrole)mut=15;;reserved)mut=12;;esac
 iverilog -g2012 -s tb_collar -Ptb_collar.FAN=$fan -Ptb_collar.MUT=$mut -o "$O/$c.vvp" "$S" tools/hbm_static/vm_r2048/collar_golden/legacy.sv tools/hbm_static/vm_r2048/tb_collar.sv >"$O/$c.build.log" 2>&1
 rc=0;vvp "$O/$c.vvp" >"$O/$c.log" 2>&1||rc=$?
 case "$c" in fan*)test "$rc" = 0;cat "$O/$c.log";;*)test "$rc" != 0;grep FATAL "$O/$c.log";echo "COLLAR_MUTANT_CAUGHT $c";;esac
done
verilator --lint-only --timing -Wno-fatal -Werror-WIDTH -Werror-SELRANGE --top-module ot_hbm_static_cfg_collar_idx256r_r2048 -GFAN32=1 "$S" >"$O/lint.log" 2>&1
echo COLLAR_WIDTH_PASS
