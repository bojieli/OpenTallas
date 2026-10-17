#!/usr/bin/env bash
# args: OUT PIN_IN CDX
set -u
S=rtl/hbm_accel/generic/vm/static; O=$1; mkdir -p $O
iverilog -g2012 -s tb_vms_static_ring4_memory -Ptb_vms_static_ring4_memory.PIN_IN=$2 -Ptb_vms_static_ring4_memory.CDX=$3 -o $O/t.vvp $S/ot_vms_bank_static.sv $S/ot_vms_rstop_static.sv $S/ot_vms_rcl_static.sv $S/ot_vms_hub_static.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v $S/tb_vms_static_ring4_memory.sv > $O/c.log 2>&1 || { tail -5 $O/c.log; exit 2; }
vvp $O/t.vvp | tail -3
