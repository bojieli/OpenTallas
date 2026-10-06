#!/bin/bash
# die_round.sh <src> <round dir> [cases]: the r16g die with every indexed real view in place of its generated master
# (tools/hbm_die_views.py die): a_real = legality / on-track / pin access (k = 1), b_k16_i5 / b_k16_i50 = bundled GRT.
# Cases run in the pinned ORFS image through tools/hbm_accel_die_run_case.sh under admit.sh (EPYC2 NVMe scratch).
set -u
SRC=$1; RD=$2; CASES=${3:-"a_real b_k16_i5 b_k16_i50"}
mkdir -p $RD; cp $SRC/tools/hbm_accel_die_run_case.sh $RD/run_case.sh; chmod +x $RD/run_case.sh; cp $SRC/SOURCE_COMMIT $RD/
cd $SRC
for c in $CASES; do
  case $c in
    a_real) python3 tools/hbm_die_views.py die --case real --work $RD/a_real > $RD/a_real.gen.log 2>&1 ;;
    b_k16_i5) python3 tools/hbm_die_views.py die --case grt --k 16 --iters 5 --work $RD/$c > $RD/$c.gen.log 2>&1 ;;
    b_k16_i50) python3 tools/hbm_die_views.py die --case grt --k 16 --iters 50 --work $RD/$c > $RD/$c.gen.log 2>&1 ;;
  esac
done
cd $RD
for c in $CASES; do /srv/opentallas-scratch/admit.sh 24 -- ./run_case.sh $c run.tcl run.log 8 48 > $c.nohup 2>&1 & done
wait
echo ALLDONE > $RD/ALLDONE
