#!/bin/bash
# run phase only of a2f_parent_gate.sh on the already-built binaries (original unit died after builds at 09:27, no run logs)
set -uo pipefail
O=${1:?out}; NMIX=${NMIX:-2400}
declare -A RUN
run() { local key=$1 bin=$2; shift 2; "$O/obj_$bin/tb" "$@" > "$O/$key.log" 2>&1 & RUN[$key]=$!; }
for s in 1 2 3; do run diff_h1_w1_s$s diff_h1_w1 +seed=$s +nmix=$NMIX; done
run diff_h1_w0_s1 diff_h1_w0 +seed=1 +nmix=$NMIX
run diff_h0_w1_s1 diff_h0_w1 +seed=1 +nmix=$NMIX
for m in lane commit rel; do run mut_$m mut_$m +seed=1 +nmix=600; done
for s in 1 2; do run par_a2f_s$s par_a2f +mode=0 +seed=$s; run par_legacy_s$s par_legacy +mode=0 +seed=$s; done
for m in 1 2 3 4 5 6 7 8; do run par_a2f_m$m par_a2f +mode=$m; done
for m in capword wfcpair x43phase; do run par_$m par_$m +mode=0 +seed=1; done
for s in 1 2 3; do run x34sw2_s$s x34sw2 +mode=0 +seed=$s; done
for m in 1 2; do run x34sw2_m$m x34sw2 +mode=$m +seed=1; done
for m in swap drop; do run x34sw2_$m x34sw2_$m +mode=0 +seed=1; done
for k in "${!RUN[@]}"; do wait "${RUN[$k]}"; done
bad=0
chk() { if grep -q "$2" "$O/$1.log"; then echo "PASS $1"; else echo "FAIL $1"; tail -8 "$O/$1.log"; bad=1; fi; }
for s in 1 2 3; do chk diff_h1_w1_s$s '^TB_A2F_DIFF PASS$'; done
chk diff_h1_w0_s1 '^TB_A2F_DIFF PASS$'
chk diff_h0_w1_s1 '^TB_A2F_DIFF PASS$'
for m in lane commit rel; do chk mut_$m '^TB_A2F_DIFF FAIL$'; done
for s in 1 2; do chk par_a2f_s$s '^TB_SPVM PASS mode 0$'; chk par_legacy_s$s '^TB_SPVM PASS mode 0$'; done
for m in 1 2 3 4 5 6 7 8; do chk par_a2f_m$m "^TB_SPVM PASS mode $m "; done
for m in capword wfcpair x43phase; do chk par_$m '^TB_SPVM FAIL mode 0$'; done
for s in 1 2 3; do chk x34sw2_s$s '^TB_X34SW2 PASS mode 0$'; done
for m in 1 2; do chk x34sw2_m$m "^TB_X34SW2 PASS mode $m\$"; done
for m in swap drop; do chk x34sw2_$m '^TB_X34SW2 FAIL mode 0$'; done
grep -h '^TB_A2F_DIFF LAT\|^TB_A2F_DIFF RESULT\|^TB_SPVM RESULT\|^TB_X34SW2 RESULT' "$O"/*.log | sort | uniq -c
[ $bad = 0 ] && echo 'A2F_GATE PASS' || echo 'A2F_GATE FAIL'
exit $bad
