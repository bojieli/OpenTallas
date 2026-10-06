#!/bin/bash
# usage: qgrt_all.sh <round> [var]   Qwen tile die: legality/track/pin access + GRT k16 (empty base i5, i5, i50)
set -u
R=$(cd $(dirname $0) && pwd); RD=$R/cases/$1; VAR=${2:-}
mkdir -p $RD; cp $R/src/tools/hbm_accel_die_run_case.sh $RD/run_case.sh; chmod +x $RD/run_case.sh
echo "${VAR}" > $RD/VARIANT; cp $R/src/SOURCE_COMMIT $RD/
cd $R/src
F="--die qwen ${VAR:+--var $VAR}"
python3 tools/hbm_accel_die_fp.py real $F --work $RD/a_real > /dev/null
python3 tools/hbm_accel_die_fp.py grt $F --work $RD/b_k16_i5_base --k 16 --iters 5 --empty > /dev/null
python3 tools/hbm_accel_die_fp.py grt $F --work $RD/b_k16_i5 --k 16 --iters 5 > /dev/null
python3 tools/hbm_accel_die_fp.py grt $F --work $RD/b_k16_i50 --k 16 --iters 50 > /dev/null
cd $RD
MEM=$(free -g | awk '/^Mem:/{print $2}')
if [ "$MEM" -lt 200 ]; then BIG=14; SMALL=10; else BIG=24; SMALL=12; fi   # AGIdock rule: <=16 GB; EPYC: 24
/srv/opentallas-scratch/admit.sh $BIG -- ./run_case.sh a_real run.tcl run.log 16 96 > a_real.nohup 2>&1 &
for c in b_k16_i5_base b_k16_i5 b_k16_i50; do /srv/opentallas-scratch/admit.sh $SMALL -- ./run_case.sh $c run.tcl run.log 12 48 > $c.nohup 2>&1 & done
wait
echo ALLDONE > $RD/ALLDONE
