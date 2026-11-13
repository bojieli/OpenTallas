#!/bin/bash
# DIE-HBM-102 11-13: pEv11a = pEv10 (b334c92f7a84) + d1 capture-tap latches (q_spb1/vsN1/vsN2) + d3 NW_io spread + d4 fabric rows
set -e
W=/srv/opentallas-scratch2/claude/die-hbm-102; P=$W/plans; O=${1:-pEv11a}; SC=$W/scripts
K=/srv/opentallas-scratch2/claude/kw45/src_hbm_main_9fc09952cd_q0g_p18
rm -rf $P/$O; cp -a $P/pEv10 $P/$O
python3 -I $SC/d1_captap.py $P/pEv10/die_plan.json $P/$O/s1.json
python3 -I $SC/d3_nwio.py $P/$O/s1.json $P/$O/s3.json
python3 -I $SC/d4_rows.py $P/$O/s3.json $P/$O/s4.json $K/tools/die_plan
(cd $K; python3 -I tools/die_plan/ft_nudge.py $P/$O/s4.json $P/$O/die_plan.json $P/$O/nudge_ledger_ev11.json 2>&1 | tail -n 1)
rm -f $P/$O/s1.json $P/$O/s3.json
(cd $K; python3 -I tools/die_plan/gen.py latency $P/$O/die_plan.json --inplace 2>&1 | tail -n 1 | cut -c1-120)
sha256sum $P/$O/die_plan.json | cut -c1-12
python3 -I -c "
import json;a=json.load(open('$P/$O/s4.json'));b=json.load(open('$P/$O/die_plan.json'))
for tn,sn in (('q_b113','L1271x7'),('q_hub_nw','L1219x1')):
  f=lambda d:[s for s in d['partition_types'][tn]['ft_slots'] if s['name']==sn][0]['regs_um']
  print(tn,sn,'nudge kept' if f(a)==f(b) else 'NUDGE MOVED', f(b))
print('NW_io ist same', a['partition_types']['NW_io']['internal_stations']==b['partition_types']['NW_io']['internal_stations'])
la=a['latency']['lanes'];lb=b['latency']['lanes'];print('latency lanes changed',[k for k in lb if la.get(k,{}).get('cycles')!=lb[k].get('cycles')][:20])
"
