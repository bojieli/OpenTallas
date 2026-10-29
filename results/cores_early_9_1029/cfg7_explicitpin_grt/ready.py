import json,sys,collections,csv,re
plan=json.load(open(sys.argv[1])); own=sys.argv[2]
st={}; tst={}
for r in csv.reader(open(own),delimiter='\t'):
    if len(r)>4 and r[0]=='s81':
        (st if r[2] in('core','macro') else tst)[r[1]]=r[3]
T=plan['partition_types']
def hc(t):
    h=t.get('hard_cores') or []
    out=collections.Counter()
    if isinstance(h,dict): h=list(h.values())
    for x in h:
        m=x.get('module') if isinstance(x,dict) else x
        out[m]+=1
    return out
fams=collections.defaultdict(list); blockers=collections.Counter(); ready=[]
for tn,s in tst.items():
    if s!='NEEDS-KIT': continue
    t=T[tn]; c=hc(t)
    miss=sorted(m for m in c if st.get(m)!='SIGNED')
    fam=re.sub(r'__t\d+$','',tn)
    fams[fam].append((tn,len(c),miss))
    for m in miss: blockers[m]+=1
    if not miss: ready.append(tn)
print('NEEDS-KIT types',sum(len(v) for v in fams.values()),'ready(all hard cores SIGNED):',len(ready),ready[:20])
for f,v in sorted(fams.items(),key=lambda kv:-len(kv[1])):
    print(f, 'n',len(v),'hc/type',sorted(set(x[1] for x in v)),'types w/ all cores signed',sum(1 for x in v if not x[2]), 'top missing',collections.Counter(m for x in v for m in x[2]).most_common(4))
print('BLOCKING cores (types blocked):')
for m,n in blockers.most_common(25): print(' ',n,m,st.get(m,'?'))
