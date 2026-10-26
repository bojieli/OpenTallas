import json,sys,collections
D='/home/ubuntu/wt/codex-shared-core-0733/results/fallback_land_0733/'
for die in ['qc','s81','head','kv','hbm']:
    d=json.load(open(D+die+'.json'))
    G=collections.defaultdict(set); nodes=set()
    for k in d['partition_pair_census']:
        a,b=k.split(' -> '); G[a].add(b); nodes|={a,b}
    def bfs(s):
        dist={s:0};q=collections.deque([s])
        while q:
            u=q.popleft()
            for v in G[u]:
                if v not in dist: dist[v]=dist[u]+1;q.append(v)
        return dist
    deg=sorted(nodes,key=lambda n:-(len(G[n])+sum(n in G[m] for m in nodes)))
    ecc={n:max(bfs(n).values()) for n in nodes}
    reach={n:len(bfs(n)) for n in nodes}
    full=[n for n in nodes if reach[n]==len(nodes)]
    cen=min(full,key=lambda n:ecc[n]) if full else None
    print(die,'nodes',len(nodes),'edges',sum(len(v) for v in G.values()),'strongly-reach-all',len(full),'radius',ecc[cen] if cen else None,'center',cen,'diameter',max(ecc.values()),'top-degree',deg[:4])
    # distance from named hubs
    for h in [n for n in nodes if any(t in n for t in ('root','hub_C','tt_ctlm','sp0','hub'))][:6]:
        b=bfs(h); print('   from',h,'ecc',max(b.values()),'reach',len(b))
