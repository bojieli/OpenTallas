#!/bin/bash
# ir_round.sh <src> <round dir> <windows...>: method-c IR windows of the ADOPTED generator round (tools/hbm_accel_die_fp.py
# ir), 4 at a time (r16j: the windows that overlap the re-floorplanned svc bands and the host PHY black box).
# Record: python3 tools/hbm_accel_die_fp.py record --work <round dir> --out <json>.
set -u
SRC=$1; RD=$2; shift 2
mkdir -p $RD; sed "s|openroad/orfs:asap7lock|${IMG:-openroad/orfs:asap7lock}|" $SRC/tools/hbm_accel_die_run_case.sh > $RD/run_case.sh; chmod +x $RD/run_case.sh; cp $SRC/SOURCE_COMMIT $RD/
cd $SRC
for w in "$@"; do python3 tools/hbm_accel_die_fp.py ir --window $w --work $RD/c_$w > $RD/c_$w.gen.log 2>&1; done
cd $RD
echo "$@" | tr ' ' '\n' | xargs -P ${PAR:-4} -I{} /srv/opentallas-scratch/admit.sh 6 -- ./run_case.sh c_{} run.tcl run.log 4 16
echo ALLDONE > ALLDONE
