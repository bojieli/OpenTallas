import sys, random, json
sys.argv=['x','lanes.json','rows103.json','rows_h8b.json']
import replan_est as R
rowset=set(R.A0)|set(R.C0)|{R.mirror(n) for n in R.A0+R.C0}
P={k:v for k,v in R.pairs.items() if k[0] in rowset or k[1] in rowset}
MOVEPEN=float(__import__('os').environ.get('MOVEPEN','0'))
def cost(rect):
    c=sum(MOVEPEN for n in R.A0+R.C0+['NW_b110','NW_b111'] if n in rect and abs(rect[n][0]-R.rect0[n][0])>0.01 or (n in rect and abs(rect[n][1]-R.rect0[n][1])>0.01)); far=0
    dem={}
    for (a,b),(pb,nb) in P.items():
        w=pb+nb; e,g=R.rel(rect[a],rect[b])
        if e>=R.MIN_EDGE:
            if w>e*R.PPU: c+= (w-e*R.PPU)*2.0   # over-subscribed window ~ like 2 mm far
            continue
        c+=w*max(g,1.0)/1000
        if g>R.NEAR: c+=w*1.0; far+=1
    return c
def run(A,C,iters,seed,fixA=(),fixC=()):
    rnd=random.Random(seed)
    cur=(list(A),list(C)); cc=cost(R.apply_rows({'A':cur[0],'C':cur[1]}))
    best=(cc,[list(cur[0]),list(cur[1])])
    T=2000.0
    for i in range(iters):
        r=0 if rnd.random()<0.6 else 1
        L=list(cur[r]); fix=fixA if r==0 else fixC
        idx=[j for j,n in enumerate(L) if n not in fix]
        if rnd.random()<0.5:
            i1,i2=rnd.sample(idx,2); L[i1],L[i2]=L[i2],L[i1]
        else:
            i1,i2=rnd.sample(idx,2); n=L.pop(i1); L.insert(i2,n)
            if any(L[j]!=cur[r][j] and cur[r][j] in fix for j in range(len(L))): continue
        new=(L,cur[1]) if r==0 else (cur[0],L)
        nc=cost(R.apply_rows({'A':new[0],'C':new[1]}))
        import math
        if nc<cc or rnd.random()<math.exp((cc-nc)/T):
            cur=(list(new[0]),list(new[1])); cc=nc
            if cc<best[0]: best=(cc,[list(cur[0]),list(cur[1])])
        T*=0.9995
    return best
