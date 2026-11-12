#!/bin/bash
# run_r2all.sh : R2-APRON on all 5 col_h9_r2 types of ready7 -> aug4/plan_r2all.json + route_supply + G0 diff
W=/srv/opentallas-scratch2/claude/vislayout2-s81/w; R=$W/../repo; cd $W
rm -rf r2all; mkdir -p r2all
TS="col_h9_r2__t1__cl774acf45 col_h9_r2__t1__cl87f3ff59 col_h9_r2__t1__clb8d86cd5 col_h9_r2__t1__clc9ad8f7e col_h9_r2__t1__clce45cab5"
cp ready7.json aug4/all_tmp.json
for T in $TS; do python3 -I ../tools/move_taps.py aug4/all_tmp.json aug4/all_tmp.json $T clk_t20=1425.6,650 clk_t23=1425.6,700 clk_t24=1425.6,750 >/dev/null; python3 -I ../tools/seed_r2f.py aug4/all_tmp.json $T r2all/seed_$T.json >/dev/null; done
python3 -I -c "
import json,glob;d={}
for f in glob.glob('r2all/seed_*.json'): d.update(json.load(open(f)))
json.dump(d,open('r2all/seed.json','w'),indent=1)"
OMP_NUM_THREADS=8 python3 -I $R/tools/die_plan/core_place_vl2.py $W/aug4/all_tmp.json --die s81 --repo $R --types $(echo $TS | tr " " ",") --seed r2all/seed.json --no-search --gap auto --accept-timing --out-plan $W/aug4/plan_r2all_pre.json --event $W/r2all/ev.json --svg $W/r2all/svg > r2all/log.txt 2>&1
grep -E "seed:|^col" r2all/log.txt
cp aug4/plan_r2all_pre.json aug4/plan_r2all.json
for T in $TS; do python3 -I ../tools/move_taps.py aug4/plan_r2all.json aug4/plan_r2all.json $T clk_t20=724.92,452.16 clk_t23=596.16,730.04 clk_t24=339.12,613.44 >/dev/null; python3 -I ../tools/tapcheck.py $R aug4/plan_r2all.json $T | grep ADDED; done
for T in $TS; do python3 -I $R/tools/die_plan/route_supply.py $W/aug4/plan_r2all.json --die s81 --repo $R --types $T --grt-halving edge_outline --out $W/rs/all_$T >/dev/null 2>&1; tail -1 rs/all_$T/route_supply_s81.tsv | cut -f2,3,4,5,8,9,10; done
d=$W/g0dir_v7; cp aug4/plan_r2all.json $d/plan.json; (cd $R && python3 -I tools/die_plan/check.py $d/plan.json --out $W/g0/r2all --quiet > $W/g0/r2all.log 2>&1); /usr/bin/tail -n 1 g0/r2all.log | cut -c1-120
python3 -I -c "
import json,collections,re
a=json.load(open('g0/base/g0_report.json'));b=json.load(open('g0/r2all/g0_report.json'))
E=lambda r:set(f['msg'] for f in r['findings'] if f['level']=='ERROR')
W=lambda r:[f['msg'] for f in r['findings'] if f['level']=='WARN' and 'col_h9_r2' in f['msg']]
print('err base',len(E(a)),'new',len(E(b)),'added',sorted(E(b)-E(a))[:5])
print('r2 warns base',len(W(a)),'new',len(W(b)))
k=lambda m: re.sub(r'cl[0-9a-f]{8}','clX',re.sub(r'>= [0-9.]+ um','>= # um',m))[:150]
ca=collections.Counter(k(m) for m in W(a)); cb=collections.Counter(k(m) for m in W(b))
for key in sorted(set(ca)|set(cb), key=lambda x:-(cb[x]-ca[x])):
  if cb[key]>ca[key]: print(ca[key],'->',cb[key],key)
" | head -20
sha256sum aug4/plan_r2all.json | cut -c1-12
