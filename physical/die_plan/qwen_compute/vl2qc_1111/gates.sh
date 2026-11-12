#!/bin/bash
# VISLAYOUT2-QC gates: schema.validate, G0 check.py, station_lint on main tools (sparse worktree src)
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/vislayout2-qc; S=$W/src
echo "gates start $(date) main $(git -C $S rev-parse --short HEAD)"
for P in "$@"; do
  PL=$W/planq/$P.json
  ( cd $S && nice -n 19 python3 -I -c "import sys; sys.path.insert(0, 'tools/die_plan'); import schema; sys.exit(schema.main(['schema.py', 'validate', '$PL']))" > $W/gt/schema_$P.log 2>&1; echo "rc=$?" >> $W/gt/schema_$P.log ) &
  ( mkdir -p $W/gt/g0_$P; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $W/gt/g0_$P --quiet > $W/gt/g0_$P.log 2>&1; echo "rc=$?" >> $W/gt/g0_$P.log ) &
  ( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $W/gt/sl_$P.tsv > $W/gt/sl_$P.log 2>&1; echo "rc=$?" >> $W/gt/sl_$P.log ) &
done
wait
echo "gates end $(date)"
