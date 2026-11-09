#!/bin/bash
# TYPE-SAFE-3 S81 relay event on v3b 48f8eba4984a with cbind3b bound RTL
set -u
B=/srv/opentallas-scratch2/claude/type-safe-3b
cd $B/wt
python3 -I - <<'P'
import json,os
B=os.environ.get('B','/srv/opentallas-scratch2/claude/type-safe-3b')
d=json.load(open(f'{B}/s81_v3b.json'))
out=open(f'{B}/s81_bound.tsv','w');n=0
for t in d['partition_types']:
    p=f'{B}/s81_cbind3b_rtl/{t}.sv'
    if os.path.exists(p):
        out.write(f'{t}\t{p}\n');n+=1
print('bound',n,'of',len(d['partition_types']))
P
A=/srv/opentallas-scratch3/claude/codex-wave-bind-1106/src_28fc7/physical/die_plan/s81/bind/asbuilt_b178_coll_h2_2249.json
ls -la $A
NT=$(python3 -I -c "
import json;d=json.load(open('$A'));print(','.join(d.get('internal_stations_types') or d.get('asbuilt',{}).get('internal_stations_types') or []))")
echo native-types: "$NT" | cut -c1-300
prlimit --as=40000000000 python3 -I -B tools/die_plan/ts_relay_event.py $B/s81_v3b.json $B/s81_v3b_ts3.json $B/s81_v3b_ts3_event.json \
  --pins-root /srv/opentallas-scratch3/claude/kw35/src_c303p/physical/die_plan/s81 \
  --bound-list $B/s81_bound.tsv --skip-types "$(cat $B/signed_s81.txt)" --native-types "$NT" 2>&1 | tail -15 | cut -c1-400
