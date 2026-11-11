#!/bin/bash
# CPL-S81-SLICE-4 t73 ST2: positions (t73_pos.json) + fix.py stations/taps + resite + bands + ft sites; gates
L=/srv/opentallas-scratch3/claude/cpl-s81-slice-4; R=/srv/opentallas-scratch2/claude/die-s81-85/compose1111; B=$R/out/v_fb2b/plan.json; cd $L
TY=ot_s81sl_leaf__t73; V=${V:-t73}; D=$L/$V
cp $L/INTENT_T73-ST4.md $D/ 2>/dev/null
(cd $R/repo/tools/die_plan && nice -n 19 python3 /srv/opentallas-scratch3/claude/cpl-s81-slice-3/fix.py $B $D/t73_pos.json $D/F0) | cut -c1-400
cmp(){ (cd $R/repo; nice -n 19 python3 -I physical/die_plan/s81/compose_cleanslate_1111_r4.py compose $B $1 --base-sha b5faa1bacc5f6e80c6167856ee1597a7a775ea81dad9305424a3c47de0786d7b --phys --g0-base $R/out/g0_base_1200 --pos $D/t73_pos.json::$L/INTENT_T73-ST4.md --derived $2 --window-tap $D/F0_window_tap.json > $1.log 2>&1); grep '"verdict"' $1.log | cut -c1-900; }
rm -rf $D/c1 $D/c2; cmp $D/c1 $D/F0_companion.json
(cd $R/repo/tools/die_plan && nice -n 19 python3 $L/resite.py $B $D/c1/plan.json $D/F0_companion.json $D/F1_companion.json $D/F1_resite_rep.json) | cut -c1-1500
python3 -I -c "
import json,copy
B=json.load(open('$B'))['partition_types']['$TY']; C=json.load(open('$D/F1_companion.json')); F=json.load(open('$D/t73_ft.json'))['$TY']
fs=[]
for f in B['ft_slots']:
  g=copy.deepcopy(f); g.update(F.get(f['name'],{})); fs.append(g)
C['$TY']['ft_slots']=fs; json.dump(C,open('$D/F2_companion.json','w'))"
cmp $D/c2 $D/F2_companion.json
nice python3 -I $L/apply_bands.py $D/c2/plan.json $D/t73_bands.json $D/final_plan.json
sha256sum $D/final_plan.json $D/t73_pos.json $D/F2_companion.json $D/t73_ft.json $D/t73_bands.json | cut -c1-12,65-
S=$R/repo/physical/die_plan/s81; T=$S/.slice4_g0_$V$$.json; cp $D/final_plan.json $T; (cd $R/repo; nice -n 19 python3 -I tools/die_plan/check.py $T --out $D/g0 --quiet > $D/g0.log 2>&1 || true); rm -f $T
python3 -I -c "
import json
b=json.load(open('$R/out/g0_base_1200/g0_report.json'));o=json.load(open('$D/g0/g0_report.json'))
k=lambda i:(i.get('check'),i.get('msg'))
eb={k(i) for i in b['findings'] if i.get('level')=='ERROR'};wb={k(i) for i in b['findings'] if i.get('level')=='WARN'}
ne=[i for i in o['findings'] if i.get('level')=='ERROR' and k(i) not in eb];nw=[i for i in o['findings'] if i.get('level')=='WARN' and k(i) not in wb]
print('G0 errors',b['errors'],'->',o['errors'],'new',len(ne),'warn new',len(nw)); [print(' E',i['check'],i['msg'][:220]) for i in ne[:12]]; [print(' W',i['check'],i['msg'][:200]) for i in nw[:10]]"
cd /srv/opentallas-scratch2/claude/plan-route-1/repo
for p in $B $D/final_plan.json; do echo -n "station_lint: "; nice -n 19 python3 -I tools/die_plan/station_lint.py $p --types $TY 2>&1 | tail -1; done
nice -n 19 python3 -I tools/die_plan/route_supply.py $D/final_plan.json --die s81 --repo . --types $TY --release-cache /srv/opentallas-scratch2/claude/plan-route-1/release_cache.json --out $D/rs 2>&1 | grep -E "^s81" | cut -f2,3,6,7,8,9
X=/srv/opentallas-scratch3/claude/explorer-script/tools/fleet_viz/explorer_render.py
nice -n 19 python3 -I $X type --plan $D/final_plan.json --type $TY --repo . --supply --release-cache /srv/opentallas-scratch2/claude/plan-route-1/release_cache.json --out $D/ex >/dev/null 2>&1
for f in $L/t73_base/type_$TY.links.tsv $D/ex/type_$TY.links.tsv; do awk -F"\t" "NR>1{if(\$10>m)m=\$10; b+=\$14; if(\$12==\"over\")o++; bm+=\$11} END{printf \"explorer over=%d maxhop=%.1f bypass=%d bitmm=%.0f\n\", o,m,b,bm}" $f; done
echo T73_DONE
