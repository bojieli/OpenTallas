#!/bin/bash
# HCENG 1000: RTL mutant N build, then run the P1 case chosen by chain_m0 (expect FAIL)
set -u
N=$1; R=/tmp/ot-hc-eng-0600b; O=$R/out_1000; mkdir -p $O
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
V(){ echo "$(date -Is) $*" >> $O/verdict.txt; }
cd $R || exit 9
V "chain_mut$N start"
/usr/bin/time -v python3 tools/hbm_hc_eng_build.py --objdir objv_m$N --mutant $N --xwb 4 --jobs 16 > $O/build_m$N.log 2>&1; rc=$?
V "build_m$N rc=$rc"
B=$R/objv_m$N/Vtb_hbm_hc_eng_static; [ -x $B ] || { V "NO BINARY m$N"; exit 2; }
for i in $(seq 1 1440); do [ -s $O/rs.txt ] && [ -d $O/p1 ] && break; [ -s $O/rs.txt ] && [ "$(cat $O/rs.txt)" = 0 ] && break; sleep 60; done
[ -d $O/p1 ] || { V "mut$N: no passing P1 case to mutate against"; exit 3; }
for c in p1 g22; do
  [ $N != 2 ] && [ $c = g22 ] && continue
  [ -d $O/$c ] || continue
  d=$O/mut${N}_$c; rm -rf $d; cp -r $O/$c $d; rm -f $d/run.log
  ( cd $d && /usr/bin/time -v $B $(cat plus.txt) > run.log 2>&1; echo RUN_RC=$? >> run.log )
  grep -h "HC_ENG_DONE\|HC_ENG PASS\|HC_ENG FAIL\|FAULT\|MISMATCH\|RUN_RC" $d/run.log | head -6 | sed "s|^|  mut${N}_$c: |" >> $O/verdict.txt
  grep -q "HC_ENG PASS" $d/run.log && V "MUT$N $c unexpectedly PASS (escape)" || V "MUT$N $c FAIL as expected"
done
V "chain_mut$N done"
