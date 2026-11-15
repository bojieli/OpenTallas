import sys,collections
f=sys.argv[1]; lo=int(round(float(sys.argv[2])*1000))%4320; want=sys.argv[3] if len(sys.argv)>3 else None
P=4320; G=570
def legal(r):
    a=r*G; b=a+G; n=0
    t=((a-32+63)//64)*64+32
    while t<b:
        m=(t-lo)%P  # position relative to VSS bottom
        # stripes [0,288],[384,672]; wire [m-16,m+16], spacing 32
        ok=True
        for s0,s1 in ((0,288),(384,672),(-P,288-P),(384-P,672-P),(P,P+288)):
            if m+16+32> s0 and m-16-32 < s1: ok=False
        n+= ok; t+=64
    return n
cache={}
tot=0; byleg=collections.Counter(); longs=collections.Counter(); net=None; hits=[]
for line in open(f):
    s=line.split()
    if len(s)==1:
        if s[0] not in '()': net=s[0]
        continue
    if len(s)!=5: continue
    if want and want in net: hits.append(line.strip())
    if s[4]!='M6': continue
    x1,y1,x2,y2=map(int,s[:4]); w=x2-x1
    if w<=G: continue
    for r in range(y1//G,(y2+G-1)//G):
        if r not in cache: cache[r]=legal(r)
        k=min(cache[r],2); tot+=w; byleg[k]+=w
        if w>5*G: longs[k]+=1
rows=collections.Counter(min(legal(r),2) for r in range(0,2000))
print('row share by legal tracks (0,1,>=2):',[round(100*rows[k]/2000,1) for k in (0,1,2)])
print('M6 guide um',round(tot/1000),'in rows with 0 legal',round(byleg[0]/1000),'1 legal',round(byleg[1]/1000),'pct0', round(100*byleg[0]/tot,2),'pct1',round(100*byleg[1]/tot,2),'long(>5gcell) guides in 0-rows',longs[0],'1-rows',longs[1])
for h in hits[:30]: print('NET',h)
