#!/bin/bash
# HCENG 1000: complete m0 full-engine build (parallel make; PVE make4.3 inner make was serial), probe RAW0, sweep RS on P1,
# then P2/P8/G22 exact + data mutant. Verdicts -> $O/verdict.txt
set -u
R=/tmp/ot-hc-eng-0600b; O=$R/out_1000; mkdir -p $O
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
V(){ echo "$(date -Is) $*" >> $O/verdict.txt; }
V "chain_m0 start host=$(hostname)"
cd $R/objv_h5 || exit 9
/usr/bin/time -v make -f Vtb_hbm_hc_eng_static_hier.mk -j 64 hier_build > $O/build_m0.log 2>&1; rc=$?
V "build_m0 rc=$rc"
B=$R/objv_h5/Vtb_hbm_hc_eng_static
[ -x $B ] || { V "NO BINARY m0"; exit 2; }
run(){ # dir -> rc
  ( cd $1 && /usr/bin/time -v $B $(cat plus.txt) > run.log 2>&1; echo RUN_RC=$? >> run.log )
  grep -h "HC_ENG_DONE\|HC_ENG PASS\|HC_ENG FAIL\|FAULT\|MISMATCH\|watchdog\|RUN_RC\|Elapsed\|Maximum resident" $1/run.log | head -12 | sed "s|^|  $(basename $1): |" >> $O/verdict.txt
  grep -q "HC_ENG PASS" $1/run.log
}
gen(){ ( cd $R/gen && python3 tools/rtl_hbm_hc_eng_static_gate.py --run $1 "${@:2}" ) >> $O/gen.log 2>&1; }
rm -rf $O/probe; cp -r $R/v_probe1 $O/probe
run $O/probe
TL=$(python3 -c "import json;print(json.load(open('$O/probe/case.json'))['events']['TL'])")
T0=$(grep -m1 "PROBE raw" $O/probe/run.log | sed 's/.*t=\([0-9]*\).*/\1/')
[ -n "$T0" ] || { V "probe: no PROBE raw line"; exit 3; }
RAW0=$((T0-TL)); V "probe TL=$TL first_raw_t=$T0 RAW0=$RAW0"
grep "PROBE raw" $O/probe/run.log | head -30 > $O/probe_raw_first30.txt
RS=0
for rs in 104 105 106 108 112 120 136 168 232; do
  d=$O/p1_rs$rs; rm -rf $d; gen $d --mode full --npos 1 --raw0 $RAW0 --rs $rs
  if run $d; then RS=$rs; break; fi
done
echo $RS > $O/rs.txt; echo $RAW0 > $O/raw0.txt
V "P1 RS sweep -> RS=$RS (0 = none passed)"
[ $RS -gt 0 ] || exit 4
cp -r $O/p1_rs$RS $O/p1
if [ $RS -gt 104 ]; then V "neg control RS-1 already failed in sweep (p1_rs<$RS)"; else
  d=$O/neg_rs103; rm -rf $d; gen $d --mode full --npos 1 --raw0 $RAW0 --rs 103; run $d && V "NEG RS103 unexpectedly PASS" || V "NEG RS103 FAIL as expected"; fi
d=$O/neg_raw0m1; rm -rf $d; gen $d --mode full --npos 1 --raw0 $((RAW0-1)) --rs $RS; run $d && V "NEG RAW0-1 unexpectedly PASS" || V "NEG RAW0-1 FAIL as expected"
d=$O/mut_data; rm -rf $d; cp -r $O/p1 $d; python3 - $d/expmix.mem <<'PY'
import sys; p=sys.argv[1]; L=open(p).read().split(); L[5]='%08x'%(int(L[5],16)^1); open(p,'w').write('\n'.join(L)+'\n')
PY
run $d && V "DATA MUTANT (expmix[5]^1) unexpectedly PASS" || V "DATA MUTANT FAIL as expected"
for P in 2 8; do d=$O/p$P; rm -rf $d; gen $d --mode full --npos $P --raw0 $RAW0 --rs $RS; run $d && V "P$P PASS" || V "P$P FAIL"; done
rm -rf $O/g22; cp -r $R/v_g22 $O/g22; run $O/g22 && V "G22 PASS" || V "G22 FAIL"
V "chain_m0 done"
