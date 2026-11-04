#!/bin/bash
# DIE-HBM-61/CUTS q2_reduce LREP lockstep EQ + mutants (iverilog). Usage: run_eq.sh REPO GOLD_REV OUT
set -u; R=$1; G=$2; O=$3; mkdir -p $O; P=$R/rtl/hbm_accel/generic/collective/p2p
for m in ot_hgi_coll_reduce_static ot_hgi_coll_reduce_static_pr; do
  git -C $R show $G:rtl/hbm_accel/generic/collective/p2p/$m.sv | sed 's/\bot_hgi_coll_reduce_static/gold_ot_hgi_coll_reduce_static/g' > $O/gold_$m.sv; done
L="$R/rtl/hdc/ot_hdc_fastfp.sv $R/rtl/hdc/ot_hdc_prefix.sv $R/rtl/hdc/ot_hdc_fp32_add_lat.sv $P/ot_hgi_coll_pring_static.sv"
for M in 0 1 2 3 4; do
  D="-DOT_HBM_REDUCE_LREP"; [ $M = 0 ] || D="$D -DOT_HBM_REDUCE_LMUT=$M"
  iverilog -g2012 $D -o $O/sim$M $R/results/hbm_cuts_1103/q2_reduce/tb_q2_reduce_lrep.sv $O/gold_*.sv $L \
    $P/ot_hgi_coll_reduce_static.sv $P/ot_hgi_coll_reduce_static_lr.sv $P/ot_hgi_coll_reduce_static_pr.sv 2>&1 | grep -iv warn | head -5
  ( timeout ${SIM_T:-5400} vvp -n $O/sim$M > $O/run$M.log 2>&1; rc=$?; echo "LMUT=$M rc=$rc $(grep LREP_EQ $O/run$M.log | grep -v MISMATCH | tail -1)" ) &
done
wait
