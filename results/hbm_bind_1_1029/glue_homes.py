"""HBM-BIND-1: whole-cell homes for residual (unmapped) glue/leaf cells under given as-built roots.
Usage: glue_homes.py WT PLAN MANIFEST ELAB OUT_JSON ROOT_REGEX
Method (generalizes Codex su_control_ownership_r2 to K partitions; no FF fracture, no duplication, no semantic edit):
bit-weighted label propagation over non-clock/reset nets; anchors = already-mapped cells' partitions; candidate
partitions per root = partitions of that root's already-mapped cells. Ties / unanchored cells -> the root's partition
with the largest anchor weight (reported). Output: map parts {path: partition}."""
import sys,json,re,collections
from pathlib import Path
import numpy as np
w,plan,man,elab,out,rootrx=sys.argv[1:7]
sys.path.insert(0,str(Path(w)/'tools'));sys.path.insert(0,str(Path(w)/'tools/die_plan'));import bind as B
a=json.loads(Path(man).read_text());p=json.loads(Path(plan).read_text());p['asbuilt']=a
b=B.Binder(p,json.loads(Path(elab).read_text()),Path(plan).parent,a['base']);b.map_cells();F=b.F
ctl=lambda pn: bool(re.fullmatch(r'(clk.*|clock.*|ck(_.*)?|rst.*|reset.*|arst.*|srst.*)',pn.lower()))
drv=collections.defaultdict(list);lds=collections.defaultdict(list)
for i,c in enumerate(F.cells):
    for pn,bs in c.ports.items():
        if ctl(pn): continue
        t=drv if b.G.dirs[i].get(pn)=='output' else lds
        for n in bs:
            if isinstance(n,int): t[n].append(i)
roots=collections.defaultdict(list)
for i,c in enumerate(F.cells):
    if i not in b.cpart and re.match(rootrx,c.path): roots[c.path.split('.')[0]].append(i)
parts_out={};rep=[]
for r,ids in sorted(roots.items()):
    parts=sorted({z for i,z in b.cpart.items() if F.cells[i].path.startswith(r+'.')})
    K=len(parts);ix={i:j for j,i in enumerate(ids)};N=len(ids)
    anc=np.zeros((N,K));E=collections.Counter()
    nets={n for i in ids for pn,bs in F.cells[i].ports.items() if not ctl(pn) for n in bs if isinstance(n,int)}
    ext=collections.Counter()
    for n in nets:
        for s in drv[n]:
            for d in lds[n]:
                if s==d: continue
                x=ix.get(s);y=ix.get(d)
                if x is not None and y is not None: E[(x,y)]+=1;E[(y,x)]+=1
                elif x is not None or y is not None:
                    u,o=(x,d) if x is not None else (y,s)
                    z=b.cpart.get(o)
                    if z in parts: anc[u,parts.index(z)]+=1
                    elif z is not None: ext[z]+=1
    er=np.array([e[0] for e in E],dtype=np.int64);ec=np.array([e[1] for e in E],dtype=np.int64);ew=np.array(list(E.values()),dtype=float)
    deg=anc.sum(1)+np.bincount(er,weights=ew,minlength=N);safe=np.where(deg>0,deg,1)[:,None]
    prior=anc.sum(0);prior=prior/prior.sum() if prior.sum() else np.ones(K)/K
    S=np.tile(prior,(N,1))
    for it in range(400):
        nb=np.zeros((N,K))
        for k in range(K): nb[:,k]=np.bincount(er,weights=ew*S[ec,k],minlength=N)
        U=(anc+nb)/safe;U=np.where(deg[:,None]>0,U,prior);U=.5*S+.5*U
        d=float(np.abs(U-S).max());S=U
        if d<1e-9: break
    ties=0;unanch=int((deg==0).sum());cnt=collections.Counter()
    for i,j in ix.items():
        srt=np.sort(S[j])
        if K>1 and srt[-1]-srt[-2]<1e-6: ties+=1
        z=parts[int(np.argmax(S[j]))];parts_out[F.cells[i].path]=z;cnt[z]+=1
    rep.append(dict(root=r,cells=N,parts=parts,per_part=dict(cnt),ties=ties,unanchored=unanch,iterations=it+1,last_delta=d,external_anchor_bits=dict(ext)))
    print(r,N,dict(cnt),'ties',ties,'unanch',unanch,'it',it+1)
Path(out).write_text(json.dumps(dict(schema='hbm_bind_1.glue_homes.v1',method=__doc__,root_regex=rootrx,report=rep,parts=parts_out),indent=0))
