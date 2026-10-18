import re,sys,collections
V,P=sys.argv[1],sys.argv[2]
pos={}
for l in open(P):
    m=re.search(r'findInst (\S+)\] ([\d.]+) ([\d.]+)',l)
    if m: pos[m.group(1)]=(float(m.group(2)),float(m.group(3)))
txt=open(V).read()
R=collections.defaultdict(list)
for m in re.finditer(r'^\s*(\w+)\s+(\w+)\s*\((.*?)\);',txt,re.S|re.M):
    mod,inst,body=m.groups()
    for c in re.finditer(r'\.(\w+)\((n_clk_\w+)\)',body):
        R[c.group(2)].append((inst,mod,c.group(1)))
for r,L in sorted(R.items(),key=lambda x:-len(x[1])):
    xs=[pos[i][0] for i,_,_ in L if i in pos]; ys=[pos[i][1] for i,_,_ in L if i in pos]
    mods=collections.Counter(re.sub(r'_\d+.*','',m) for _,m,_ in L)
    if xs: print(r,len(L),'bbox_mm %.1fx%.1f'%((max(xs)-min(xs))/1e3,(max(ys)-min(ys))/1e3),dict(mods.most_common(4)))
