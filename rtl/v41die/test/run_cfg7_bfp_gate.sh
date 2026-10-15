#!/bin/bash
# run_cfg7_bfp_gate.sh <src root> <out dir>: exact gate of ot_s81_cfg7_seq_bfp (BF cfg sequencer + static programme
# producer, descriptor from the cfg ROM spare columns); the row mutant must FAIL.  (The producer arithmetic itself is
# gated in the real BF bench: tools/s81/bf_txn_bench.py --die-pair --static-prog, mutant OT_S81_BF_PROG_MUT_ADDR.)
set -u
SRC=$1; OUT=$2; mkdir -p $OUT
F="$SRC/rtl/v41die/ot_s81_cfg7_seq.sv $SRC/rtl/v41die/ot_s81_cfg7_seq_bfp.sv $SRC/rtl/dsrom_sys/s81_die_bind/ot_s81_bf_prog_seq.sv $SRC/rtl/v41die/test/tb_ot_s81_cfg7_seq_bfp.sv"
v=PASS
run() { l=$1; want=$2; shift 2
  iverilog -g2012 -s tb_ot_s81_cfg7_seq_bfp "$@" -o $OUT/$l.vvp $F > $OUT/build_$l.log 2>&1 || { echo "$l BUILD_FAIL"; cat $OUT/build_$l.log | head; v=FAIL; return; }
  vvp $OUT/$l.vvp > $OUT/run_$l.log 2>&1
  if grep -q "^PASS" $OUT/run_$l.log; then got=PASS; else got=FAIL; fi
  echo "$l $got (want $want): $(grep -E '^PASS|MISMATCH|fault' $OUT/run_$l.log | head -1 | cut -c1-200)"
  [ $got = $want ] || v=FAIL
}
run base PASS
run mut_row FAIL -DOT_S81_CFG7_BFP_MUT_ROW
echo "CFG7_BFP_GATE $v"; [ $v = PASS ]
