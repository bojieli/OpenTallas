#!/bin/bash
# Leaf miter of ot_qfd_vm_xcol_t (PLAN 2026-10-13), run ON the build host inside a synced tree (never localhost):
#   ot-run --mem 28 --dir <tree> -- bash wt/tools/qwen_tp8/vm_xcol_leaf_miter.sh all
# one run: vm_xcol_leaf_miter.sh <name> [-G...]; `all` runs the recorded set in parallel into $B.
R=${VM_RTL_ROOT:-$(pwd)}; B=${VM_RTL_OUT:-$(cd "$R/.." && pwd)/xcol}; mkdir -p $B; cd "$R" || exit 9
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
one() { n=$1; shift
  $V --binary --timing -O1 --output-split 20000 --output-split-cfuncs 2000 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-BLKSEQ -Wno-LATCH -j 4 \
    --top-module tb_qfd_vm_xcol "$@" --Mdir $B/$n rtl/qwen_sys/vm_plane_20261013/tb_qfd_vm_xcol.sv \
    rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_xtree.sv rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_xplane.sv > $B/$n.build.log 2>&1 \
    || { echo "$n BUILD-FAIL $(grep -m3 -i error $B/$n.build.log | tr '\n' ' ')"; return 2; }
  /usr/bin/time -f "maxrss_kb=%M wall=%e" $B/$n/Vtb_qfd_vm_xcol > $B/$n.log 2>&1
  echo "$n args='$*' :: $(grep -E '^(PASS|FAIL)' $B/$n.log | head -1) $(grep maxrss $B/$n.log)"; }
if [ "$1" = all ]; then
  { one ok & one ok_s2 -GSEED=2 & for m in 1 2 3; do one pmut$m -GPMUT=$m & one lmut$m -GLMUT=$m & done
  one prod -GNRB=64 -GSMAX=11 -GCYCLES=1500 & one prod_lmut1 -GNRB=64 -GSMAX=11 -GCYCLES=1500 -GLMUT=1 &
  wait; } | sort | tee $B/summary.txt
else one "$@"; fi
