#!/usr/bin/env bash
set -eu
mkdir -p out_fourstate
python3 tools/s81_dv/lep_hierarchy_1019/iverilog_portable.py
iverilog -g2012 -s tb_lep_hierarchy_4state -o out_fourstate/sim rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_rst_relay.sv out_fourstate/ot_sram_oldread_wreg.sv out_fourstate/ot_sram_showahead_1r1w.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v out_fourstate/ot_s81sl_slice_lep.sv tools/s81_dv/lep_hierarchy_1019/tb_lep_hierarchy_4state.sv
vvp out_fourstate/sim
