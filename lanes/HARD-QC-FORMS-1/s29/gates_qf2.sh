#!/bin/bash
# gates_qf2.sh PLAN_ABS OUTDIR : schema / G0 / G0C / street_rule with the pipe tree tools (DIE-QC-100 gates_g.sh recipe)
set -uo pipefail; cd /
S=${TREE:-/srv/opentallas-scratch2/claude/hard-qc-forms-1/pipe/tree}; PL=$1; O=$2; rm -rf $O; mkdir -p $O/g0 $O/g0c
echo "gates start $(date) plan=$(sha256sum $PL|cut -c1-12)" > $O/gates.log
( cd $S && nice -n 19 python3 -I -c "import sys; sys.path.insert(0, \"tools/die_plan\"); import schema; sys.exit(schema.main([\"schema.py\", \"validate\", \"$PL\"]))" > $O/schema.log 2>&1; echo "rc=$?" >> $O/schema.log ) &
( cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0 --quiet > $O/g0.log 2>&1; echo "rc=$?" >> $O/g0.log ) &
( cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0c --quiet --completeness > $O/g0c.log 2>&1; echo "rc=$?" >> $O/g0c.log ) &
( cd $S && nice -n 19 python3 -I tools/die_plan/street_rule.py check $PL --repo . --out $O/street.json > $O/street.log 2>&1; echo "rc=$?" >> $O/street.log ) &
wait; echo "gates end $(date)" >> $O/gates.log
