#!/bin/bash
# DIE-HBM-61/CUTS 11-03: cp_rxs CRCSPLIT lockstep EQ (link_capture CRCSPLIT=1 vs the base commit form, 0 cycles) +
# codec mutants CMUT 1..3 (must FAIL).  Run from the repo root: results/hbm_cuts_1103/cprxs/run_eq.sh [CYC] [BASE]
set -u
CYC=${1:-200000}; BASE=${2:-3465966986}
O=${OUT:-results/hbm_cuts_1103/cprxs/eq_out}; mkdir -p "$O"
H=rtl/hbm_accel/host_ep_20261018; P=rtl/hbm_accel/generic/collective/p2p
G=$O/gold_link.sv
[ -s $G ] || { git show $BASE:$H/ot_hbm_host_link_capture.sv; git show $BASE:$P/ot_hgi_coll_static_seq_ctl.sv; } \
 | sed -E 's/\b(ot_hbm_host_link_capture|ot_hbm_host_link_pinreg_ctl|ot_hgi_coll_static_seq_ctl)\b/gold_\1/g' > $G
F="results/hbm_cuts_1103/cprxs/tb_link_capture_crcsplit.sv $G $H/ot_hbm_host_link_capture.sv $P/ot_hgi_coll_static_seq_ctl.sv
 $P/ot_hgi_coll_static_pinreg_store.sv rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
rc=0
for m in 0 1 2 3; do
 iverilog -g2012 -DOT_MEM_NO_INIT -s tb -Ptb.CMUT=$m -Ptb.CYC=$CYC -o $O/sim$m $F > $O/build$m.log 2>&1 || { tail $O/build$m.log; echo BUILD_FAIL $m; rc=2; continue; }
 vvp -n $O/sim$m > $O/run$m.log 2>&1; grep CRCSPLIT_EQ $O/run$m.log
 if [ $m = 0 ]; then grep -q "CRCSPLIT_EQ PASS" $O/run$m.log || rc=1; else grep -q "CRCSPLIT_EQ FAIL" $O/run$m.log || rc=1; fi
done
exit $rc
