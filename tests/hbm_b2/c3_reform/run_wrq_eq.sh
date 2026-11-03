#!/bin/bash
# DIE-HBM-61/RTL-C3: wrq lanes_n new-vs-old lockstep + mutants (iverilog, memory capped by ulimit)
set -u
R=$1; W=$2; mkdir -p $W; cd $W
git -C $R show origin/main:rtl/hbm_accel/generic/vm/static/ot_hbm_sm_vm_wr_q_lanes_n.sv | sed 's/module ot_hbm_sm_vm_wr_q_lanes_n /module ot_hbm_sm_vm_wr_q_lanes_n_old /' > old.sv
NEW=$R/rtl/hbm_accel/generic/vm/static/ot_hbm_sm_vm_wr_q_lanes_n.sv
TB=$R/tests/hbm_b2/c3_reform/tb_c3_wrq_lanes_n_eq.sv
ulimit -v 8000000
rc=0
run() { tag=$1; exp=$2; shift 2; iverilog -g2012 -o $tag.vvp "$@" -s tb_c3_wrq_lanes_n_eq $NEW old.sv $TB > $tag.comp 2>&1 || { echo "$tag COMPILE_FAIL"; cat $tag.comp | head -5; rc=1; return; }
  vvp -n $tag.vvp > $tag.log 2>&1; r=$?; line=$(grep C3_WRQ_EQ $tag.log | tail -n 1); e=$(grep -c MISMATCH $tag.log)
  if [ $exp = pass ]; then [ $r = 0 ] && [ -n "$line" ] && st=OK || { st=BAD; rc=1; }; else [ $r != 0 ] && st=OK || { st=BAD; rc=1; }; fi
  echo "$tag expect=$exp rc=$r $st: $line mism_lines=$e"; }
run pos_nl4 pass -Ptb_c3_wrq_lanes_n_eq.NL=4 -Ptb_c3_wrq_lanes_n_eq.NB2=2 -Ptb_c3_wrq_lanes_n_eq.LBPIN=1
run pos_nl4_s2 pass -Ptb_c3_wrq_lanes_n_eq.NL=4 -Ptb_c3_wrq_lanes_n_eq.NB2=2 -Ptb_c3_wrq_lanes_n_eq.SEED=7
run pos_nl8 pass -Ptb_c3_wrq_lanes_n_eq.NL=8 -Ptb_c3_wrq_lanes_n_eq.NB2=1 -Ptb_c3_wrq_lanes_n_eq.LBPIN=0
for m in LASTCUR DPN CNTN POPE0 WSEL EMITC; do run mut_$m fail -DC3MUT_$m -Ptb_c3_wrq_lanes_n_eq.NL=4 -Ptb_c3_wrq_lanes_n_eq.NB2=2; done
echo "OVERALL rc=$rc"; exit $rc
