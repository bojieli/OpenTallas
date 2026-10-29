#!/usr/bin/env python3
"""DIE-KV-31-SRC: per-net census of plan_access.py output (groups / contacts planned and failed per supply net)."""
import argparse,json,collections
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--out',required=True);a=p.parse_args()
pl=json.load(open(a.plan+'/access_plan.json'));s=json.load(open(a.plan+'/summary.json'))
c=collections.defaultdict(lambda:dict(groups_ok=0,contacts_ok=0,groups_failed=0,contacts_failed=0))
for q in pl['paths']:c[q['net']]['groups_ok']+=1;c[q['net']]['contacts_ok']+=len(q['members'])
for q in pl['failed']:c[q['net']]['groups_failed']+=1;c[q['net']]['contacts_failed']+=len(q['members'])
r=dict(per_net=c,summary=s,failed_examples=pl['failed'][:20],VDDPHY='no std-cell rails in phy_sys_c_ucie; macro pin contacts (sys_c VDDPHY M7 -> M8) are outside plan_access scope')
json.dump(r,open(a.out,'w'),indent=1);print(json.dumps(dict(per_net=c,verdict=s['verdict'])))
