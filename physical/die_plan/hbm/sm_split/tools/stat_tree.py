import re,sys,json
txt=open(sys.argv[1]).read()
blocks=re.split(r'\n=== (.+?) ===\n',txt)
mods={}
for i in range(1,len(blocks),2):
    name=blocks[i]; body=blocks[i+1]
    m=re.search(r'^\s+(\S+)\s+(\S+) cells$',body,re.M)
    cells=float(m.group(1)) if m else 0
    area=float(m.group(2)) if m and m.group(2)!='-' else 0
    subs={}; srams={}
    sm=re.search(r'submodules\n((?:\s+\d+\s+-\s+\S.*\n)+)',body)
    if sm:
        for l in sm.group(1).splitlines():
            n,_,mn=l.split(None,2); subs[mn.strip()]=int(n)
    for l in re.findall(r'^\s+(\d+)\s+-\s+(ot_sram\S+)$',body,re.M):
        srams[l[1]]=int(l[0])
    dff=sum(int(x) for x in re.findall(r'^\s+(\d+)\s+\S+\s+DFF\S+$',body,re.M))
    mods[name]=dict(cells=cells,area=area,subs=subs,srams=srams,dff=dff)
memo={}
def tot(n):
    if n in memo: return memo[n]
    m=mods.get(n) or mods.get('\\'+n) 
    if m is None:
        return dict(cells=0,area=0,dff=0,sram=0)
    t=dict(cells=m['cells'],area=m['area'],dff=m['dff'],sram=sum(m['srams'].values()))
    for s,k in m['subs'].items():
        if s.startswith('ot_sram'): continue
        st=tot(s)
        for kk in t: t[kk]+=k*st[kk]
    memo[n]=t; return t
def short(n): return n.split('\\')[-1]
def show(n,depth,maxd,mult=1):
    t=tot(n)
    print('  '*depth+f'{short(n)[:60]:60s} x{mult:<3d} cells {t["cells"]/1e3:9.1f}k dff {t["dff"]/1e3:8.1f}k area {t["area"]:10.0f} sram {t["sram"]}')
    if depth<maxd:
        for s,k in sorted(mods.get(n,{}).get('subs',{}).items(), key=lambda x:-tot(x[0])['cells']*x[1]):
            if s.startswith('ot_sram'): continue
            if tot(s)['cells']*k < float(sys.argv[3]): continue
            show(s,depth+1,maxd,k)
top=[n for n in mods if n.endswith('\\ot_hbm_accel_smh_attn')][0]
show(top,0,int(sys.argv[2]))
json.dump({short(k):dict(own=v, total=tot(k)) for k,v in mods.items()}, open('/home/ubuntu/scratch/hbm-p3-sm-1023/stat_tree.json','w'))
