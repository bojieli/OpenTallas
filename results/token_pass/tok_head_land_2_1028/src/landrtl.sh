#!/bin/bash
# TOK-HEAD-LAND-2 step 2a: LANDED HEAD top RTL in the strap form from the DIE-HEAD-17 GATE CA plan (clk17_max_2, 545.3/445.7)
# Fail-closed on count_align_bind (incl. its verify), compose, latency, ft adapter, gen rtl (incl. strap audit).
# = MESO-STRAP-1 head_part_run.sh chain (count_align_bind --strap-form -> compose -> latency -> ft adapter -> gen rtl --clock-landing)
set -u
W=/srv/opentallas-scratch2/claude/wt/tok-head-land-2; O=/srv/opentallas-scratch2/claude/tok-head-land-2/land
G=/srv/opentallas-scratch2/claude/die-head-17/clk17_max_2
J=$W/physical/die_plan/s81_head/die_plan_root_sp5_lat545.3.json; OBS=/srv/opentallas-scratch2/claude/land-head-bind-1/observer_ctl.json
T0=/srv/opentallas-scratch2/claude/die-head-3/part/regions_part.json
mkdir -p $O; cd $W; echo START $(date) code $(git rev-parse --short HEAD) dirty $(git status --porcelain -uno | wc -l)
md5sum $G/ca/plan.json $G/ca/bind.json $J $T0 $OBS
python3 tools/die_plan/count_align_bind.py $G/ca/plan.json --parts region --table $T0 --table-out $O/regions_strap.json --out $O/bind_strap.json --strap-form --plan-die $J --straps-out $O/straps.json > $O/cab.log 2>&1 || { echo CAB_FAIL; tail -5 $O/cab.log; exit 1; }; tail -3 $O/cab.log
python3 tools/s81_head/fallback_land.py compose $J --table $O/regions_strap.json --out $O/compose --monitor region --observer-spec $OBS > $O/compose.log 2>&1 || { echo COMPOSE_FAIL; tail -5 $O/compose.log; exit 1; }
python3 -c "import json;r=json.load(open(\"$O/compose/compose_report.json\"));c=r[\"compose\"];print(\"compose\",c[\"status\"],\"types\",c[\"types_before\"],\"->\",c[\"types_after\"],\"lc_err\",c[\"landing_contract\"][\"errors\"],\"boot\",c.get(\"boot_ready_max_cycles\"))"
cp $O/compose/landed_plan.json $O/landed_lat.json
python3 tools/die_plan/gen.py latency $O/landed_lat.json --out $O/lat --inplace > $O/lat.log 2>&1 || { echo LAT_FAIL; tail -3 $O/lat.log; exit 1; }
python3 tools/s81_head/head_landed_ft_adapter.py $O/landed_lat.json --out $O/landed_lat_ft.json > $O/ft.log 2>&1 || { echo FT_FAIL; tail -3 $O/ft.log; exit 1; }
rm -rf $O/gen; python3 tools/die_plan/gen.py rtl $O/landed_lat_ft.json --out $O/gen --rtl-root $W --clock-landing $O/compose/landed_sidecar.json > $O/gen.log 2>&1 || { echo GEN_FAIL; tail -3 $O/gen.log; exit 1; }
cat $O/gen/gen_count_strap_audit.json 2>/dev/null | head -8
# die sim (intel1 run dir R; copy land/ there first): bench + START tree, build, nominal run
echo "next: R=/srv/opentallas-scratch2/claude/tok-head-land-2: setup_land.sh; ot-run build.sh TT; run.sh TT pos_TT (expect DIE_SPINE PASS, GO->result 8780)"
echo END $(date)
