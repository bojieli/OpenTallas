"""Scope ONE actual native M7/VIA78/M8 contact per bound macro supply term.
Keep all original fragment failures. This closes logical-term geometry only,
not distributed pin coverage, current capacity or IR.
"""
import json,collections
from pathlib import Path
K=Path('native_pg');p=json.load(open(K/'direct/join_plan.json'));groups=collections.defaultdict(list)
for c in p['contacts']:groups[c['inst'],c['pin']].append(c)
contacts=[];failed=[]
for t in p['terms']:
 assert t['net']==t['existing_bound_net'] and t['net'] in ('VDD','VSS'),t
 key=t['inst'],t['pin']
 if not groups[key]:failed.append(t);continue
 def area(c):a,b,x,y=c['native_pin_dbu'];return(x-a)*(y-b)
 contacts.append(max(groups[key],key=lambda c:(area(c),-c['shape'])))
assert len(contacts)+len(failed)==320
out=dict(dbu=p['dbu'],contacts=contacts,failed=failed,terms=p['terms'],scope='SCOPED_CONNECTIVITY_ONLY one VIA78 per actual supply term; original198fragment misses retained in direct/join_plan.json')
json.dump(out,open(K/'selected_plan.json','w'),separators=(',',':'));json.dump(dict(dbu=p['dbu'],paths=[],failed=[]),open(K/'empty_bridges.json','w'))
print('SELECTED',len(contacts),'TERMS_WITHOUT_CONTACT',len(failed),'ORIGINAL_FRAGMENT_MISSES',len(p['failed']))
