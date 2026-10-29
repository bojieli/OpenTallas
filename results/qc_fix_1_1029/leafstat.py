import sys,collections,statistics as st
for f in sys.argv[1:]:
    L=collections.defaultdict(list)
    for l in open(f):
        p=l.split(); L[p[1]].append(abs(float(p[2])-float(p[5]))+abs(float(p[3])-float(p[6])))
    mx=sorted((max(v),k,len(v)) for k,v in L.items())
    allv=[x for v in L.values() for x in v]
    bt=[x for l in open(f) for p in [l.split()] if p[4].startswith('btcap') for x in [abs(float(p[2])-float(p[5]))+abs(float(p[3])-float(p[6]))]]
    print(f.split('/')[-1], 'leaves',len(L),'sink dist med %.1f p99 %.1f max %.1f'%(st.median(allv),sorted(allv)[int(.99*len(allv))],max(allv)),
          'leaves w/ max>30um:',sum(m>30 for m,_,_ in mx),'btcap max %.1f'%max(bt), 'worst', [(k,round(m,1),n) for m,k,n in mx[-4:]])
