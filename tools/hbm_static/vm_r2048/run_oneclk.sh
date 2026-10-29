#!/bin/bash
set -euo pipefail
O=${1:?fresh output root}
N=rtl/hbm_accel/generic/vm/static/faces_q0_r2048
G=tools/hbm_static/vm_r2048/golden
mkdir -p "$O"
for c in positive high_macro_clock_drop;do
 drop=0;test "$c" = positive || drop=1
 iverilog -g2012 -s tb_vm_r2048_oneclk -Ptb_vm_r2048_oneclk.DROP_CLOCK=$drop -o "$O/$c.vvp" "$G"/*.sv "$N"/*.sv rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v tools/hbm_static/vm_r2048/tb_oneclk.sv >"$O/$c.build.log" 2>&1
 rc=0;vvp "$O/$c.vvp" >"$O/$c.log" 2>&1||rc=$?
 if [ "$c" = positive ];then test "$rc" = 0;grep 'VM_R2048_ONECLK PASS' "$O/$c.log";else test "$rc" != 0;grep -q FATAL "$O/$c.log";echo 'ONECLK_MUTANT_CAUGHT high_macro_clock_drop';fi
done
verilator --lint-only --timing -Wno-fatal -Werror-WIDTH -Werror-SELRANGE --top-module hfd_vms_bank_native_q0_faces_r2048_oneclk "$N"/*.sv rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v >"$O/lint.log" 2>&1
echo 'ONECLK_WIDTH_SELRANGE_PASS'
