#!/bin/bash
# usage: qir_all.sh <round> [var] [cov]   Qwen tile die: every IR window (PSM), 16 at a time
set -u
R=$(cd $(dirname $0) && pwd); RD=$R/cases/$1; VAR=${2:-}; COV=${3:-}
mkdir -p $RD; cp $R/src/tools/hbm_accel_die_run_case.sh $RD/run_case.sh; chmod +x $RD/run_case.sh
echo "${VAR}" > $RD/VARIANT; cp $R/src/SOURCE_COMMIT $RD/
cd $R/src
F="--die qwen ${VAR:+--var $VAR}"
for w in $(python3 tools/hbm_accel_die_fp.py irwin $F); do echo $w; done | xargs -P 8 -I{} sh -c "python3 tools/hbm_accel_die_fp.py ir $F --work $RD/c_{} --window {} ${COV:+--cov $COV} > /dev/null"
cd $RD
ls -d c_* | xargs -P 16 -I{} sh -c '/srv/opentallas-scratch/admit.sh 12 -- ./run_case.sh {} run.tcl run.log 6 16 > {}.nohup 2>&1'
echo ALLDONE > $RD/ALLDONE
