#!/bin/bash
# QC-S28-E gates: schema (src28m tools), G0, G0C, station_lint for BASE and a candidate plan
set -u; cd /
W=/srv/opentallas-scratch2/claude/qc-s28e; POR=physical/die_plan/qwen_compute/plan_of_record
[ -d $W/src28me ] || nice -n 19 cp -al /srv/opentallas-scratch2/claude/qc-event-s28/src28m $W/src28me
S=$W/src28me; rm -f $S/$POR/sink_bins/glue.json; cp $W/glue.json $S/$POR/sink_bins/glue.json
TAG=$1; PL=$2; O=$W/gates_$TAG; rm -rf $O; mkdir -p $O/g0 $O/g0c
cd $S
( nice -n 19 python3 -I -c "import sys; sys.path.insert(0, 'tools/die_plan'); import schema; sys.exit(schema.main(['schema.py', 'validate', '$PL']))" > $O/schema.log 2>&1; echo "rc=$?" >> $O/schema.log ) &
( nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0 --quiet > $O/g0.log 2>&1; echo "rc=$?" >> $O/g0.log ) &
( nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0c --quiet --completeness > $O/g0c.log 2>&1; echo "rc=$?" >> $O/g0c.log ) &
( nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $O/station_lint.tsv > $O/station_lint.log 2>&1; echo "rc=$?" >> $O/station_lint.log ) &
wait; echo "GATES_DONE $TAG $(date)"
