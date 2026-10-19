#!/bin/bash
# HBM-RTL5 10-18: HC ring lockstep, d4g U-ring form (XRLY die relay on b7->b0). Usage: bench.sh TAG MUT "DEFS" CASE:OUT ...
set -u
R=$(cd "$(dirname "$0")" && pwd); O=$R/out; mkdir -p $O; T=$1; M=$2; D=$3; shift 3
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
V(){ echo "$(date -Is) $*" >> $O/verdict_$T.txt; }
V "start host=$(hostname) tag=$T mut=$M defs=$D"
d=$R/obj_$T; rm -rf $d
( cd $R/src && verilator --binary --timing --hierarchical -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
    --top-module tb_hbm_hc_eng4_static +define+MUT=$M +define+OT_FP_DATA_NORST $D -Mdir $d -o V$T \
    rtl/test/tb_hbm_hc_eng4_static_hier.vlt $(cat $R/split.f) ) > $O/build_$T.log 2>&1
V "build $T rc=$? bin=$( [ -x $d/V$T ] && echo ok || echo MISSING)"
for c in "$@"; do
  cs=${c%%:*}; ot=${c##*:}; od=$O/$ot; rm -rf $od; cp -r $R/cases/$cs $od
  ( cd $od && $d/V$T $(cat plus.txt) > run.log 2>&1; echo RUN_RC=$? >> run.log
    grep -h "HC_ENG_DONE\|HC_ENG PASS\|HC_ENG FAIL\|FAULT\|MISMATCH\|watchdog\|RUN_RC\|PROBE raw" run.log | head -8 | sed "s|^|  $ot: |" >> $O/verdict_$T.txt ) &
done
wait
rm -rf $d
V "done $T"
