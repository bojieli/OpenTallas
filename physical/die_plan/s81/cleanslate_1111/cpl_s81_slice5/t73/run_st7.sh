#!/bin/bash
# CPL-S81-SLICE-5 t73 ST6 (quad form): positions (gen2) + fix.py + compose + resite + quad sites + ST4 ft sites + compose
# + bands, then the approved pin-cycle stations (pc.py), gates and the PLANMODEL-1 route_supply.
L=/srv/opentallas-scratch3/claude/cpl-s81-slice-5; L4=/srv/opentallas-scratch3/claude/cpl-s81-slice-4
R=/srv/opentallas-scratch2/claude/die-s81-85/compose1111; B=$R/out/v_fb2b/plan.json; TY=ot_s81sl_leaf__t73; D=$L/st7
PM=/srv/opentallas-scratch2/claude/s81-planmodel-1; PR=/srv/opentallas-scratch2/claude/plan-route-1/repo
mkdir -p $D; cd $L; export PYTHONDONTWRITEBYTECODE=1
nice -n 19 python3 -I $L/gen2.py $B $L4/t73s4/t73_pos.json $D
cp $L/INTENT_T73-ST7.md $D/
(cd $R/repo/tools/die_plan && nice -n 19 python3 $L4/../cpl-s81-slice-3/fix.py $B $D/t73_pos.json $D/F0) | cut -c1-400
python3 -I -c "
import json; f='$D/F0_window_tap.json'; w=json.load(open(f)); a=w.setdefault('$TY',{}).setdefault('clock.added_taps',{})
a['clk_t22']={'from':[17.28,17.28],'to':[60.48,17.28]}; a['clk_t30']={'from':[678.942,950.265],'to':[600.0,950.0]}; json.dump(w,open(f,'w'),indent=1); print('clk_t22 -> [60.48,17.28] (radius), clk_t30 -> [600,950] (unloads clk_t27 1540/1500)')"
cmp(){ (cd $R/repo; nice -n 19 python3 -I physical/die_plan/s81/compose_cleanslate_1111_r4.py compose $B $1 --base-sha b5faa1bacc5f6e80c6167856ee1597a7a775ea81dad9305424a3c47de0786d7b --phys --g0-base $R/out/g0_base_1200 --pos $D/t73_pos.json::$D/INTENT_T73-ST7.md --derived $2 --window-tap $D/F0_window_tap.json > $1.log 2>&1); grep '"verdict"' $1.log | cut -c1-900; }
rm -rf $D/c1 $D/c2; cmp $D/c1 $D/F0_companion.json
(cd $R/repo/tools/die_plan && nice -n 19 python3 $L4/resite.py $B $D/c1/plan.json $D/F0_companion.json $D/F1_companion.json $D/F1_resite_rep.json) | cut -c1-600
nice -n 19 python3 -I $L/ov.py $B $D/F1_companion.json $D/quad_sites.json $D/F1q_companion.json
python3 -I -c "
import json,copy
B=json.load(open('$B'))['partition_types']['$TY']; C=json.load(open('$D/F1q_companion.json')); F=json.load(open('$L4/t73s4/t73_ft.json'))['$TY']
fs=[]
for f in B['ft_slots']:
  g=copy.deepcopy(f); g.update(F.get(f['name'],{})); fs.append(g)
C['$TY']['ft_slots']=fs; json.dump(C,open('$D/F2_companion.json','w'))"
cmp $D/c2 $D/F2_companion.json
nice python3 -I $L4/apply_bands.py $D/c2/plan.json $L4/t73s4/t73_bands.json $D/pos_plan.json
nice -n 19 python3 -I $L/pc.py $D/pos_plan.json $R/repo/physical/die_plan/s81 $D/final_plan.json
sha256sum $D/pos_plan.json $D/final_plan.json $D/t73_pos.json $D/F2_companion.json $D/quad_sites.json | cut -c1-12,65-
for V in pos_plan final_plan; do
S=$R/repo/physical/die_plan/s81; T=$S/.slice5_g0_$V$$.json; cp $D/$V.json $T; (cd $R/repo; nice -n 19 python3 -I tools/die_plan/check.py $T --out $D/g0_$V --quiet > $D/g0_$V.log 2>&1 || true); rm -f $T
python3 -I -c "
import json
b=json.load(open('$R/out/g0_base_1200/g0_report.json'));o=json.load(open('$D/g0_$V/g0_report.json'))
k=lambda i:(i.get('check'),i.get('msg'))
eb={k(i) for i in b['findings'] if i.get('level')=='ERROR'};wb={k(i) for i in b['findings'] if i.get('level')=='WARN'}
ne=[i for i in o['findings'] if i.get('level')=='ERROR' and k(i) not in eb];nw=[i for i in o['findings'] if i.get('level')=='WARN' and k(i) not in wb]
print('$V G0 errors',b['errors'],'->',o['errors'],'new',len(ne),'warn new',len(nw)); [print(' E',i['check'],i['msg'][:220]) for i in ne[:12]]; [print(' W',i['check'],i['msg'][:200]) for i in nw[:10]]"
done
cd $PR
for p in $B $L4/t73s4/final_plan.json $D/final_plan.json; do echo -n "station_lint $(basename $(dirname $p)): "; nice -n 19 python3 -I tools/die_plan/station_lint.py $p --types $TY 2>&1 | tail -1; done
for p in st4:$L4/t73s4/final_plan.json st6:$D/final_plan.json; do n=${p%%:*}; f=${p#*:}
  (cd $PM && nice -n 19 python3 -I tools/die_plan/s81_leaf_conns.py $f --repo repo --types $TY --out $D/pm_$n.json > $D/pm_$n.log 2>&1)
  (cd $PM && nice -n 19 python3 -I tools/die_plan/route_supply.py $f --die s81 --repo $PR --types $TY --core-conns $D/pm_$n.json --release-cache /srv/opentallas-scratch2/claude/plan-route-1/release_cache.json --out $D/rs_$n > /dev/null 2>&1)
  python3 -I -c "
import json
r=json.load(open('$D/rs_$n/route_supply_s81.json'))['rows'][0]
print('$n PM route_supply', r['verdict'], 'p99', r['worst'].get('p99'), r['flag_regions'], 'stbits', r['station_bits'], {k:v['p99'] for k,v in r['regions'].items() if v['p99']>0.8})"
done
X=/srv/opentallas-scratch3/claude/explorer-script/tools/fleet_viz/explorer_render.py
nice -n 19 python3 -I $X type --plan $D/final_plan.json --type $TY --repo . --supply --release-cache /srv/opentallas-scratch2/claude/plan-route-1/release_cache.json --out $D/ex >/dev/null 2>&1
for f in $L4/t73s4/ex/type_$TY.links.tsv $D/ex/type_$TY.links.tsv; do awk -F"\t" "NR>1{if(\$10>m)m=\$10; b+=\$14; if(\$12==\"over\")o++; bm+=\$11} END{printf \"explorer over=%d maxhop=%.1f bypass=%d bitmm=%.0f\n\", o,m,b,bm}" $f; done
echo ST7_DONE
