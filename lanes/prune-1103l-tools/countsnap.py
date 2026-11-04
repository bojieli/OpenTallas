#!/usr/bin/env python3
# PRUNE-1103L read-only snapshot/compare of credited keys in the counter cache. usage: countsnap.py out.json [baseline.json]
import json,os,sys
c=json.load(open(os.path.expanduser('~/.local/state/fleet-viz/release_tree_plan_cache.json')))
s={'generated':c.get('generated'),'errors':c.get('errors'),'unreachable':c.get('unreachable_hosts')}
for p in c['plans'].values():
    for d in('signed_types','signed_cores','signed_designs'): s[p['die']+'.'+d]=sorted((p.get(d) or {}).keys())
json.dump(s,open(sys.argv[1],'w'))
print(s['generated'],'errors',s['errors'],'unreachable',s['unreachable'],{k:len(v) for k,v in s.items() if '.' in k})
if len(sys.argv)>2:
    b=json.load(open(sys.argv[2])); lost=0
    for k in s:
        if '.' not in k: continue
        d=set(b.get(k,[]))-set(s[k]); a=set(s[k])-set(b.get(k,[]))
        if d: print('LOST',k,sorted(d)); lost+=len(d)
        if a: print('GAIN',k,sorted(a))
    print('LOST TOTAL',lost)
