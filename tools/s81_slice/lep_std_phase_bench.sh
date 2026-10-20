#!/bin/bash
set -eu
O=$1;HOST=${2:-1};M=${3:-none};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
D=();if [ "$M" != none ];then D=("+define+OT_S81SL_LEP_MUT_${M^^}");fi
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN "${D[@]}" -GHOST=$HOST --top-module tb_s81sl_lep_std_phase \
 rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_sram_oldread_wreg.sv rtl/lib/ot_sram_showahead_1r1w.sv rtl/lib/ot_rst_relay.sv \
 rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v \
 rtl/dsrom_sys/s81_dv/slice/test/ot_s81sl_lep_slice3_reference.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_lep_std_phase.sv \
 -Mdir "$O/obj" --build-jobs ${J:-2} -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > "$O/build.log" 2>&1
"$O/obj/Vtb_s81sl_lep_std_phase" > "$O/run.log" 2>&1
cat "$O/run.log"
