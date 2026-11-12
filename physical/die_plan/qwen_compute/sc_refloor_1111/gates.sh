#!/bin/bash
# SC-REFLOOR-1 gates: schema validate, G0 check.py, station_lint on the s25 tool tree (read-only use)
set -uo pipefail; cd /
R=/srv/opentallas-scratch2/claude/sc-refloor-1; S=/srv/opentallas-scratch2/claude/kw45/src_qc_s25_4e2764d237
mkdir -p $R/gt
for P in "$@"; do
  PL=$R/planq/$P.json
  ( cd $S && nice -n 19 python3 -I -B -c "import sys; sys.path.insert(0, 'tools/die_plan'); import schema; sys.exit(schema.main(['schema.py', 'validate', '$PL']))" > $R/gt/schema_$P.log 2>&1; echo "rc=$?" >> $R/gt/schema_$P.log ) &
  ( mkdir -p $R/gt/g0_$P; cd $S && nice -n 19 python3 -I -B tools/die_plan/check.py $PL --out $R/gt/g0_$P --quiet > $R/gt/g0_$P.log 2>&1; echo "rc=$?" >> $R/gt/g0_$P.log ) &
  ( cd $S && nice -n 19 python3 -I -B tools/die_plan/station_lint.py $PL --tsv $R/gt/sl_$P.tsv > $R/gt/sl_$P.log 2>&1; echo "rc=$?" >> $R/gt/sl_$P.log ) &
done
wait
echo "GATES DONE $(date)"
