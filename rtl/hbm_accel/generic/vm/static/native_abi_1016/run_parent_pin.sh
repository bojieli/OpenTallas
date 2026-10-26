#!/usr/bin/env bash
# H-SM 2026-10-17: native parent bench with literal bank input pin flops.  run_parent_pin.sh OUT PIN_IN EXP_LAT
set -u
D=rtl/hbm_accel/generic/vm/static; O=$1; P=$2; E=${3:--1}; mkdir -p $O
M=physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
for shape in 0:5:2 1:4:2 2:5:3 3:4:2;do
 IFS=: read -r sid rg wg <<< "$shape"
 iverilog -g2012 -s tb_hbm_vm_native_parent -Ptb_hbm_vm_native_parent.SID=$sid -Ptb_hbm_vm_native_parent.RG=$rg -Ptb_hbm_vm_native_parent.WG=$wg -Ptb_hbm_vm_native_parent.PIN_IN=$P -Ptb_hbm_vm_native_parent.EXP_LAT=$E -o $O/q$sid.vvp $D/ot_vms_ce_counter_pipe.sv $D/ot_vms_bank_static_strap.sv $D/ot_vms_bank_native_physical.sv $D/ot_vms_slice_static.sv $D/hfd_hgi_vms_static.sv $D/ot_vms_hub_static.sv $D/ot_vms_rstop_static.sv $D/ot_vms_rcl_static.sv $D/ot_vms_status_static.sv $D/physical/hfd_vms_bank_native_q*.sv $D/wq_merge/hfd_vms_wq2_merge.sv $M $D/native_abi_1016/tb_hbm_vm_native_parent.sv > $O/q$sid.c.log 2>&1 || { echo "q$sid COMPILE FAIL"; tail -3 $O/q$sid.c.log; continue; }
 vvp $O/q$sid.vvp 2>&1 | grep -E "PASS|FATAL" | head -2 | sed "s/^/q$sid PIN_IN=$P: /"
done
