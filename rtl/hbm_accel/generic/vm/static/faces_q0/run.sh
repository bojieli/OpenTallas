#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../../../../.."
D=rtl/hbm_accel/generic/vm/static/faces_q0
O=${1:?output dir required}
mkdir -p "$O"
src=("$D"/*.sv rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
for case in positive latency response clock_n clock_s clock_e clock_w;do
 lat=1;mut=0;drop=0
 case $case in latency)lat=0;;response)mut=1;;clock_n)drop=1;;clock_s)drop=2;;clock_e)drop=3;;clock_w)drop=4;;esac
 iverilog -g2012 -s tb_hbm_vm_q0_faces -Ptb_hbm_vm_q0_faces.EXPECT_INPUT_LAT=$lat -Ptb_hbm_vm_q0_faces.MUT=$mut -Ptb_hbm_vm_q0_faces.FACE_DROP=$drop -o "$O/$case.vvp" "${src[@]}" > "$O/$case.build.log" 2>&1
 rc=0;vvp "$O/$case.vvp" > "$O/$case.log" 2>&1||rc=$?
 if [[ $case = positive ]];then test "$rc" = 0;grep -q 'VM_NATIVE_ABI PASS' "$O/$case.log";else test "$rc" != 0;grep -q FATAL "$O/$case.log";fi
 echo "$case rc=$rc $(head -1 "$O/$case.log")"
done
echo 'Q0_FACE_CLOCKS BENCH PASS: actual 8 banks/24 SRAM; return7/write4; latency, response, and four independent clock-drop negatives rejected'
