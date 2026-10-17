#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs
src=(ot_vms_ce_counter_pipe.sv ot_vms_bank_static_strap.sv ot_vms_bank_native_physical.sv q0_core_renamed.sv q1_core_renamed.sv q2_core_renamed.sv ot_sram_1r1w_1024x256_m2_r2c2.v tb_hbm_vm_native_nat2_exact.sv)
for sid in 0 1 2 3;do
 if ((sid==0));then rg=5;wg=2;elif ((sid==2));then rg=5;wg=3;else rg=4;wg=2;fi
 for case in positive latency identity clock_drop;do
  mut=0;lat=1
  if [[ $case == latency ]];then lat=0;elif [[ $case == identity ]];then mut=3;elif [[ $case == clock_drop ]];then mut=5;fi
  iverilog -g2012 -s tb_hbm_vm_native_nat2_exact -Ptb_hbm_vm_native_nat2_exact.SID=$sid -Ptb_hbm_vm_native_nat2_exact.RG=$rg -Ptb_hbm_vm_native_nat2_exact.WG=$wg -Ptb_hbm_vm_native_nat2_exact.MUT=$mut -Ptb_hbm_vm_native_nat2_exact.EXPECT_INPUT_LAT=$lat -o "logs/s${sid}_${case}.vvp" "${src[@]}" q0_wrapper.v q1_wrapper.v q2_wrapper.v > "logs/s${sid}_${case}.build.log" 2>&1
  rc=0;vvp "logs/s${sid}_${case}.vvp" > "logs/s${sid}_${case}.log" 2>&1||rc=$?
  if [[ $case == positive ]];then test "$rc" = 0;grep -q 'VM_NATIVE_ABI PASS' "logs/s${sid}_${case}.log"
  else test "$rc" != 0;grep -q FATAL "logs/s${sid}_${case}.log";fi
  echo "SID=$sid RG=$rg WG=$wg CASE=$case rc=$rc $(head -1 "logs/s${sid}_${case}.log")"
 done
done
iverilog -g2012 -s tb_hbm_vm_native_nat2_exact -Ptb_hbm_vm_native_nat2_exact.SID=1 -Ptb_hbm_vm_native_nat2_exact.RG=4 -Ptb_hbm_vm_native_nat2_exact.WG=2 -o logs/slot_mut.vvp "${src[@]}" q0_wrapper.v q1_wrapper_slot_mut.v q2_wrapper.v > logs/slot_mut.build.log 2>&1
rc=0;vvp logs/slot_mut.vvp > logs/slot_mut.log 2>&1||rc=$?
test "$rc" != 0;grep -q FATAL logs/slot_mut.log
echo "NONUNIFORM_SLOT_MUTANT rejected $(head -1 logs/slot_mut.log)"
