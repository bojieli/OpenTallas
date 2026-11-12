#!/bin/bash
# QC-VIS-RESITE gates on epyc9: main e49b6ac817 + s25 tools overlay (srcm), plans in planq/. Usage: gates.sh NAME [NAME...]
# per plan: schema validate, G0, G0C (--completeness), station_lint, route_supply (27 types). DO_NOT_COUNT.
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-vis-resite; S=${SRC:-$W/srcm}; PD=$W/conns; PQ=${PQ:-planq}
TY=$(python3 -I -c "import json;print(','.join(json.load(open('$W/reverted_types.json'))+json.load(open('$W/reverted_stm.json'))))")
echo "gates start $(date) check.py=$(sha256sum $S/tools/die_plan/check.py|cut -c1-12) route_supply.py=$(sha256sum $S/tools/die_plan/route_supply.py|cut -c1-12)"
for P in "$@"; do
  PL=$W/$PQ/$P.json; O=$W/out/$P; mkdir -p $O
  echo "$P sha $(sha256sum $PL|cut -c1-12)"
  ( cd $S && nice -n 19 python3 -I -c "import sys; sys.path.insert(0, 'tools/die_plan'); import schema; sys.exit(schema.main(['schema.py', 'validate', '$PL']))" > $O/schema.log 2>&1; echo "rc=$?" >> $O/schema.log ) &
  ( mkdir -p $O/g0; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0 --quiet > $O/g0.log 2>&1; echo "rc=$?" >> $O/g0.log ) &
  ( mkdir -p $O/g0c; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0c --quiet --completeness > $O/g0c.log 2>&1; echo "rc=$?" >> $O/g0c.log ) &
  ( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $O/station_lint.tsv > $O/station_lint.log 2>&1; echo "rc=$?" >> $O/station_lint.log ) &
  ( cd $S && nice -n 19 python3 -I tools/die_plan/route_supply.py $PL --die qwen_compute --repo $S --ref-dirs $PD --types $TY --out $O/rs > $O/rs.log 2>&1; echo "rc=$?" >> $O/rs.log ) &
done
wait
echo "gates end $(date)"
