import json,re,sys
from collections import Counter,defaultdict
p=json.load(open(sys.argv[1]));pos=p['positions'];T=p['targets']
def fam(n):
    n=n.replace('\\','');n=re.sub(r'\[\d+\]','[]',n);n=re.sub(r'\$_.*','',n);n=re.sub(r'/q$','',n);return n[:80]
def d(a,b):return abs(pos[a][0]-pos[b][0])+abs(pos[a][1]-pos[b][1])
def feas(r):
    nb=[x for x in T[r]['src']+T[r]['dst'] if x in pos]
    if not nb:return True,None
    u=[pos[x][0]+pos[x][1] for x in nb];v=[pos[x][0]-pos[x][1] for x in nb]
    su=max(u)-min(u);sv=max(v)-min(v)
    return su<=810 and sv<=810, max(su,sv)/2
bad=defaultdict(list)
for s,t in T.items():
    for a in t['src']:
        if a in T and d(s,a)>405: bad[(fam(a),fam(s))].append((a,s))
for k,L in sorted(bad.items(),key=lambda kv:-len(kv[1]))[:20]:
    srcs=set(a for a,_ in L);snks=set(s for _,s in L)
    fs=[feas(a) for a in srcs];fk=[feas(s) for s in snks]
    print(len(L),k[0][-45:],'->',k[1][-45:],'| src n',len(srcs),'movable',sum(f for f,_ in fs),'minR',round(max(r or 0 for _,r in fs)),'| snk n',len(snks),'movable',sum(f for f,_ in fk),'minR',round(max(r or 0 for _,r in fk)))
