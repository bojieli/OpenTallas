import json,re,sys,statistics as st
spec=sys.argv[1]; pj=json.load(open(sys.argv[2]))
txt=open(spec).read()
nodes={}
tree=re.search(r"set ot_ms_tree \{\n(.*?)\n\}",txt,re.S).group(1)
for ln in tree.splitlines():
    f=ln.strip()[1:-1].split(); nodes[f[0]]=(f[1],float(f[2]),float(f[3]))
lv=re.search(r"set ot_ms_leaves \{\n(.*?)\n\}\nset ot_ms_macros",txt,re.S).group(1)
for ln in lv.splitlines():
    m=re.match(r"\s*\{(\S+) (\S+) \{(\S+) (\S+)\}",ln); nodes[m.group(1)]=(m.group(2),float(m.group(3)),float(m.group(4)))
root=tuple(map(float,re.search(r"set ot_ms_root \{(\S+) (\S+)\}",txt).groups())); nodes['root']=(None,)+root
kids={}
for n,(p,x,y) in nodes.items():
    if p: kids.setdefault(p,[]).append(n)
def xy(n): return nodes[n][1:]
viol_box=[];viol_mono=[]
for n,ks in kids.items():
    if n=='root': continue
    X=[xy(k)[0] for k in ks];Y=[xy(k)[1] for k in ks];x,y=xy(n)
    if not(min(X)-1e-3<=x<=max(X)+1e-3 and min(Y)-1e-3<=y<=max(Y)+1e-3): viol_box.append(n)
    px,py=xy(nodes[n][0])
    w=max(max(0,min(abs(px-x)+abs(x-cx),1e9)-abs(px-cx))+max(0,abs(py-y)+abs(y-cy)-abs(py-cy)) for cx,cy in (xy(k) for k in ks))
    if w>0.5: viol_mono.append((n,round(w,1)))
# per leaf excess path vs manhattan
leaves=[n for n in nodes if n not in kids and n!='root']
def path(n):
    L=0;c=n
    while nodes[c][0]: p=nodes[c][0]; L+=abs(xy(p)[0]-xy(c)[0])+abs(xy(p)[1]-xy(c)[1]); c=p
    return L
ex={n:path(n)-(abs(xy(n)[0]-root[0])+abs(xy(n)[1]-root[1])) for n in leaves}
print("nodes",len(nodes),"leaves",len(leaves),"box_viol",len(viol_box),viol_box[:8])
print("mono_viol",len(viol_mono),sorted(viol_mono,key=lambda t:-t[1])[:10])
print("excess path um: mean %.1f max %.1f"%(st.mean(ex.values()),max(ex.values())))
print("pathlen min %.1f max %.1f"%(min(path(n) for n in leaves),max(path(n) for n in leaves)))
if len(sys.argv)>3:
    import collections
    for C,f,b in (("TT","meas_ck_TT.tsv",2),("FF","meas_ck_FF.tsv",None)):
        agg=collections.defaultdict(list)
        for ln in open(f):
            if ln[0]=='#':continue
            t=ln.split('\t'); lf=t[1][6:-4]
            v=float(t[2]) if C=="TT" else min(float(t[4]),float(t[5]))
            agg[lf].append(v)
        pr=pj[C+"_leaf"]; res={k:st.mean(v)-pr[k] for k,v in agg.items() if k in pr and k in ex}
        r=list(res.values())
        import math
        xs=[ex[k] for k in res]; 
        mx=st.mean(xs); my=st.mean(r)
        cov=sum((a-mx)*(b-my) for a,b in zip(xs,r)); vx=sum((a-mx)**2 for a in xs); vy=sum((b-my)**2 for b in r)
        print(C,"resid mean %.2f sd %.2f min %.2f max %.2f | corr(excess) %.2f slope %.3f ps/um"%(my,st.pstdev(r),min(r),max(r),cov/math.sqrt(vx*vy),cov/vx))
        top=sorted(res.items(),key=lambda kv:-kv[1])[:6]; print(" top",[(k,round(v,1),round(ex[k],1)) for k,v in top])
        g=collections.defaultdict(list)
        for k,v in res.items(): g[k[:4]].append(v)
        print(" by L2",{k:round(st.mean(v),1) for k,v in sorted(g.items())})
