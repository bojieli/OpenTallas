#!/bin/bash
set -u
Q=/srv/opentallas-scratch3/claude/type-safe-3b/qc
C=/srv/opentallas-scratch3/claude/codex-qc-compose-1113
cd $Q
python3 -I - <<'P'
import json,os
Q='/srv/opentallas-scratch3/claude/type-safe-3b/qc'
C='/srv/opentallas-scratch3/claude/codex-qc-compose-1113'
d=json.load(open(f'{C}/plan/plan_qc53v4n.json'))
b=open(f'{Q}/bound.tsv','w');n=0;miss=[]
for t,v in d['partition_types'].items():
    m=v.get('module',t)
    for cand in (f'{C}/bind_v4n_hc3_fixed2/rtl/{m}.sv',f'{C}/bind_v4n_hc3_fixed2/rtl/{t}.sv'):
        if os.path.exists(cand):
            b.write(f'{t}\t{cand}\n');n+=1;break
    else: miss.append(t)
print('bound',n,'of',len(d['partition_types']),'miss',miss[:6])
a=json.load(open(f'{C}/src_fixed/physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_hc3.json'))
ist=a.get('internal_stations_types',[])
print('native types',len(ist))
open(f'{Q}/native.txt','w').write(','.join(ist))
P
prlimit --as=24000000000 python3 -I -B tools/die_plan/ts_relay_event.py $C/plan/plan_qc53v4n.json $Q/plan_qc53v4n_ts3.json $Q/event.json \
  --pins-root $C/plan --bound-list $Q/bound.tsv --skip-types "$(cat $Q/skip.txt)" --native-types "$(cat $Q/native.txt)" 2>&1 | tail -6 | cut -c1-500
python3 -I - <<'P'
import json
from collections import Counter
e=json.load(open('/srv/opentallas-scratch3/claude/type-safe-3b/qc/event.json'))
print(e['base_plan_sha256'][:12],e['plan_output_sha256'][:12],e['totals'])
print(sorted(Counter(e['pin_cycle_deltas'].values()).items()), len(e['reported']), e['native_out_types'])
for x in e['edits'][:6]: print(x['type'],x['bus'],x['dir'],x['d_um'],x['need'],x.get('count'),list(x['lanes'].items())[:2])
P
