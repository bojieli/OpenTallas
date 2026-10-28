#!/bin/bash
# MESO-STRAP-1 real example: HEAD part map in the strap form (count_align_bind --strap-form -> compose -> lat -> ft -> gen rtl)
set -u
W=/srv/opentallas-scratch2/claude/wt/meso-strap-1; O=/srv/opentallas-scratch2/claude/meso-strap-1/head
J=$W/physical/die_plan/s81_head/die_plan.json; OBS=/srv/opentallas-scratch2/claude/land-head-bind-1/observer_ctl.json
T0=/srv/opentallas-scratch2/claude/die-head-3/part/regions_part.json
cd $W; echo START $(date) code $(git rev-parse --short HEAD)
for F in strap param; do
  X=""; [ $F = strap ] && X="--strap-form --plan-die $J --straps-out $O/straps.json"
  python3 tools/die_plan/count_align_bind.py results/meso_reconcile_1027/head_part/plan_edgepad.json --parts region --table $T0 --table-out $O/regions_$F.json --out $O/bind_$F.json $X > $O/cab_$F.log 2>&1; echo cab $F rc=$?
done
python3 tools/s81_head/fallback_land.py compose $J --table $O/regions_strap.json --out $O/compose --monitor region --observer-spec $OBS > $O/compose.log 2>&1 || { echo COMPOSE_FAIL; tail -5 $O/compose.log; exit 1; }
python3 -c "import json;r=json.load(open(\"$O/compose/compose_report.json\"));c=r[\"compose\"];print(\"compose\",c[\"status\"],\"types\",c[\"types_before\"],\"->\",c[\"types_after\"],\"lc_err\",c[\"landing_contract\"][\"errors\"])"
cp $O/compose/landed_plan.json $O/landed_lat.json
python3 tools/die_plan/gen.py latency $O/landed_lat.json --out $O/lat --inplace > $O/lat.log 2>&1 || { echo LAT_FAIL; tail -3 $O/lat.log; exit 1; }
python3 tools/s81_head/head_landed_ft_adapter.py $O/landed_lat.json --out $O/landed_lat_ft.json > $O/ft.log 2>&1 || { echo FT_FAIL; tail -3 $O/ft.log; exit 1; }
rm -rf $O/gen; python3 tools/die_plan/gen.py rtl $O/landed_lat_ft.json --out $O/gen --rtl-root $W --clock-landing $O/compose/landed_sidecar.json > $O/gen.log 2>&1; echo "gen rc=$?"; tail -3 $O/gen.log
echo END $(date)
