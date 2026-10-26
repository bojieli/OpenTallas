import json,sys,collections,re
def load(p):
    g=json.load(open(p)); m=collections.defaultdict(set)
    for gr in g['landing']:
        for x in gr['members']:
            m[x.get('lane')].add(x['landed_stages'])
    return m
A=load(sys.argv[1]);B=load(sys.argv[2])
print('lanes ref',len(A),'new',len(B),'common',len(set(A)&set(B)))
cls=collections.defaultdict(collections.Counter)
for k in set(A)&set(B):
    dd=max(B[k])-max(A[k])
    c=re.sub(r'[EW]\d','X',k); c=re.sub(r'_\d\d_','_##_',c); c=re.sub(r'\d','#',c)
    cls[c][dd]+=1
for c,v in sorted(cls.items()):
    if any(v2 for v2 in v if v2): print(c, sorted(v.items()))
print('only new lanes', sorted(set(B)-set(A))[:20], len(set(B)-set(A)))
print('only ref lanes', sorted(set(A)-set(B))[:20], len(set(A)-set(B)))
