"""Recover all missing-lane driver groups from existing full latency output (not truncated report examples).
usage: unplanned_census.py bind_latency.json OUT.json
"""
import collections,json,sys
p=json.load(open(sys.argv[1]));pairs=collections.defaultdict(collections.Counter)
for l in p['buses']:
 if l['lane'] is not None:continue
 for b in l['source_bits']:
  assert b[0]=='leaf',b
  pairs[(l['src'],l['dst'])][b[1]+'.'+b[2]]+=1
out={'status':'Existing selected-source diagnosis; no lane insertion/latency/plan change',
 'pairs':[{'src':s,'dst':d,'bits':sum(c.values()),'drivers':dict(c)} for (s,d),c in sorted(pairs.items())]}
out['total_bits']=sum(q['bits'] for q in out['pairs']);out['pair_count']=len(out['pairs'])
open(sys.argv[2],'w').write(json.dumps(out,indent=1)+'\n')
print(out['pair_count'],out['total_bits'])
