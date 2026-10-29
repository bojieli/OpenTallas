import json,re,sys,collections
r=json.load(open(sys.argv[1]))
c=collections.Counter(); ex={}
for e in r['errors']:
    s=str(e); k=s.split()[0]
    if k=='TIED': k2='TIED '+re.sub(r'\[\d+\]','',s.split()[1]).rsplit('.',1)[-1]
    elif k=='UNPLANNED': k2='UNPLANNED'
    else: k2=k
    c[k2]+=1; ex.setdefault(k2,s[:260])
print('n_errors',r['n_errors'],'unmapped',r['unmapped'],'tied_by_port',len(r.get('tied_by_port',{})))
for k,v in c.most_common(): print(v,k,'|',ex[k])
