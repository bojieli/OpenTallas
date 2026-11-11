#!/bin/bash
# bf.sh NAME : band strip + per-type band fill (8 parallel) + merge -> plan_NAME_bf.json
N=$1; W=/srv/opentallas-scratch3/claude/cpl-kv-pv-3; cd $W
nice -n 19 python3 -I band_strip.py plan_${N}_ft.json plan_${N}_bs.json delta_kv_pv_$N.json > bs_$N.log
mkdir -p bf_$N; rm -f bf_$N/*
cd repo/tools/die_plan
python3 -I -c "import json;print('\n'.join(json.load(open('$W/delta_kv_pv_$N.json'))))" | xargs -P 8 -I{} sh -c "nice -n 19 timeout 2400 python3 -s $W/bandfill.py $W/plan_${N}_bs.json /srv/opentallas-scratch2/claude/dkv98/kv1200/eW_sidecar.json {} $W/bf_$N/{}.json . > $W/bf_$N/{}.log 2>&1; echo rc=\$? >> $W/bf_$N/{}.log"
cd $W; nice -n 19 python3 -I bandmerge.py plan_${N}_bs.json plan_${N}_bf.json "bf_$N/*.json" > bm_$N.log 2>&1
grep -l "rc=[^0]" bf_$N/*.log > bf_${N}_fail.txt; echo BF_DONE >> bm_$N.log
