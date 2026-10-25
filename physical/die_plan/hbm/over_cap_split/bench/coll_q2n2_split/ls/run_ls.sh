#!/bin/bash
# run_ls.sh TAG CYCLES : lock-step runs (positive seeds/densities + mutants 1..5) of obj_TAG/sim (PATH-HBM/Q3 10-25)
D=/srv/opentallas-scratch2/claude/path-hbm/ne2/ls; cd $D; T=$1; N=${2:-4000}; out=lockstep_$T.log; : > $out
run() { (timeout 3000 ./obj_$T/sim +seed=$1 +dens=$2 +mut=$3 +cycles=$N > ls_${T}_s$1_d$2_m$3.log 2>&1; echo "rc=$?" >> ls_${T}_s$1_d$2_m$3.log) ; }
run 1 8 0 & run 2 2 0 & run 3 32 0 & run 4 4 0 &
for m in 1 2 3 4 5; do run 1 8 $m & done
wait
for f in ls_${T}_*.log; do echo "$f: $(grep -E "LOCKSTEP" $f | tail -1) $(grep -m3 MISMATCH $f | tr "\n" " ") $(tail -1 $f)"; done >> $out
cat $out
