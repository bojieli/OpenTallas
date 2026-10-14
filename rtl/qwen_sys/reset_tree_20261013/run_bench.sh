#!/bin/bash
# reset tree bench + mutants (iverilog), run in REMOTE_DIR/rtl
cd "$(dirname "$0")"
for v in "base" "MUT_ROOT=1" "MUT_ROOT=2" "MUT_REP=1"; do
  d=""; [ "$v" != base ] && d="-D$v"
  iverilog -g2012 $d -o tb_$$.vvp tb_ot_qwen_rst_tree.sv ot_qwen_rst_root.sv ot_qwen_rst_rep.sv && echo "== $v: $(vvp tb_$$.vvp | grep -E 'PASS|FAIL|ERR' | head -3 | tr '\n' ' ')"
done
rm -f tb_$$.vvp
