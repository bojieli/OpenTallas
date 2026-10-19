#!/usr/bin/env bash
# run_ring4_packet_pin.sh OUT PIN_IN SHIFT
set -u
S=rtl/hbm_accel/generic/vm/static; O=$1; mkdir -p $O
iverilog -g2012 -s tb_vms_static_ring4_packet -Ptb_vms_static_ring4_packet.PIN_IN=$2 -Ptb_vms_static_ring4_packet.SHIFT=$3 -o $O/t.vvp $S/ot_vms_bank_static.sv $S/ot_vms_rstop_static.sv $S/ot_vms_rcl_static.sv $S/ot_vms_hub_static.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v $S/tb_vms_static_ring4_packet.sv > $O/c.log 2>&1 || { tail -5 $O/c.log; exit 2; }
vvp $O/t.vvp | grep -E "PASS|FATAL" | head -2
