#!/bin/bash
# HBMc/TOKEN3 10-22: P40 bench of ot_hbm_hc_q_static (qhub u_q) at the r18h S8b geometry RD_CAPTURE/GATHER_PHASE 39, DONE_LAT 35
# (GATHER_PERIOD 40) with a 16-edge return pad (tb_hbm_hc_q_static_p40 PAD), plus the 23/23/19 regression.
# Must: 39 MUT0 PASS; 39 MUT1-4 FAIL; phase/capture/done off-by-one and PAD 15 FAIL; 23 MUT0 PASS, MUT1-4 FAIL.
set -u; cd "$(dirname "$0")/../../../../.."; O=${OUT:-/tmp/hc_q_static_p40}; mkdir -p $O; rc=0
SRC="rtl/test/tb_hbm_hc_q_static_p40.sv rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_q_static.sv
 rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_residual_vm_static.sv rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_result_vm_static.sv
 rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_gathered_mix_reader_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_split_term.sv
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank_term.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_leaf.sv
 rtl/hdc/ot_hdc_delay.sv rtl/test/full_sm_service/sram_models.sv rtl/lib/ot_rst_relay.sv
 rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_xw_rx_static.sv"
one() { # PAD RDC GPH DNL MUT want
  local T=p$1_r$2_g$3_d$4_m$5 P=tb_hbm_hc_q_static_p40
  iverilog -g2012 -P $P.PAD=$1 -P $P.RDC=$2 -P $P.GPH=$3 -P $P.DNL=$4 -P $P.MUT=$5 -o $O/$T.vvp $SRC || { echo "$T COMPILE_FAIL"; rc=1; return; }
  local r=$(vvp -n $O/$T.vvp | grep TB_HBM_HC_Q_STATIC); echo "$r"; [[ "$r" == *$6* ]] || { echo "  ^ expected $6"; rc=1; }
}
for m in 0 1 2 3 4; do w=FAIL; [ $m = 0 ] && w=PASS; one 0 23 23 19 $m $w; one 16 39 39 35 $m $w; done
one 16 39 38 35 0 FAIL; one 16 39 40 35 0 FAIL; one 16 38 39 35 0 FAIL; one 16 39 39 34 0 FAIL; one 15 39 39 35 0 FAIL
[ $rc = 0 ] && echo "HC_Q_STATIC_P40 BENCH PASS" || echo "HC_Q_STATIC_P40 BENCH FAIL"; exit $rc
