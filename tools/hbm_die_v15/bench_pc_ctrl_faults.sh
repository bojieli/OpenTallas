#!/bin/bash
set -euo pipefail
out=${1:?out}; mut=${2:-none}; mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
p=results/rtl/hbm_harden_0811/fault_split
base=(rtl/lib/ot_rst_relay.sv rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v "$d/ot_hbm_svc_pc_ctrl_leaf.sv")
cp "$d/ot_hbm_svc_pc_ctrl_leaf_cfg_faults.sv" "$out/candidate.sv"
if [ "$mut" != none ];then
 sed -i "s/owner_fault_split\[$mut\]<=1;/owner_fault_split[$mut]<=0;/g" "$out/candidate.sv"
 if cmp -s "$out/candidate.sv" "$d/ot_hbm_svc_pc_ctrl_leaf_cfg_faults.sv";then echo MUTANT_NOT_APPLIED;exit 3;fi
fi
src=("${base[@]}" "$p/reference.sv" "$out/candidate.sv" "$p/miter_wrapper.sv")
iverilog -g2012 -s tb -o "$out/classes.vvp" "${src[@]}" "$d/tb_hbm_pc_ctrl_leaf_fault_classes.sv" > "$out/classes.build.log" 2>&1
vvp "$out/classes.vvp" > "$out/classes.log" 2>&1 || { cat "$out/classes.log";exit 1; }
cat "$out/classes.log"
if [ "$mut" != none ];then echo MUTANT_SURVIVED;exit 2;fi
iverilog -g2012 -s tb -o "$out/miter.vvp" "${src[@]}" "$d/tb_hbm_pc_ctrl_leaf_faults_miter.sv" > "$out/miter.build.log" 2>&1
vvp "$out/miter.vvp" > "$out/miter.log" 2>&1
cat "$out/miter.log";grep -q PC_CTRL_FAULTS_MITER\ PASS "$out/miter.log"
echo PC_CTRL_FAULTS_GATE_PASS
