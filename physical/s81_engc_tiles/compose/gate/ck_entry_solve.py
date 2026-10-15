import sys, itertools, numpy as np
f=sys.argv[1]; S={};H={}
for l in open(f):
    w=l.split()
    if w[:1]!=['PAIR'] or w[3]=='WNS': continue
    (S if w[2]=='max' else H)[(w[3],w[4])]=float(w[5])
ch=['u_win','u_io','u_sink','u_ws','u_lkp','u_pb0','u_pb1','u_pb2']
N0=dict(zip(ch,map(int,sys.argv[2].split(','))))
ST,SF=float(sys.argv[3]),float(sys.argv[4]); HM=float(sys.argv[5]) if len(sys.argv)>5 else 30
R=range(-3,4)
grid=np.array(list(itertools.product(R,repeat=8)),dtype=np.int8)
ok=np.ones(len(grid),bool)
for i,c in enumerate(ch): ok&=(grid[:,i]+N0[c]>=0)
idx={c:i for i,c in enumerate(ch)}
LEAF=dict(zip(ch,map(float,sys.argv[6].split(','))))
leaf=np.stack([grid[:,i]*ST+LEAF[c] for i,c in enumerate(ch)],1)
SP=float(sys.argv[7])
ok&=(leaf.max(1)-leaf.min(1)<=SP)
grid=grid[ok]; leaf=leaf[ok]
best=None
for dV in range(-200,201,10):
    mn=np.full(len(grid),1e9); hm=np.full(len(grid),1e9)
    for (a,b),s in S.items():
        da=grid[:,idx[a]] if a in idx else 0; db=grid[:,idx[b]] if b in idx else 0
        v=s-(da-db)*ST + (dV if b=='OUT' else 0) - (dV if a=='IN' else 0)
        mn=np.minimum(mn,v)
        h=H[(a,b)]+(da-db)*SF - (0.79*dV if b=='OUT' else 0) + (0.79*dV if a=='IN' else 0)
        if a!='IN': hm=np.minimum(hm,h)
    mn=np.where(hm>=HM,mn,-1e9)
    # tie-break: fewest stage changes
    j=np.lexsort((np.abs(grid).sum(1),-mn))[0]
    if best is None or mn[j]>best[0]: best=(mn[j],dV,grid[j].copy(),hm[j])
print('best min setup slack (route SDC, unc 123):',round(best[0],1),'dV',best[1],'d',dict(zip(ch,best[2].tolist())),'min hold FF',round(best[3],1))
print('leaf spread',round(float((best[2]*ST+np.array([LEAF[c] for c in ch])).max()-(best[2]*ST+np.array([LEAF[c] for c in ch])).min()),1))
print('N:',{c:N0[c]+int(d) for c,d in zip(ch,best[2])})
