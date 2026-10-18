#!/bin/bash
# HBM-B-RTL2 HC split lockstep chain: builds orig m0, split m0/m1/m4 (Verilator 5.050 --hierarchical), runs cases.
set -u
R=$(cd "$(dirname "$0")" && pwd); O=$R/out2; mkdir -p $O
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
V(){ echo "$(date -Is) $*" >> $O/verdict.txt; }
V "chain start host=$(hostname)"
build(){ # name tbtop filelist mut vlt
  local d=$R/obj_$1; rm -rf $d
  ( cd $R/src && verilator --binary --timing --hierarchical -j 32 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
      --top-module $2 +define+MUT=$4 +define+OT_FP_DATA_NORST -Mdir $d -o V$1 rtl/test/$5 $(cat $R/$3) ) > $O/build_$1.log 2>&1
  V "build $1 rc=$? bin=$( [ -x $d/V$1 ] && echo ok || echo MISSING)"
}

build s0 tb_hbm_hc_eng4_static split.f 0 tb_hbm_hc_eng4_static_hier.vlt &
build s1 tb_hbm_hc_eng4_static split.f 1 tb_hbm_hc_eng4_static_hier.vlt &
build s4 tb_hbm_hc_eng4_static split.f 4 tb_hbm_hc_eng4_static_hier.vlt &
wait
run(){ # bin case tag
  local d=$O/$3; rm -rf $d; cp -r $R/cases/$2 $d
  ( cd $d && /usr/bin/time -v $R/obj_$1/V$1 $(cat plus.txt) > run.log 2>&1; echo RUN_RC=$? >> run.log )
  grep -h "HC_ENG_DONE\|HC_ENG PASS\|HC_ENG FAIL\|FAULT\|MISMATCH\|watchdog\|RUN_RC\|Elapsed" $d/run.log | head -8 | sed "s|^|  $3: |" >> $O/verdict.txt
}

run s0 s_probe s_probe &
run s0 s_p1 s_p1 &
run s0 s_p2 s_p2 &
run s0 s_p8 s_p8 &
run s0 s_g22 s_g22 &
run s0 s_neg164 s_neg164 &
run s0 s_mutdata s_mutdata &
run s1 s_p1 s_mut1_p1 &
run s4 s_p1 s_mut4_p1 &
wait
grep -m3 "PROBE raw" $O/s_probe/run.log | sed 's/^/  probe: /' >> $O/verdict.txt
V "chain done"
