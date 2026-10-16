#!/bin/bash
# run_landing_cal.sh OUT [T ...]: qkd_kv_landing_cal against kv_calendar.py (tools/qwen_static_kv/landing_cal_golden.py):
# every (stack, group) at each T (default 1 77 700 2048 4097 4300 4500 6000 8192) with random boot constants, then the three
# negative controls (MUT 1 V sector map, 2 phase, 3 K second half) on cases that exercise them.  One RESULT line per
# case; exit 0 iff every positive PASSes and every mutant FAILs.  Fails closed on golden errors.
# MUTONLY=N: run every case with MUT N expecting PASS (the closure-loop negative bench: must report RESULT FAIL).
set -u
O=$1; shift; mkdir -p "$O"
python3 tools/qwen_static_kv/landing_cal_golden.py "$O/cases" "$@" > "$O/golden.log" 2>&1 || { echo "RESULT FAIL golden"; cat "$O/golden.log"; exit 1; }
S="rtl/test/qwen_static_kv/tb_qkd_kv_landing_cal.sv rtl/qwen_sys/static_kv_20261014/qkd_kv_landing_cal.sv"
rc=0; np=0; nf=0
run(){ # case mut expect
 ph=$(head -1 "$1" | cut -d' ' -f4); b="$O/bin_m$2_p$ph.vvp"
 [ -f "$b" ] || iverilog -g2012 -P tb_qkd_kv_landing_cal.PH0=$ph -P tb_qkd_kv_landing_cal.MUT=$2 -o "$b" $S > "$O/build.log" 2>&1 || { echo "RESULT FAIL build"; tail -3 "$O/build.log"; rc=1; return; }
 l=$(timeout 300 vvp -n "$b" +CASE="$1" | grep -E "^(PASS|FAIL) landing_cal" | tail -1)
 case "$l" in PASS*) got=pass;; FAIL*) got=fail;; *) got=noresult;; esac
 if [ "$got" = "$3" ]; then [ "$3" = pass ] && np=$((np+1)) || nf=$((nf+1)); else rc=1; echo "RESULT UNEXPECTED mut=$2 expect=$3 $(basename $1) :: ${l:-no result}"; fi; }
if [ -n "${MUTONLY:-}" ]; then   # closure-loop negative control: every case with MUT=$MUTONLY, RESULT OK only if all PASS
 for c in "$O"/cases/c_*.txt; do run "$c" "$MUTONLY" pass; done
 echo "RESULT $([ $rc = 0 ] && echo OK || echo FAIL) landing_cal MUTONLY=$MUTONLY positives_pass=$np"; exit $rc
fi
for c in "$O"/cases/c_*.txt; do run "$c" 0 pass; done
# negatives (cases from T 2048 / 8192, which every bench T list carries): MUT 1 V sector map, MUT 2 phase drift, MUT 3 K order
for c in "$O"/cases/c_8192_0_0.txt "$O"/cases/c_8192_3_7.txt; do run "$c" 1 fail; done
for c in "$O"/cases/c_2048_1_3.txt "$O"/cases/c_8192_2_5.txt; do run "$c" 2 fail; done
for c in "$O"/cases/c_2048_0_0.txt "$O"/cases/c_2048_1_3.txt; do run "$c" 3 fail; done
echo "RESULT $([ $rc = 0 ] && echo OK || echo FAIL) landing_cal positives_pass=$np mutants_fail=$nf"
exit $rc
