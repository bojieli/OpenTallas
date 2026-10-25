#!/bin/bash
# S81/RTLSPLIT gate runner: gate.sh NAME  (runs in the lane dir; sources = ./src snapshot of claude/s81-rtlsplit-1024r)
set -u; L=$(cd $(dirname $0) && pwd); N=$1; O=$L/runs/$N; rm -rf $O; mkdir -p $O; cd $L/src
D5=-DOT_S81_VE_LOADSAFE5
case $N in
  vnmit0)   bash tools/s81_slice/vn_spmiter.sh $O base > $O/out.log 2>&1; r=$?;;
  vnmitc1)  bash tools/s81_slice/vn_spmiter.sh $O c1 > $O/out.log 2>&1; r=$?;;
  vnmithq)  bash tools/s81_slice/vn_spmiter.sh $O hq > $O/out.log 2>&1; r=$?;;
  vemit0)   OT_VE_DEFS=$D5 bash tools/s81_slice/ve_spmiter.sh $O 0 > $O/out.log 2>&1; r=$?;;
  vemit1|vemit2|vemit3) OT_VE_DEFS=$D5 bash tools/s81_slice/ve_spmiter.sh $O ${N#vemit} > $O/out.log 2>&1; grep -q REJECTED $O/out.log; r=$?;;
  vemitmv)  OT_VE_DEFS="$D5 -DOT_S81SL_SPMUT_MV" bash tools/s81_slice/ve_spmiter.sh $O 0 > $O/out.log 2>&1; grep -q "REJECTED\|FAIL golden" $O/out.log; r=$?;;
  oldmit2)  OT_VE_DEFS=$D5 bash tools/s81_slice/ve_miter.sh $O 2 > $O/out.log 2>&1; grep -q REJECTED $O/out.log; r=$?;;
  beat)     bash tools/s81_slice/beat_bench.sh $O base > $O/out.log 2>&1; r=$?;;
  beattree) bash tools/s81_slice/beat_bench.sh $O muttree > $O/out.log 2>&1; r=$?;;
  leaf0)    bash tools/s81_slice/leaf_bench.sh $O 0 > $O/out.log 2>&1; r=$?;;
  leaf1)    bash tools/s81_slice/leaf_bench.sh $O 1 > $O/out.log 2>&1; r=$?;;
  leafeng0) bash tools/s81_slice/leaf_eng_bench.sh $O 0 > $O/out.log 2>&1; r=$?;;
  leafeng7) bash tools/s81_slice/leaf_eng_bench.sh $O 7 > $O/out.log 2>&1; r=$?;;
  *) echo "GATE $N FAIL unknown"; exit 2;;
esac
v=PASS; [ $r = 0 ] || v=FAIL
echo "GATE $N $v rc=$r $(tail -n 3 $O/out.log | tr "\n" " " | cut -c1-300)" | tee $O/verdict.txt
exit $r
