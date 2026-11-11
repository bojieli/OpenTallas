#!/bin/bash
# pipe.sh NAME : quad delta (env GAP JX RQ QY0 QY1) -> station_resite -> ft strip -> ft_sites_unblock -> route_supply (traced) -> G0
set -u; N=$1; W=/srv/opentallas-scratch3/claude/cpl-kv-pv-3; R=$W/repo; P=physical/die_plan/qwen_kvsys/plan_of_record
RS=/srv/opentallas-scratch2/claude/plan-route-1/watch/tools/die_plan/route_supply.py; BASE=/srv/opentallas-scratch2/claude/dkv98/kv1200/plan_c.json
cd $W; L=$W/pipe_$N.log; exec >>$L 2>&1; echo "== $(date) $N GAP=$GAP JX=$JX RQ=$RQ QY0=$QY0 QY1=$QY1"
nice -n 19 python3 -I quad_delta.py $BASE plan_$N.json delta_kv_pv_$N.json | tail -1 || exit 1
T=$(python3 -I -c "import json;print(','.join(json.load(open('delta_kv_pv_$N.json'))))")
mkdir -p ${N}_pd; ln -sf $W/plan_$N.json ${N}_pd/die_plan.json
nice -n 19 python3 -I repo/tools/die_plan/station_resite.py ${N}_pd ${N}_rs --types $T --reach 405 --jobs 4 > rs_$N.log 2>&1 || { echo resite FAIL; exit 1; }
grep "regs in body" rs_$N.log | sort -u
nice -n 19 python3 -I ft_strip.py ${N}_rs/die_plan.json plan_${N}_strip.json delta_kv_pv_$N.json | awk '{print $1,$5}' | tr '\n' ' '; echo
(cd $R && nice -n 19 python3 -I tools/die_plan/ft_sites_unblock.py $W/plan_${N}_strip.json $W/plan_${N}_ft.json $T --report $W/ftu_$N.json > $W/ftu_$N.log 2>&1) || { echo ftu FAIL; tail -3 ftu_$N.log; exit 1; }
python3 -I -c "import json;r=json.load(open('ftu_$N.json'));import collections;print('ftu slots',len(r),'stations_added',sum(x.get('stations_added',0) for x in r),'infeasible',sum(1 for x in r if 'infeasible' in x))"
cp plan_${N}_ft.json $R/$P/plan_c_$N.json; md5sum plan_${N}_ft.json
(cd $R && nice -n 19 python3 -I $RS --plan $P/plan_c_$N.json --repo . --types kv3_pv_v2,kv3_pv_v4n --release-cache /srv/opentallas-scratch2/claude/plan-route-1/release_cache.json --core-conns $W/cc_traced.json --out $W/rsup_$N > $W/rsup_$N.log 2>&1)
awk -F'\t' 'NR>1 && $2 ~ /kv3_pv/ {print "RS",$2,$3,$5,$6,$8,"core_H",$12,"street_H",$16,"street_V",$17,"ring_H",$18}' rsup_$N.log
(cd /srv/opentallas-scratch3/claude/cpl-kv-pv-g0/repo && cp $W/plan_${N}_ft.json $P/plan_c_$N.json && nice -n 19 python3 -I tools/die_plan/check.py $P/plan_c_$N.json --quiet --out $W/g0_$N > $W/g0_$N.log 2>&1)
grep "^G0 " g0_$N.log | cut -c1-80; echo "PIPE_DONE $N"
