import json,sys
r=json.load(open(sys.argv[1]))
for x in r:
  if x['role']=='sequential' and 'u_cen' in x['driver']: print(x['loads'],x['driver'])
seq=[x for x in r if x['role']=='sequential' and 'u_cen' not in x['driver']]
import re,collections
g=collections.OrderedDict()
for x in seq:
  k=re.sub(r'\[\d+\]','[]',x['driver']); g.setdefault(k,[]).append(x['loads'])
for k,v in g.items(): print(len(v),max(v),k)
