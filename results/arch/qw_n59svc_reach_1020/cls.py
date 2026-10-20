import json,gzip,re,collections,sys
g=json.load(gzip.open(sys.argv[1]))
N=g['endpoint_nodes'];I=g['instances']
def fam(k):
    n=N[k]; s=n['inst']+'/'+n['pin'] if n['inst']!='PORT' else 'PORT/'+n['pin']
    s=re.sub(r'\\\[\d+\\\]|\[\d+\]','[]',s); s=re.sub(r'_\d+(?=\W|$)','_N',s); s=re.sub(r'\$_[A-Z0-9_]+_','$FF',s)
    return s
L=[]
for a,z in g['edges']:
    pa=N[a]['point'];pz=N[z]['point'];d=abs(pa[0]-pz[0])+abs(pa[1]-pz[1])
    if d>405:L.append((d,a,z))
print(len(L))
c=collections.Counter()
for d,a,z in L:c[(fam(a),fam(z))]+=1
for (a,z),n in c.most_common(80):print(n,a,'->',z)
srcs=collections.Counter(fam(a) for d,a,z in L); dsts=collections.Counter(fam(z) for d,a,z in L)
print('--- distinct src insts',len({N[a]['inst'] for d,a,z in L}),'dst insts',len({N[z]['inst'] for d,a,z in L}))
for d,a,z in sorted(L)[-10:]:print(round(d,1),a,N[a]['point'],'->',z,N[z]['point'])
