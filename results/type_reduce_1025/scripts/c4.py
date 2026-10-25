import json,collections,re,statistics
exec(open('/tmp/trx/c2.py').read().split('G=collections')[0])
def nn2(n): return re.sub(r'kv_waddr_[nesw]','kv_waddr_X',nn(n)).replace('u_tail_sink_rst_n','rst_n')
G=collections.defaultdict(list)
for r in R: G[r['ms']].append(r)
def pos(r):
    d={}
    for p in r['pins']: d[nn2(p['name'])]=(float(p['x']),float(p['y']),p.get('layer'))
    return d
def fc(r,x,y):
    w,h=r['w'],r['h'];dd={'W':x,'E':w-x,'S':y,'N':h-y};return min(dd,key=dd.get)
print('master|ntabs|medoid p50/p90/max um|face-change% vs medoid|w x h')
for ms,L in sorted(G.items(),key=lambda x:-len(x[1])):
    P=[pos(r) for r in L]
    tabs={tuple(sorted(p.items())) for p in P}
    if len(tabs)<2: continue
    U=[dict(t) for t in tabs]
    best=None
    for c in U:
        ds=[];fch=0;n=0
        for u in U:
            for k,v in u.items():
                if k in c:
                    ds.append(abs(v[0]-c[k][0])+abs(v[1]-c[k][1]));n+=1
                    fch+= fc(L[0],v[0],v[1])!=fc(L[0],c[k][0],c[k][1])
        s=sum(ds)
        if best is None or s<best[0]: best=(s,ds,fch/n)
    ds=sorted(best[1]);q=lambda f:ds[int(f*(len(ds)-1))]
    print(ms,'|',len(U),'| %.0f/%.0f/%.0f'%(q(.5),q(.9),ds[-1]),'| %.0f%%'%(100*best[2]),'|',L[0]['w'],'x',L[0]['h'])
print('\n--- with per-instance orient of the template (R0/MX/MY/R180) ---')
def tr(v,o,w,h):
    x,y=v[0],v[1]
    if o in('MY','R180'):x=w-x
    if o in('MX','R180'):y=h-y
    return x,y
tot_old=tot_new=0
for ms,L in sorted(G.items(),key=lambda x:-len(x[1])):
    P=[pos(r) for r in L]
    tabs={tuple(sorted(p.items())) for p in P}
    if len(tabs)<2: continue
    U=[dict(t) for t in tabs]; w,h=L[0]['w'],L[0]['h']
    best=None
    for c in U:
        ds=[];fch=0;n=0
        for u in U:
            bo=None
            for o in ('R0','MX','MY','R180'):
                dd=[];f=0
                for k,v in u.items():
                    if k in c:
                        cx,cy=tr(c[k],o,w,h);dd.append(abs(v[0]-cx)+abs(v[1]-cy));f+=fc(L[0],v[0],v[1])!=fc(L[0],cx,cy)
                if bo is None or sum(dd)<sum(bo[0]): bo=(dd,f)
            ds+=bo[0];fch+=bo[1];n+=len(bo[0])
        if best is None or sum(ds)<best[0]: best=(sum(ds),ds,fch/n)
    ds=sorted(best[1]);q=lambda f:ds[int(f*(len(ds)-1))]
    print(ms,'| %.0f/%.0f/%.0f'%(q(.5),q(.9),ds[-1]),'| %.0f%%'%(100*best[2]))
