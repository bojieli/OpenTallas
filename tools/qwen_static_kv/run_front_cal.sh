#!/bin/bash
# run_front_cal.sh OUT [T ...]: qkd_kv_front_cal against kv_calendar.py (the landing_cal golden case files): every
# (stack, group) at each T (default 1 77 700 2048 4097 4300 4500 6000 8192), then negatives (MUT 1 floor block count,
# MUT 2 pacing ignored).  MUTONLY=N runs every case with MUT N expecting PASS (closure-loop negative bench).
set -u
O=$1; shift; mkdir -p "$O"
python3 tools/qwen_static_kv/landing_cal_golden.py "$O/cases" "$@" > "$O/golden.log" 2>&1 || { echo "RESULT FAIL golden"; cat "$O/golden.log"; exit 1; }
S="rtl/test/qwen_static_kv/tb_qkd_kv_front_cal.sv rtl/qwen_sys/static_kv_20261014/qkd_kv_front_cal.sv"
rc=0; np=0; nf=0
run(){ b="$O/bin_m$2.vvp"
 [ -f "$b" ] || iverilog -g2012 -P tb_qkd_kv_front_cal.MUT=$2 -o "$b" $S > "$O/build.log" 2>&1 || { echo "RESULT FAIL build"; tail -3 "$O/build.log"; rc=1; return; }
 l=$(timeout 300 vvp -n "$b" +CASE="$1" | grep -E "^(PASS|FAIL) front_cal" | tail -1)
 case "$l" in PASS*) got=pass;; FAIL*) got=fail;; *) got=noresult;; esac
 if [ "$got" = "$3" ]; then [ "$3" = pass ] && np=$((np+1)) || nf=$((nf+1)); else rc=1; echo "RESULT UNEXPECTED mut=$2 expect=$3 $(basename $1) :: ${l:-no result}"; fi; }
if [ -n "${MUTONLY:-}" ]; then
 for c in "$O"/cases/c_*.txt; do run "$c" "$MUTONLY" pass; done
 echo "RESULT $([ $rc = 0 ] && echo OK || echo FAIL) front_cal MUTONLY=$MUTONLY positives_pass=$np"; exit $rc
fi
for c in "$O"/cases/c_*.txt; do run "$c" 0 pass; done
for c in "$O"/cases/c_77_0_0.txt "$O"/cases/c_700_1_4.txt; do run "$c" 1 fail; done
for c in "$O"/cases/c_8192_0_0.txt "$O"/cases/c_8192_2_5.txt; do run "$c" 2 fail; done
echo "RESULT $([ $rc = 0 ] && echo OK || echo FAIL) front_cal positives_pass=$np mutants_fail=$nf"
exit $rc
