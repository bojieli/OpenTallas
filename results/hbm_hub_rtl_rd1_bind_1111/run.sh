#!/bin/bash
# usage: run.sh WT OUTDIR ; gold body = a918972c^ (pre-rd1), rd1 body = main
set -u; cd /  # results/hbm_hub_rtl_rd1_bind_1111/run.sh WORKTREE OUTDIR (copy tb_rd1_lg_rt.sv into OUTDIR first)
W=$1; O=$2; mkdir -p $O; cd $O
git -C $W show a918972c20^:rtl/hbm_accel/generic/vm/static/faces_q0/ot_vms_bank_q0_faces_body.sv > body_main_prerd1.sv
cp $W/rtl/hbm_accel/generic/vm/static/faces_q0/ot_vms_bank_q0_faces_body.sv body_rd1.sv
COMMON="$W/rtl/hbm_accel/generic/vm/static/faces_q0/hfd_vms_bank_native_q0_faces.sv $W/rtl/hbm_accel/generic/vm/static/faces_q0/ot_vms_bank_q0_faces_core.sv $W/rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv $W/rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv $W/rtl/test/full_sm_service/sram_models.sv"
sha256sum body_main_prerd1.sv body_rd1.sv $O/tb_rd1_lg_rt.sv > inputs.sha256
for c in "prerd1 11 pos" "prerd1 10 neg-1" "prerd1 12 neg+1" "rd1 12 pos" "rd1 11 neg+0" "rd1 13 neg+2"; do
  set -- $c; b=$1; rr=$2; tag=$3
  iverilog -g2012 -o sim_${b}_$rr -P tb.RR=$rr -s tb tb_rd1_lg_rt.sv body_$([ $b = rd1 ] && echo rd1 || echo main_prerd1).sv $COMMON > build_${b}_$rr.log 2>&1 || { echo "$b RR=$rr BUILD FAIL"; tail -5 build_${b}_$rr.log; continue; }
  vvp -n sim_${b}_$rr > sim_${b}_$rr.log 2>&1
  echo "$b $tag $(grep -h 'RESULT\|VERDICT' sim_${b}_$rr.log | tr '\n' ' ')"
done
