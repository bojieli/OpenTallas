import json,collections,math,statistics as st
T=833.0
d=json.load(open('/home/ubuntu/coord/lanes/evidence/head_reset_model_1117/feasibility_r4.json'))
R=d['rows']
print(len(R), collections.Counter(r['bus'] for r in R))
F=[r for r in R if r['ff_hold']<0]
def q(v,p): v=sorted(v); return v[min(len(v)-1,int(p*len(v)))]
sk=[r['tt_capture']-r['tt_launch'] for r in R]
print('skew all p10/p50/p90/min/max',[round(q(sk,p)) for p in (0.1,0.5,0.9)],round(min(sk)),round(max(sk)))
W=[r['tt_setup']+r['ff_hold'] for r in R]
print('window setupTT+holdFF min/p10/p50/max',round(min(W)),round(q(W,.1)),round(q(W,.5)),round(max(W)))
print('tt_setup<0:',sum(r['tt_setup']<0 for r in R),' tt_setup<-42:',sum(r['tt_setup']<-42 for r in R))
# data delay estimate: hold = launch + dd - capture  => dd = tt_hold + skew
dd=[r['tt_hold']+r['tt_capture']-r['tt_launch'] for r in R]
print('dd(TT min path incl clk-q, minus th) p10/50/90/max',[round(q(dd,p)) for p in (0,0.1,0.5,0.9)],round(max(dd)))
def best(r,step,G=0):
    # choose integer h, capture edge moved earlier by h*step
    b=None
    for h in range(-8,9):
        s=r['tt_setup']-h*step; ho=r['ff_hold']+h*step
        m=min(s+42,ho)
        if b is None or m>b[0]: b=(m,h,s,ho)
    return b
for name,step in (('whole',T),('half',T/2)):
    res=[best(r,step) for r in R]
    resF=[best(r,step) for r in F]
    print(name,'ALL714 infeasible',sum(x[0]<0 for x in res),'min margin',round(min(x[0] for x in res),1),'margin<50',sum(x[0]<50 for x in res),'<100',sum(x[0]<100 for x in res),'<150',sum(x[0]<150 for x in res))
    print(name,'  h hist(fails)',sorted(collections.Counter(x[1] for x in resF).items()))
    print(name,'  h hist(all)',sorted(collections.Counter(x[1] for x in res).items()))
# mechanism classification of the 530
cl=collections.Counter()
for r in F:
    s=r['tt_capture']-r['tt_launch']; need=-r['ff_hold']
    w=best(r,T); hf=best(r,T/2)
    if r['tt_setup']<-42: c='REVERSE(setup neg)'
    elif w[1]!=0 and w[0]>=100: c='A whole-cycle phase alias (integer relabel, margin>=100)'
    elif w[1]!=0 and w[0]>=0: c='B whole-cycle relabel thin (<100)'
    elif hf[1]!=0 and hf[0]>=100: c='C sub-cycle phase (half-cycle entry)'
    elif need<=120: c='D short path / small skew (<=120 ps pad)'
    else: c='E other'
    cl[c]+=1; r['_c']=c
print(cl)
# by type pair
tp=collections.Counter((r['src_type'],r['dst_type'],r['bus']) for r in F)
print(len(tp),'type-pair classes; top',tp.most_common(12))
# setup-negative rows anywhere
for r in sorted(R,key=lambda r:r['tt_setup'])[:16]: print(r['seam'],round(r['tt_setup']),round(r['tt_hold']),round(r['ff_hold']),round(r['tt_capture']-r['tt_launch']))
# dst-type uniformity: can one half-step h serve all instances of (dst_type,bus,dst_cell)?
grp=collections.defaultdict(list)
for r in R: grp[(r['dst_type'],r['bus'],r['dst_cell'])].append(r)
okw=okh=0;n=0
for k,v in grp.items():
    n+=1
    for step,nm in ((T,'w'),(T/2,'h')):
        ok=any(all(min(r['tt_setup']+42-h*step, r['ff_hold']+h*step)>=0 for r in v) for h in range(-8,9))
        if nm=='w': okw+=ok
        else: okh+=ok
print('dst entry groups',n,'uniform whole ok',okw,'uniform half ok',okh)
print('dst types',len(set(r['dst_type'] for r in R)),'dst parts',len(set(r['dst'] for r in R)))
