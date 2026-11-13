#!/bin/bash
# gates.sh PLAN_ABS OUTDIR : schema / G0 / G0C / station_lint with the branch (origin/main) tools
set -uo pipefail; cd /
S=${GTREE:-/srv/opentallas-scratch2/claude/qc-s28-hf1c/visform/gtree}; PL=$1; O=$2; rm -rf $O; mkdir -p $O/g0 $O/g0c
echo "gates start $(date) plan=$(sha256sum $PL|cut -c1-12) tree=$(cd $S && git rev-parse --short=12 HEAD)" > $O/gates.log
( cd $S && nice -n 19 python3 -I -c "import sys; sys.path.insert(0, \"tools/die_plan\"); import schema; sys.exit(schema.main([\"schema.py\", \"validate\", \"$PL\"]))" > $O/schema.log 2>&1; echo "rc=$?" >> $O/schema.log ) &
( cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0 --quiet > $O/g0.log 2>&1; echo "rc=$?" >> $O/g0.log ) &
( cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0c --quiet --completeness > $O/g0c.log 2>&1; echo "rc=$?" >> $O/g0c.log ) &
( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $O/station_lint.tsv > $O/station_lint.log 2>&1; echo "rc=$?" >> $O/station_lint.log ) &
wait; echo "gates end $(date)" >> $O/gates.log
