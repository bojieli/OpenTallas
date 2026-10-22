#!/bin/bash
set -euo pipefail
D=${1:?output}; IMPL=${2:-sram}; MUT=${3:-none};mkdir -p "$D"
defs=();[ "$IMPL" != sram ] || defs+=(-DS81CTRL_SRAM_FIFO)
[ "$MUT" = none ] || defs+=("-D$(if [ "$MUT" = PACK ];then echo S81PH_MUT_PACK;else echo S81CTRL_MUT_$MUT;fi)")
verilator --binary --timing -j 4 --top-module tb_ctrl_pcr_min -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN "${defs[@]}" --Mdir "$D/obj" \
 rtl/dsrom_sys/s81_ph/ctrl/test/tb_ctrl_pcr_min.sv rtl/dsrom_sys/s81_ph/ctrl/test/ctrl_pcr_ref_05689.sv \
 rtl/dsrom_sys/s81_ph/ctrl/dsfd_ctrl_rg2.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv \
 rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_ctrl_pcr.sv rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g.sv rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g_sram.sv rtl/dsrom_sys/s81_ph/ot_s81ph_afifo.sv \
 physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1.v >"$D/build.log" 2>&1
set +e
"$D/obj/Vtb_ctrl_pcr_min" >"$D/run.log" 2>&1
rc=$?
set -e
printf '%s\n' "$rc" >"$D/exit_code"
cat "$D/run.log"
if [ "$MUT" = none ];then [ "$rc" = 0 ] && grep -q 'CTRL_PCR_MIN PASS' "$D/run.log";else [ "$rc" != 0 ] && grep -q 'CTRL_PCR_MIN FAIL' "$D/run.log";fi
