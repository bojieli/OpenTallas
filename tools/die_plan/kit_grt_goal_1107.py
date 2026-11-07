#!/usr/bin/env python3
"""Copy a legacy runner with an opt-in GRT-only goal; existing goals keep their paths."""
import argparse, hashlib, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('runner',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
assert a.runner.resolve()!=a.out.resolve(), 'write a private copy, never the original runner'
s=a.runner.read_text();before=hashlib.sha256(s.encode()).hexdigest()
assert s.count('case "$GOAL" in place|cts|route)')==1
s=s.replace('case "$GOAL" in place|cts|route)','case "$GOAL" in place|cts|grt|route)',1)
i=s.index(r'  if [ \$rc = 0 ] && { [ $GOAL = cts ]')
j=s.index(r'  if [ \$rc = 0 ] && [ -f /work/core_infra_post.v ]',i)
body=s[i:j];n=body.count('[ $GOAL = route ]');assert n==6, n
body=body.replace('[ $GOAL = route ]','{ [ $GOAL = route ] || [ $GOAL = grt ]; }')
s=s[:i]+body+s[j:]
# Final finish/abstract/signoff conditions intentionally remain route/finish only.
a.out.write_text(s)
a.out.with_suffix(a.out.suffix+'.profile.json').write_text(json.dumps({'profile':'kit_grt_goal_1107','source_sha256':before,'result_sha256':hashlib.sha256(s.encode()).hexdigest(),'new_goal':'grt','preserved':'CTS hooks, FF structural/post gates, GRT repair/legacy gates','stops_before':'detail route, finish, abstract, signoff','existing_goals_unchanged':True},indent=2)+'\n')
print('PRIVATE_GRT_RUNNER',a.out,'route-guard extensions',n)
