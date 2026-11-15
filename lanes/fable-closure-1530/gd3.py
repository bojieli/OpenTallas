import sys,collections,re
f=sys.argv[1]; lo=int(round(float(sys.argv[2])*1000))%4320
P=4320; G=570
def legal(r):
    a=r*G; b=a+G; n=0
    t=((a-32+63)//64)*64+32
    while t<b:
        m=(t-lo)%P; ok=True
        for s0,s1 in ((0,288),(384,672),(-P,288-P),(384-P,672-P),(P,P+288)):
            if m+48> s0 and m-48 < s1: ok=False
        n+=ok; t+=64
    return n
net=None; out=[]
for line in open(f):
    s=line.split()
    if len(s)==1:
        if s[0] not in '()': net=s[0]
        continue
    if len(s)!=5 or s[4]!='M6': continue
    x1,y1,x2,y2=map(int,s[:4]); w=x2-x1
    if w<=5*G: continue
    for r in range(y1//G,(y2+G-1)//G):
        if legal(r)==0: out.append((net,x1,y1,x2,y2,w))
fam=collections.Counter()
for n,*_ in out:
    k=re.sub(r'\d+','#',n.split('/')[0])[:28] if '/' in n else re.sub(r'\d+','#',n)[:20]
    fam[k]+=1
print(len(out),'long M6 guides in 0-track rows; len um min/med/max', sorted(o[5] for o in out)[0]/1000, sorted(o[5] for o in out)[len(out)//2]/1000, sorted(o[5] for o in out)[-1]/1000)
print(fam.most_common(12))
print('y mod gcell-row sample', sorted(set(o[2]//G for o in out))[:12])
for o in out[:6]: print(o)
