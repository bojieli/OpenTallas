#!/bin/bash
# DIE-HBM-61/RTL-C3: ot_hgi_coll_static_seq_ctl RXPRE=1 vs origin/main lockstep + killing mutants (iverilog, ulimit -v).
# Usage: run_seq_eq.sh REPO WORKDIR
set -u
R=$1; W=$2; mkdir -p $W; cd $R
P=rtl/hbm_accel/generic/collective/p2p
git show origin/main:$P/ot_hgi_coll_static_seq_ctl.sv | sed 's/^module ot_hgi_coll_static_seq_ctl /module ot_hgi_coll_static_seq_ctl_old /' > $W/old.sv
ulimit -v 8000000
rc=0
run() { # name expect defines...
  n=$1; e=$2; shift 2
  iverilog -g2012 -s tb_c3_seq_ctl_rxpre_eq -o $W/$n.vvp "$@" tests/hbm_b2/c3_reform/tb_c3_seq_ctl_rxpre_eq.sv $W/old.sv \
    $P/ot_hgi_coll_static_seq_ctl.sv rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv > $W/$n.compile.log 2>&1 \
    || { echo "$n COMPILE_FAIL"; head -5 $W/$n.compile.log; rc=1; return; }
  timeout 3000 vvp -n $W/$n.vvp > $W/$n.log 2>&1; r=$(grep C3_SEQ_EQ $W/$n.log)
  case "$e:$r" in pass:*PASS*|fail:*FAIL*) echo "$n OK expect=$e :: $r";; *) echo "$n BAD expect=$e :: $r"; rc=1;; esac
}
run pos_s11 pass
run pos_s5 pass -Ptb_c3_seq_ctl_rxpre_eq.SEED=5
for m in RX_BIT RX_STALE RX_NOREG; do run mut_$m fail -DC3MUT_$m; done
echo "OVERALL rc=$rc"; exit $rc
