import json,re,sys
from collections import Counter,defaultdict
p=json.load(open(sys.argv[1]));pos=p['positions'];T=p['targets']
def fam(n):
    n=n.replace('\\','')
    n=re.sub(r'\[\d+\]','[]',n); n=re.sub(r'\$_.*','',n); n=re.sub(r'/q$','',n)
    return n[:90]
def d(a,b):return abs(pos[a][0]-pos[b][0])+abs(pos[a][1]-pos[b][1])
pairs=Counter();sinks=set();srcs=set();mx=defaultdict(float)
for s,t in T.items():
    for a in t['src']:
        x=d(s,a)
        if x>405:
            k=(fam(a),fam(s));pairs[k]+=1;sinks.add(s);srcs.add(a);mx[k]=max(mx[k],x)
print('unique sinks>405',len(sinks),'unique srcs',len(srcs),'families',len(pairs))
for k,c in pairs.most_common(int(sys.argv[2]) if len(sys.argv)>2 else 30):print(c,round(mx[k]),k[0],'->',k[1])
xs=[v[0] for v in pos.values()];ys=[v[1] for v in pos.values()];print('bbox',min(xs),max(xs),min(ys),max(ys))
