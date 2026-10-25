#!/bin/bash
# gate.sh NAME OUTROOT  (cwd = repo root): one S81-KITS-RTLA gate; prints "GATE NAME PASS|FAIL <detail>"
set -u; N=$1; O=$2/$N; rm -rf $O; mkdir -p $O
case $N in
  hcpl)      bash tools/s81_slice/hcpl_bench.sh $O both > $O/out.log 2>&1; r=$?;;
  vs0)       bash tools/s81_slice/vs_bench.sh $O 0 > $O/out.log 2>&1; r=$?;;
  vs1)       bash tools/s81_slice/vs_bench.sh $O 1 > $O/out.log 2>&1; r=$?;;
  leaf0)     bash tools/s81_slice/leaf_bench.sh $O 0 > $O/out.log 2>&1; r=$?;;
  ve0)       OT_VE_DEFS=-DOT_S81_VE_LOADSAFE5 bash tools/s81_slice/ve_bench.sh $O 0 > $O/out.log 2>&1; r=$?;;
  ve1)       OT_VE_DEFS=-DOT_S81_VE_LOADSAFE5 bash tools/s81_slice/ve_bench.sh $O 1 > $O/out.log 2>&1; r=$?; [ $r != 0 ] && grep -q REJECTED $O/out.log && r=0 || r=1;;
  vemiter0)  OT_VE_DEFS=-DOT_S81_VE_LOADSAFE5 bash tools/s81_slice/ve_miter.sh $O 0 > $O/out.log 2>&1; r=$?;;
  vemiter1)  OT_VE_DEFS=-DOT_S81_VE_LOADSAFE5 bash tools/s81_slice/ve_miter.sh $O 1 > $O/out.log 2>&1; r=$?; [ $r != 0 ] && grep -q REJECTED $O/out.log && r=0 || r=1;;
  vemix0)    OT_VE_DEFS=-DOT_S81_VE_LOADSAFE5 bash tools/s81_slice/ve_mixmiter.sh $O 0 > $O/out.log 2>&1; r=$?;;
  ves20)     OT_VE_DEFS=-DOT_S81_VE_LOADSAFE5 bash tools/s81_slice/ve_s2miter.sh $O 0 > $O/out.log 2>&1; r=$?;;
  beat)      bash tools/s81_slice/beat_bench.sh $O base > $O/out.log 2>&1; r=$?;;
  vqpr)      bash tools/s81_slice/vq_pinreg_eq.sh $O base > $O/out.log 2>&1; r=$?;;
  vqprmut)   bash tools/s81_slice/vq_pinreg_eq.sh $O mut > $O/out.log 2>&1; grep -q NEGATIVE_CONTROL_FAILED_AS_EXPECTED $O/out.log; r=$?;;
  aq12)      bash tools/s81_slice/aq12_xmem_bench.sh $O base > $O/out.log 2>&1; r=$?;;
  rrbase)    J=8 bash tools/s81_dv/eng_rr/bench_rr_split.sh $O base > $O/out.log 2>&1; r=$?;;
  rrsm1)     J=8 bash tools/s81_dv/eng_rr/bench_rr_split.sh $O sm1 > $O/out.log 2>&1; r=$?; [ $r != 0 ] && r=0 || r=1;;
  rrpre)     git show origin/main:rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr_split.sv > $O/split_prefix.sv
             J=8 SPLIT_SV=$O/split_prefix.sv bash tools/s81_dv/eng_rr/bench_rr_split.sh $O base > $O/out.log 2>&1; r=$?; [ $r != 0 ] && r=0 || r=1;;
  plan)      PNG= bash physical/die_plan/s81/run_v4.sh $O/plan > $O/out.log 2>&1; r=$?
             python3 tools/die_plan/check.py $O/plan/die_plan.json --completeness > $O/compl.log 2>&1; r2=$?; [ $r = 0 ] && r=$r2;;
  *) echo "GATE $N FAIL unknown"; exit 2;;
esac
v=PASS; [ $r = 0 ] || v=FAIL
echo "GATE $N $v rc=$r $(tail -n 3 $O/out.log | tr '\n' ' ' | cut -c1-300)"
exit $r
