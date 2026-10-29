#!/usr/bin/env bash
# HBM-CORES-REBAL-9: one phase of tools/hbm_static/su_multirate_native_run.sh "run" (same binary, same +args, same pass
# rule), so the positive run, the six mutants and BRIDGE_LEAF run as parallel ot-run jobs instead of 11 h serially.
#   tok_phase.sh OUT POS|DATA|ADDR|RF|RED|CAL|EPOCH|BRIDGE_LEAF
set -uo pipefail
out=$1; ph=$2; bin="$out/obj/Vtb_hbm_su_native_multirate_top"
[ -x "$bin" ] || { echo "no binary $bin"; exit 2; }
case $ph in
 POS) log=$out/positive.log; "$bin" +DIR="$out/vec" > $log 2>&1; rc=$?
      grep -q 'SU_NATIVE_MULTIRATE_TOP PASS' $log && echo "PHASE POS PASS rc=$rc" > $out/phase_POS.res || echo "PHASE POS FAIL rc=$rc" > $out/phase_POS.res;;
 BRIDGE_LEAF) log=$out/bridge_leaf.log; "$bin" +DIR="$out/vec" +BRIDGE_LEAF > $log 2>&1; rc=$?
      grep -q 'SU_NATIVE_MULTIRATE_TOP PASS' $log && echo "PHASE BRIDGE_LEAF PASS rc=$rc" > $out/phase_BRIDGE_LEAF.res || echo "PHASE BRIDGE_LEAF FAIL rc=$rc" > $out/phase_BRIDGE_LEAF.res;;
 DATA|ADDR|RF|RED|CAL|EPOCH) log=$out/mut_$ph.log; "$bin" +DIR="$out/vec" +MUT_$ph $( [ $ph = ADDR ] && [ -n "${MUT_ADDR_EDGE:-}" ] && echo +MUT_ADDR_EDGE=$MUT_ADDR_EDGE ) > $log 2>&1; rc=$?
      if [ $rc != 0 ] && grep -q 'SU_NATIVE_MULTIRATE_TOP FAIL' $log; then echo "PHASE MUT_$ph CAUGHT rc=$rc" > $out/phase_$ph.res
      else echo "PHASE MUT_$ph NOT_CAUGHT rc=$rc" > $out/phase_$ph.res; fi;;
 *) echo "bad phase $ph"; exit 2;;
esac
cat $out/phase_$ph.res
