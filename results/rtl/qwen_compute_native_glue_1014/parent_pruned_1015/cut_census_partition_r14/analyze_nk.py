import gzip,collections,sys,json
inst={}
for l in gzip.open('instances.tsv.gz','rt'):
    n,m,w,h=l.rstrip('\n').split('\t'); inst[n]=m
std=lambda m: m.endswith('_ASAP7_75t_R')
hard={n for n,m in inst.items() if not std(m)}
nets=collections.defaultdict(list)
for l in gzip.open('connections.tsv.gz','rt'):
    net,typ,i,m,pin,io=l.rstrip('\n').split('\t')
    if typ!='SIGNAL': continue
    nets[net].append((i,m,pin,io))
# drop clock nets (any FF CLK pin or hard clk pin) and high-fanout nets (reset/broadcast) from the clustering graph
clk=set();hf=set()
for net,ts in nets.items():
    if any(p in('CLK',) or p.startswith('ck') or p=='clk' for _,_,p,_ in ts): clk.add(net)
    if len(ts)>64: hf.add(net)
parent=dict()
def find(x):
    while parent.get(x,x)!=x:
        parent[x]=parent.get(parent[x],parent[x]); x=parent[x]
    return x
def union(a,b):
    ra,rb=find(a),find(b)
    if ra!=rb: parent[ra]=rb
for net,ts in nets.items():
    if net in clk or net in hf: continue
    s=[i for i,m,_,_ in ts if i in inst and std(inst[i]) and not inst[i].startswith('TAPCELL')]
    for a in s[1:]: union(s[0],a)
comp=collections.defaultdict(set)
for i,m in inst.items():
    if std(m) and not m.startswith('TAPCELL') and not m.startswith('FILL'): comp[find(i)].add(i)
touch=collections.defaultdict(collections.Counter)
for net,ts in nets.items():
    if net in clk: continue
    s=[i for i,m,_,_ in ts if i in inst and std(inst[i]) and not inst[i].startswith('TAPCELL')]
    h=[i for i,m,_,_ in ts if i in hard]
    if s and h:
        for c in {find(x) for x in s}:
            for x in h: touch[c][x]+=1
rows=[]
for c,cells in comp.items():
    ff=sum(1 for x in cells if 'DFF' in inst[x])
    rows.append((len(cells),ff,len(touch[c]),sum(touch[c].values()),c,touch[c].most_common(40)))
rows.sort(reverse=True)
print('hard',len(hard),'std comps',len(rows),'cells',sum(r[0] for r in rows),'clk nets',len(clk),'hf nets',len(hf))
hist=collections.Counter(min(r[2],20) for r in rows)
print('components by #hard touched (20=20+):',sorted(hist.items()))
for r in rows[:25]:
    print(r[0],'cells',r[1],'FF',r[2],'hard',r[3],'pins',[f'{k}:{v}' for k,v in r[5]])
small=[r for r in rows if r[2]<=3]
print('components touching <=3 hard:',len(small),'cells',sum(r[0] for r in small),'FF',sum(r[1] for r in small))
big=[r for r in rows if r[2]>3]
print('components touching >3 hard:',len(big),'cells',sum(r[0] for r in big),'FF',sum(r[1] for r in big))
json.dump([dict(cells=r[0],ff=r[1],hard=r[2],pins=r[3],top=r[5]) for r in rows],open('components.json','w'))
