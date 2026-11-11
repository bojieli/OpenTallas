#!/bin/bash
# CPL-S81-SLICE-4 FIN8 = CPL-S81-SLICE-3 FIN7 positions/bands/window taps + re-sited station regs (FIN8_companion.json)
P=/srv/opentallas-scratch3/claude/cpl-s81-slice-3; L=/srv/opentallas-scratch3/claude/cpl-s81-slice-4; R=/srv/opentallas-scratch2/claude/die-s81-85/compose1111; B=$R/out/v_fb2b/plan.json; cd $L
cp $P/FIN7_pos.json $P/FIN7_window_tap.json $P/FIN7_bands.json $P/INTENT_SLICE-C-SRING.md $P/apply_bands.py .
TY=dsdv_slice_c1x_C__t1,dsdv_slice_c1x_C__t3,dsdv_slice_c1x_C__t5,dsdv_slice_c1x_C__t7,dsdv_slice_lepw_mu_C__t1,dsdv_slice_lepw_mus_C__t1
rm -rf d8 d8b_plan.json
(cd $R/repo; nice -n 19 python3 -I physical/die_plan/s81/compose_cleanslate_1111_r4.py compose $B $L/d8 --base-sha b5faa1bacc5f6e80c6167856ee1597a7a775ea81dad9305424a3c47de0786d7b --phys --g0-base $R/out/g0_base_1200 --pos $L/FIN7_pos.json::$L/INTENT_SLICE-C-SRING.md --derived $L/FIN8_companion.json --window-tap $L/FIN7_window_tap.json > $L/d8.log 2>&1)
grep '"verdict"' d8.log | cut -c1-600
nice python3 -I apply_bands.py d8/plan.json FIN7_bands.json d8b_plan.json
sha256sum d8/plan.json d8b_plan.json FIN8_companion.json | cut -c1-12,65-
S=$R/repo/physical/die_plan/s81; T=$S/.slice4_g0_$$.json; cp d8b_plan.json $T; (cd $R/repo; nice -n 19 python3 -I tools/die_plan/check.py $T --out $L/g0_fin8 --quiet > $L/g0_fin8.log 2>&1 || true); rm -f $T
python3 -I -c "
import json
b=json.load(open('$R/out/g0_base_1200/g0_report.json'));o=json.load(open('$L/g0_fin8/g0_report.json'))
k=lambda i:(i.get('check'),i.get('msg'))
eb={k(i) for i in b['findings'] if i.get('level')=='ERROR'};wb={k(i) for i in b['findings'] if i.get('level')=='WARN'}
ne=[i for i in o['findings'] if i.get('level')=='ERROR' and k(i) not in eb];nw=[i for i in o['findings'] if i.get('level')=='WARN' and k(i) not in wb]
print('G0 errors',b['errors'],'->',o['errors'],'new',len(ne),'warn new',len(nw)); [print(' E',i['check'],i['msg'][:200]) for i in ne[:8]]; [print(' W',i['check'],i['msg'][:200]) for i in nw[:10]]"
cd /srv/opentallas-scratch2/claude/plan-route-1/repo
for p in $B $P/d7b_plan.json $L/d8b_plan.json; do echo -n "station_lint $(basename $(dirname $p))/$(basename $p): "; nice -n 19 python3 -I tools/die_plan/station_lint.py $p --types $TY 2>&1 | tail -1; done
nice -n 19 python3 -I tools/die_plan/route_supply.py $L/d8b_plan.json --die s81 --repo . --types $TY --release-cache /srv/opentallas-scratch2/claude/plan-route-1/release_cache.json --out $L/rs_fin8 2>&1 | grep -E "^s81" | cut -f2,3,6,7,8,9
X=/srv/opentallas-scratch3/claude/explorer-script/tools/fleet_viz/explorer_render.py; rm -rf $L/ex_C
for T in ${TY//,/ }; do nice -n 19 python3 -I $X type --plan $L/d8b_plan.json --type $T --repo . --out $L/ex_C >/dev/null 2>&1 & done; wait
for T in ${TY//,/ }; do for tag in B A C; do awk -F"\t" -v t=$T -v g=$tag "NR>1{if(\$10>m)m=\$10; b+=\$14; if(\$12==\"over\")o++} END{printf \"%s %s over=%d maxhop=%.1f bypass=%d\n\", t,g,o,m,b}" $L/ex_$tag/type_${T}.links.tsv; done; done
echo FIN8_DONE
