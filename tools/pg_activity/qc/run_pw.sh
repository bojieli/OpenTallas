#!/bin/bash
# run_pw.sh TAG ODB SDC RC MACROS ACT DEF INDEF
set -uo pipefail
W=/srv/opentallas-scratch2/claude/qc-pg-3/pw; T=$1
docker run --rm --name qcpg3-pw-$T --network none --cpus 2 --memory 12g -v /srv/opentallas-scratch2/claude:/srv/opentallas-scratch2/claude:ro -v $W:$W openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; OT_ODB=$2 OT_SDC=$3 OT_RC=$4 OT_MACROS=$5 OT_ACT=$6 OT_DEF=$7 OT_IN_DEF=$8 OT_OUT=$W/out/$T.rpt openroad -exit $W/power_act.tcl" > $W/log/$T.log 2>&1
echo "rc $?" >> $W/log/$T.log
