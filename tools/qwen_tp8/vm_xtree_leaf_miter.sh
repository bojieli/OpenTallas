#!/bin/bash
# Leaf miter of ot_qfd_vm_xtree.sv, run ON the build host inside a synced tree (never localhost):
#   ssh ot-epyc1tb 'cd ~/claude-vm-rtl-1013/L/wt && ot-heavy --mem 96 -- bash -c "tools/qwen_tp8/vm_xtree_leaf_miter.sh all < /dev/null"'
# (16 parallel builds: under --mem 16 / 24 the builds are killed, leaving EMPTY build logs and no result line)
# one run: vm_xtree_leaf_miter.sh <name> [-G...]; `all` runs the recorded set in parallel into ../b.
B=${B:-$(cd .. && pwd)/b}; mkdir -p $B
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
one() { n=$1; shift
  $V --binary --timing -O1 --output-split 20000 --output-split-cfuncs 2000 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-BLKSEQ -j 8 \
    --top-module tb_qfd_vm_xtree "$@" --Mdir $B/$n rtl/qwen_sys/vm_plane_20261013/tb_qfd_vm_xtree.sv \
    rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_xtree.sv rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_xplane.sv > $B/$n.build.log 2>&1 \
    || { echo "$n BUILD-FAIL $(grep -m3 -i error $B/$n.build.log | tr '\n' ' ')"; return 2; }
  /usr/bin/time -f "maxrss_kb=%M wall=%e" $B/$n/Vtb_qfd_vm_xtree > $B/$n.log 2>&1
  echo "$n args='$*' :: $(grep -E '^(PASS|FAIL)' $B/$n.log | head -1) $(grep maxrss $B/$n.log)"; }
if [ "$1" = all ]; then
  one ok & one ok_s2 -GSEED=2 & one ok_k1 -GK=1 -GXQR=0 & one ok_k2 -GK=2 -GXQR=1 & one ok_k4 -GK=4 -GXQR=5 & one ok_mereg0 -GMEREG=0 &
  for m in 1 2 3 4 5 6 7; do one mut$m -GXMUT=$m & done
  one prod -GNRB=64 -GSMIN=7 -GSMAX=11 -GCYCLES=3000 & one prod_mut1 -GNRB=64 -GSMIN=7 -GSMAX=11 -GCYCLES=3000 -GXMUT=1 &
  one prod_mut3 -GNRB=64 -GSMIN=7 -GSMAX=11 -GCYCLES=3000 -GXMUT=3 &
  wait
else one "$@"; fi
