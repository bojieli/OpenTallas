#!/bin/bash
# struct-close 2026-10-09: TA15 body -cl lock-step vs the original composition.  run_ta15_lockstep.sh <out dir> <pos|neg> [seeds]
set -u
O=$1; M=$2; shift 2; mkdir -p $O; cd "$(dirname "$0")/../../.."
C=rtl/hbm_accel/control
sed 's/module ot_hbm_production_clock_control (/module ot_hbm_production_clock_control_ref (/' $C/ot_hbm_production_clock_control.sv > $O/ref_control.sv
D=""; [ "$M" = neg ] && D="-DOT_TA15_CL_MUT_NODROP"
rc=0
for s in ${@:-1 2 3}; do
  iverilog -g2012 $D -Ptb.SEED=$s -s tb -o $O/ls_${M}_${s}.vvp $C/ot_hbm_reset_seq.sv $C/ot_hbm_clock_reset_boundary.sv $O/ref_control.sv \
    $C/ot_hbm_clock_reset_collars_rs.sv $C/ot_hbm_production_clock_digital_body_cl.sv tests/rtl/struct_close/tb_ta15_body_lockstep.sv || exit 2
  L=$(vvp -n $O/ls_${M}_${s}.vvp | grep -m1 '^TA15_LOCKSTEP'); echo "seed $s: $L"
  case "$L" in *PASS*) ;; *) rc=1;; esac
done
exit $rc
