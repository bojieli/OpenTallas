#!/bin/bash
# QC-TYPES-10/HC3: lock-step bench ot_qfd_xs_leaf_fo32 vs the hc3 leaf config ot_qfd_xs_leaf #(NCH4,READ_PIN_PIPE1,FILL_PIPE1,BANK_PIPE0)
# on the wave src (kw35/src_c303p); seeds 7/11/23 at NOPS 20000 + mutant MUT=2 (must FAIL)
set -u
S=/srv/opentallas-scratch2/claude/kw35/src_c303p; O=/srv/opentallas-scratch2/claude/qct10/hc3/bench
cd $S
for cfg in "s7:-GSEED=7 -GNOPS=20000" "s11:-GSEED=11 -GNOPS=20000" "s23:-GSEED=23 -GNOPS=20000" "mut2:-GMUT=2 -GSEED=7"; do
  n=${cfg%%:*}; a=${cfg#*:}
  JOBS=4 bash rtl/qwen_sys/dvm_20261014/run_xs_leaf_fo32.sh $O/$n $a; echo "RC $n $?"
done
md5sum rtl/qwen_sys/dvm_20261014/ot_qfd_xs_leaf_fo32.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/qwen_sys/dvm_20261014/tb_qfd_xs_leaf_fo32.sv
