import json,sys,collections,re
D='/home/ubuntu/wt/codex-shared-core-0733/results/fallback_land_0733/'
def load(die):
    d=json.load(open(D+die+'.json'));G=collections.defaultdict(set);N=set()
    for k in d['partition_pair_census']:
        a,b=k.split(' -> ');G[a].add(b);N|={a,b}
    return G,N
def bfs(G,S):
    dist={s:0 for s in S};q=collections.deque(S)
    while q:
        u=q.popleft()
        for v in G[u]:
            if v not in dist: dist[v]=dist[u]+1;q.append(v)
    return dist
Q={'qc':[('tt_ctlm','^c_'),('tt_ctlm','^sl_.*_su_c'),('^c_','tt_ctlm'),('^c_','^sl_.*_su'),('^sl_.*_su_c','coll_core'),('coll_core','^sl_.*_su_c'),('coll_core','^c_'),('^c_','coll_core'),('ucie_kv','^sl_.*_fe'),('^sl_.*fw','ucie_kv'),('ucie_kv','^c_'),('^c_','ucie_kv')],
 's81':[('^lk_','^f[EW]'),('^f[EW]','^lk_'),('^s_.*_C$','^f[EW]'),('^f[EW]','^s_.*_C$'),('^lk_','^lk_'),('eng','^f[EW]'),('^f[EW]','eng'),('seqhost','^f[EW]')],
 'head':[('^sp','^t'),('^t','^sp'),('^lk_','^sp'),('^sp','^lk_'),('ctl','^t'),('^lk_','^t[EW]\\d+o10'),('^t[EW]\\d+b0$','^lk_')],
 'kv':[('hub_C','^pv_'),('^pv_','hub_C'),('^io_','^pv_'),('^pv_','^io_'),('^phy_','^pv_'),('^pv_','^phy_'),('hub_C','^pc_'),('^pc_','hub_C'),('^io_','^pc_')],
 'hbm':[('root','^NE_b'),('^NE_b','root'),('PHY_N','^NE_sm'),('^NE_sm','root'),('root','^vsN'),('^NW_io','^NE_sm'),('^NE_sm','^NW_io')]}
for die,qs in Q.items():
    G,N=load(die)
    for s,t in qs:
        S=[n for n in N if re.search(s,n)];T=[n for n in N if re.search(t,n)]
        # worst over targets of distance from nearest source (broadcast), and worst source
        worst=0;
        for src in S:
            dd=bfs(G,[src]);w=max(dd.get(x,999) for x in T);worst=max(worst,w)
        best=min(max(bfs(G,[src]).get(x,999) for x in T) for src in S)
        near=bfs(G,S); nw=max(near.get(x,999) for x in T)
        print(f'{die:5s} {s:>14s} -> {t:<14s} |S|={len(S):3d} |T|={len(T):3d} nearest-src-worst={nw:3d} best-single-src={best:3d} worst-src={worst}')
