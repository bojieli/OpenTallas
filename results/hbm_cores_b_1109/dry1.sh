#!/bin/bash
set -u
S=/srv/opentallas-scratch3/claude/dkv95_src_p4; P=/srv/opentallas-scratch2/claude/dkv95/plan_p4; B=/srv/opentallas-scratch2/claude/dkv95/bind5; D=/srv/opentallas-scratch2/claude/dkv96/dry1
cd $D; rm -rf plan_ov; cp -al $P plan_ov; find plan_ov -type d -exec chmod u+w {} +; rm -f plan_ov/plan_c.json
python3 -I - <<'P'
import json,os
r=json.load(open('/srv/opentallas-scratch2/claude/dkv95/plan_p4/plan_c.json'))
V='/srv/opentallas-scratch2/claude/dkv96/dry1/views'
ty=r['partition_types']; n=0
for k,t in (ty.items() if isinstance(ty,dict) else [(x['name'],x) for x in ty]):
    for hc in t.get('hard_cores') or []:
        if isinstance(hc,dict) and hc.get('module') in os.listdir(V):
            m=hc['module']; hc['lef']=f'{V}/{m}/{m}.lef'; n+=1
json.dump(r,open('/srv/opentallas-scratch2/claude/dkv96/dry1/plan_ov/plan_c.json','w'))
print('overlay hard_cores',n)
P
cd $S
for T in kv3_pc__cl254f2e73 kv3_hub_Eo; do
  rm -rf $D/out/$T; mkdir -p $D/out/$T
  python3 -I tools/die_plan/bind.py kit-rtl $D/plan_ov/plan_c.json --out $B --asbuilt $P/asbuilt.json --type $T --kit $D/out/$T > $D/$T.log 2>&1; echo "$T rc $?" >> $D/rc.txt
done
