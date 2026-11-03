#!/bin/bash
# DIE-HBM-61 RE-FORM C3: lockstep EQ of hfd_hgi_vm_calendar_f20 (FREE_PAYLOAD) vs origin/main, plus killing mutants.
# Usage: run_cal_eq.sh REPO WORKDIR   (run on a fleet host; iverilog under ulimit -v)
set -u
R=$1; W=$2; mkdir -p $W; cd $R
S=rtl/hbm_accel/generic/vm/static
git show origin/main:$S/ot_static_program_target.sv | sed 's/\bot_static_program_target\b/ot_static_program_target_old/g;s/\bot_static_target_descriptor_byte\b/ot_static_target_descriptor_byte_old/g' > $W/old_tgt.sv
git show origin/main:$S/hfd_hgi_vm_calendar_f20.sv | sed 's/\bhfd_hgi_vm_calendar_f20\b/hfd_hgi_vm_calendar_f20_old/;s/\bot_static_program_target\b/ot_static_program_target_old/' > $W/old_f20.sv
DEPS="$S/hfd_hgi_vm_calendar.sv $S/ot_vms_calendar_static_xcap.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
ulimit -v 8000000
run() { # name defines seed expect
  iverilog -g2012 -s tb_c3_cal_f20_eq -o $W/$1.vvp $2 -Ptb_c3_cal_f20_eq.SEED=$3 tests/hbm_b2/c3_reform/tb_c3_cal_f20_eq.sv $W/old_tgt.sv $W/old_f20.sv \
    $S/ot_static_program_target.sv $S/hfd_hgi_vm_calendar_f20.sv $DEPS > $W/$1.compile.log 2>&1 || { echo "$1 COMPILE_FAIL"; tail -5 $W/$1.compile.log; return; }
  timeout 1800 vvp -n $W/$1.vvp > $W/$1.log 2>&1
  r=$(grep -o "C3_CAL_EQ [A-Z]* errors=[0-9]*" $W/$1.log)
  case "$4:$r" in pass:*PASS*|fail:*FAIL*) echo "$1 OK expect=$4 :: $(grep C3_CAL_EQ $W/$1.log)";; *) echo "$1 BAD expect=$4 :: $r"; tail -3 $W/$1.log;; esac
}
run pos_s7 "" 7 pass
run pos_s3 "" 3 pass
run mut_raw -DC3MUT_CAL_RAW 7 fail
run mut_hold -DC3MUT_CAL_HOLD 7 fail
run mut_addr -DC3MUT_CAL_ADDR 7 fail
run mut_scanc -DC3MUT_CAL_SCANC 7 fail
