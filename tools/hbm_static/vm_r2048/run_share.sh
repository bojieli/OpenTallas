#!/bin/bash
set -euo pipefail
O=${1:?};mkdir -p "$O"
D=rtl/hbm_accel/index/quad_1017
for c in positive dropped_high;do
 mut=0;test "$c" = positive||mut=6
 iverilog -g2012 -s tb_share -Ptb_share.MUT=$mut -o "$O/$c.vvp" tools/hbm_static/vm_r2048/share_golden/legacy.sv "$D/ot_hbm_idx_vm_share2_static_r2048.sv" tools/hbm_static/vm_r2048/tb_share.sv >"$O/$c.build.log" 2>&1
 rc=0;vvp "$O/$c.vvp" >"$O/$c.log" 2>&1||rc=$?
 if [ "$c" = positive ];then test "$rc" = 0;cat "$O/$c.log";else test "$rc" != 0;grep FATAL "$O/$c.log";echo SHARE_MUTANT_CAUGHT;fi
done
verilator --lint-only -Wno-fatal -Werror-WIDTH -Werror-SELRANGE --top-module ot_hbm_idx_vm_share2_static_r_r2048 "$D/ot_hbm_idx_vm_share2_static_r2048.sv" >"$O/lint.log" 2>&1
echo SHARE_WIDTH_PASS
