import sys,collections,re
cells={};nets=[];pins={}
for ln in open(sys.argv[1]):
    f=ln.rstrip('\n').split('\t')
    if f[0]=='C': cells[f[1]]=(f[2],f[3],(float(f[4])+float(f[6]))/2,(float(f[5])+float(f[7]))/2,f[8])
    elif f[0]=='N': nets.append(f[1:])
    elif f[0]=='P': pins[f[1]]=(f[2],f[3],float(f[6]),float(f[7]))
node=[k for k,c in cells.items() if c[1]=='ot_qwen_tile_node'][0]
# 2-hop: node <-> cell <-> (pin / cell); classify the partner by x band and name family
b=collections.Counter(); fam=collections.Counter(); hop2=collections.Counter()
drv_of={}; nets_of=collections.defaultdict(list)
for i,n in enumerate(nets):
    for t in n[1:]:
        if t.startswith('i'): nets_of[t.rstrip('c')[1:]].append(i)
for i,n in enumerate(nets):
    ts=[t for t in n[1:] if t!='-']
    if len(ts)>16: continue
    if not any(t.startswith('i') and t.rstrip('c')[1:]==node for t in ts): continue
    for t in ts:
        if t.startswith('p'): b['toppin']+=1; continue
        c=t.rstrip('c')[1:]
        if c==node or c not in cells: continue
        x=cells[c][2]
        b['x<130' if x<130 else 'x130-260' if x<260 else 'x260-388' if x<388 else 'x>=388']+=1
        fam[re.sub(r'\\\[\d+\\\]|\[\d+\]|\d+','#',cells[c][4])[:70]]+=1
print('node partners by x band', dict(b))
for k,v in fam.most_common(14): print(v,k)
