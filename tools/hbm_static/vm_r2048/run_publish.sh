#!/bin/bash
set -euo pipefail
O=${1:?};mkdir -p "$O";N=rtl/hbm_accel/generic/vm/static/faces_q0_r2048
for c in positive highbit mirror collision date;do
 mut=0;case "$c" in highbit)mut=1;;mirror)mut=2;;collision)mut=3;;date)mut=4;;esac
 iverilog -g2012 -s tb_publish -Ptb_publish.MUT=$mut -o "$O/$c.vvp" "$N"/*.sv rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v tools/hbm_static/vm_r2048/tb_publish.sv >"$O/$c.build.log" 2>&1
 rc=0;vvp "$O/$c.vvp" >"$O/$c.log" 2>&1||rc=$?
 if [ "$c" = positive ];then test "$rc" = 0;cat "$O/$c.log";else test "$rc" != 0;grep FATAL "$O/$c.log";echo "PUBLISH_MUTANT_CAUGHT $c";fi
done
verilator --lint-only -Wno-fatal -Werror-WIDTH -Werror-SELRANGE --top-module ot_vms_f20_boot_publish_r2048 rtl/lib/ot_rst_relay.sv "$N/ot_vms_f20_boot_publish_r2048.sv" >"$O/lint.log" 2>&1
echo PUBLISH_WIDTH_PASS
