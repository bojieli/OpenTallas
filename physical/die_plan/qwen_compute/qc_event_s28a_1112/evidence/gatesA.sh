#!/bin/bash
# QC-S28-A gates (epyc9): schema / G0 / G0C / station_lint on plan_qc99_s28a with origin/main tools (src28am)
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-s28a; POR=physical/die_plan/qwen_compute/plan_of_record
S=$W/src28am; P=plan_qc99_s28a; PL=$S/$POR/$P.json; O=$W/out/$P; rm -rf $O; mkdir -p $O
echo "gatesA start $(date) plan=$(sha256sum $PL|cut -c1-12)"
( cd $S && nice -n 19 python3 -I -c "import sys; sys.path.insert(0, 'tools/die_plan'); import schema; sys.exit(schema.main(['schema.py', 'validate', '$PL']))" > $O/schema.log 2>&1; echo "rc=$?" >> $O/schema.log ) &
( mkdir -p $O/g0; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0 --quiet > $O/g0.log 2>&1; echo "rc=$?" >> $O/g0.log ) &
( mkdir -p $O/g0c; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0c --quiet --completeness > $O/g0c.log 2>&1; echo "rc=$?" >> $O/g0c.log ) &
( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $O/station_lint.tsv > $O/station_lint.log 2>&1; echo "rc=$?" >> $O/station_lint.log ) &
wait; echo "gatesA end $(date)"
