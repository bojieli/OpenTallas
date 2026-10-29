import sys,collections
g=sys.argv[1]; x0,x1=254664,261738
nets=collections.defaultdict(lambda: collections.Counter()); cur=None
for ln in open(g):
    s=ln.split()
    if not s: continue
    if len(s)==1 and s[0] not in "()": cur=s[0]; continue
    if len(s)==5:
        a,b,c,d=map(int,s[:4]); L=s[4]
        if c>x0 and a<x1 and ((17280<d and b<58344) or (90720<d and b<131784)):
            nets[cur][L]+= (min(d,58344 if b<60000 else 131784)-max(b,17280 if b<60000 else 90720))//1000
byL=collections.Counter()
for n,c in nets.items():
    for L,v in c.items(): byL[L]+=1
print("nets with guide in E corridor over macro y-span:",len(nets),"per layer nets:",dict(byL))
m3=sorted(((c.get('M3',0),n) for n,c in nets.items()),reverse=True)[:15]; print("top M3 um:",m3)
