import sys,collections,re
f=sys.argv[1]; G=4800
cnt={'M6':collections.Counter(),'M8':collections.Counter(),'M4':collections.Counter()}
netsat=collections.defaultdict(collections.Counter)
net=None
for l in open(f):
    l=l.strip()
    if not l or l=='(' : continue
    if l==')': net=None; continue
    p=l.split()
    if len(p)==1: net=p[0]; continue
    L=p[4]
    if L not in cnt: continue
    x0,y0,x1,y1=map(int,p[:4])
    for gx in range(x0//G,(x1-1)//G+1):
        for gy in range(y0//G,(y1-1)//G+1):
            cnt[L][(gx,gy)]+=1
            if L!='M4': netsat[(L,gx,gy)][re.sub(r'\[\d+\]','',re.sub(r'_\d+(?=$|_)','_#',net))[:40]]+=1
for L in ('M6','M8'):
    c=cnt[L]; top=c.most_common(12)
    print(L,'gcells used',len(c),'max',top[0] if top else None)
    for (gx,gy),n in top[:8]:
        print('  %s gcell x=%.1f y=%.1f n=%d'%(L,gx*4.8,gy*4.8,n), netsat[(L,gx,gy)].most_common(4))
    # clusters: count gcells with n>=60
    hot=[k for k,n in c.items() if n>=50]
    xs=collections.Counter(int(k[0]*4.8//1000) for k in hot); ys=collections.Counter(int(k[1]*4.8//1000) for k in hot)
    print('  gcells>=50 guides',len(hot),'by x-mm',sorted(xs.items())[:30],'by y-mm',sorted(ys.items())[:30])
