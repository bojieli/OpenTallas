#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../../../../.."
D=rtl/hbm_accel/generic/vm/static/faces_q2
O=${1:?output dir required}
mkdir -p "$O"
src=("$D"/*.sv rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
# OT_POS_DROP=<n> is the fail-mutant hook: the positive case runs with clock entry n held low (5..7 = clk_macro0..2).
for case in ${OT_CASES:-positive latency response clock_n clock_s clock_e clock_w clock_m0 clock_m1 clock_m2};do
 lat=1;mut=0;drop=0
 case $case in positive)drop=${OT_POS_DROP:-0};;latency)lat=0;;response)mut=1;;clock_n)drop=1;;clock_s)drop=2;;clock_e)drop=3;;clock_w)drop=4;;clock_m0)drop=5;;clock_m1)drop=6;;clock_m2)drop=7;;esac
 iverilog -g2012 -s tb_hbm_vm_q2_faces -Ptb_hbm_vm_q2_faces.EXPECT_INPUT_LAT=$lat -Ptb_hbm_vm_q2_faces.MUT=$mut -Ptb_hbm_vm_q2_faces.FACE_DROP=$drop -o "$O/$case.vvp" "${src[@]}" > "$O/$case.build.log" 2>&1
 rc=0;vvp "$O/$case.vvp" > "$O/$case.log" 2>&1||rc=$?
 echo "$case drop=$drop rc=$rc $(head -1 "$O/$case.log")"
 if [[ $case = positive ]];then
  if [[ $rc != 0 ]] || ! grep -q 'VM_NATIVE_ABI PASS' "$O/$case.log";then echo "Q2_FACE_CLOCKS BENCH FAIL: positive rejected (drop=$drop)";exit 1;fi
 else
  if [[ $rc = 0 ]] || ! grep -q FATAL "$O/$case.log";then echo "Q2_FACE_CLOCKS BENCH FAIL: negative $case accepted";exit 1;fi
 fi
done
echo "Q2_FACE_CLOCKS BENCH PASS: cases=${OT_CASES:-all10} actual 8 banks/24 SRAM; return7/write4; latency, response, four face-clock and three direct SRAM clk_macro drops rejected"
