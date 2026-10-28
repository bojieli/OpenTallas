#!/bin/bash
# DIE-HEAD-3 bind: compose(monitor=region, real ctl observer) -> latency -> hd_tile FT adapter -> gen rtl --clock-landing
# usage: bindrun.sh NAME REGION_TABLE
set -u
W=/srv/opentallas-scratch2/claude/wt/die-head-3-bind; O=/srv/opentallas-scratch2/claude/die-head-3/bind_$1; T=$2
J=/srv/opentallas-scratch2/claude/wt/die-head-3-bind/physical/die_plan/s81_head/die_plan.json; OBS=/srv/opentallas-scratch2/claude/land-head-bind-1/observer_ctl.json
mkdir -p $O; cd $W; echo START $(date) code $(git rev-parse --short HEAD)+dirty table $T
python3 tools/s81_head/fallback_land.py compose $J --table $T --out $O/compose --monitor region --observer-spec $OBS > $O/compose.log 2>&1 || { echo COMPOSE_FAIL; tail -5 $O/compose.log; exit 1; }
python3 -c "import json,sys;r=json.load(open('$O/compose/compose_report.json'));c=r['compose'];print('compose',c['status'],'types',c['types_before'],'->',c['types_after'],'placement_fail',c['placement_failures'],'lc_err',c['landing_contract']['errors'],'boot',c['boot_ready_max_cycles'])"
cp $O/compose/landed_plan.json $O/landed_lat.json
python3 tools/die_plan/gen.py latency $O/landed_lat.json --out $O/lat --inplace > $O/lat.log 2>&1 || { echo LAT_FAIL; tail -3 $O/lat.log; exit 1; }
python3 tools/s81_head/head_landed_ft_adapter.py $O/landed_lat.json --out $O/landed_lat_ft.json > $O/ft.log 2>&1 || { echo FT_FAIL; tail -3 $O/ft.log; exit 1; }
grep -E '"types"|ports_bound|spare_outputs' $O/ft.log | tr -d '\n'; echo
python3 tools/die_plan/gen.py rtl $O/landed_lat_ft.json --out $O/gen --rtl-root $W --clock-landing $O/compose/landed_sidecar.json > $O/gen.log 2>&1; echo "gen rc=$?"; grep -i error $O/gen.log | head -3
python3 -c "
import json;m=json.load(open('$O/gen/gen_clock_landings.json'));c=m['collector']
print('implemented',m['implemented'],'crossings',m['crossings'],'types',len(m['types']),'monitor',c['monitor'])
rp=m['reset_placements'];print('monitor modes',{v['monitor']['mode'] for v in rp.values() if 'monitor' in v},'types w/ monitor',sum('monitor' in v for v in rp.values()),'no-landed-input resets',sum('monitor_reset' in v for v in rp.values()))"
grep -c "cland_dn_ready_" $O/gen/s81_head_top.sv; grep -c "ot_dp_clk_landing" $O/gen/*.sv | awk -F: '{s+=$2} END {print "ring instances (per type files):",s}'
echo END $(date)
