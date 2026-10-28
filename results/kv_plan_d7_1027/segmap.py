import sys,re,collections,json
import numpy as np
seg,lef,ox,oy,orient,dx0,dy0,dx1,dy1,out=sys.argv[1:11]
ox,oy,dx0,dy0,dx1,dy1=map(float,(ox,oy,dx0,dy0,dx1,dy1))
G=10.8
nx=int(round((dx1-dx0)/G))+1; ny=int(round((dy1-dy0)/G))+1
L=open(lef).read(); W,H=map(float,re.search(r"SIZE (\S+) BY (\S+)",L).groups())
obs=collections.defaultdict(list)
ob=L[L.index("  OBS"):]
cur=None
for line in ob.splitlines():
    m=re.match(r"\s+LAYER (\S+)",line)
    if m: cur=m.group(1); continue
    m=re.match(r"\s+RECT (\S+) (\S+) (\S+) (\S+)",line)
    if m:
        a,b,c,d=map(float,m.groups())
        if orient=="MX": b,d=H-d,H-b
        obs[cur].append((a+ox,b+oy,c+ox,d+oy))
def cov(lay):
    m=np.zeros((ny,nx))
    for a,b,c,d in obs[lay]:
        for j in range(max(0,int((b-dy0)//G)),min(ny,int((d-dy0)//G)+1)):
            for i in range(max(0,int((a-dx0)//G)),min(nx,int((c-dx0)//G)+1)):
                gx0,gy0=dx0+i*G,dy0+j*G
                ov=max(0,min(c,gx0+G)-max(a,gx0))*max(0,min(d,gy0+G)-max(b,gy0))
                m[j,i]+=ov/G/G
    return np.clip(m,0,1)
pitch={"M4":.048,"M5":.048,"M6":.064,"M7":.064}
hdir={"M4":1,"M5":0,"M6":1,"M7":0}
use={l:np.zeros((ny,nx)) for l in pitch}   # usage on edge leaving gcell (i->i+1 for H, j->j+1 for V)
fam={l:collections.defaultdict(collections.Counter) for l in pitch}
net=None
for line in open(seg):
    s=line.split()
    if len(s)==1 and s[0] not in "()": net=re.sub(r"_\d+\[\d+\]$","",s[0]); continue
    if len(s)==6 and s[2]==s[5] and s[2] in pitch:
        x1,y1,x2,y2=[int(v)/1000 for v in (s[0],s[1],s[3],s[4])]; l=s[2]
        if hdir[l]:
            j=int((y1-dy0)//G); a,b=sorted((int((x1-dx0)//G),int((x2-dx0)//G)))
            use[l][j,a:b]+=1
            for i in range(a,b): fam[l][(j,i)][net]+=1
        else:
            i=int((x1-dx0)//G); a,b=sorted((int((y1-dy0)//G),int((y2-dy0)//G)))
            use[l][a:b,i]+=1
            for j in range(a,b): fam[l][(j,i)][net]+=1
res={}
for l in pitch:
    raw=G/pitch[l]
    below={"M5":"M4","M6":"M5","M7":"M6"}.get(l)
    capf=np.full((ny,nx),raw*0.25)
    o=cov(l); capf=capf*(1-o)
    if below: tb=cov(below)>0; capf=np.where(tb,capf*0.5,capf)
    cap=np.floor(capf)
    ovf=np.clip(use[l]-cap,0,None)
    res[l]=dict(total=int(ovf.sum()),max=int(ovf.max()))
    np.save(out+f"_{l}_use.npy",use[l]); np.save(out+f"_{l}_cap.npy",cap)
    if l=="M6":
        idx=np.argsort(-ovf.ravel())[:12]
        for k in idx:
            j,i=divmod(k,nx); print(" M6 ovf %d use %d cap %d at die (%.1f,%.1f) local (%.1f,%.1f) %s"%(ovf[j,i],use[l][j,i],cap[j,i],dx0+i*G,dy0+j*G,dx0+i*G-ox,dy0+j*G-oy,fam[l][(j,i)].most_common(3)))
        # attribution: ovf by family share
        att=collections.Counter()
        for k in np.flatnonzero(ovf.ravel()):
            j,i=divmod(k,nx); c=fam[l][(j,i)]; t=sum(c.values())
            for n,v in c.items(): att[n]+=ovf[j,i]*v/t
        print(" M6 overflow by FT slot:",[(n.split("__")[1],int(v)) for n,v in att.most_common(12)])
        # overflow over obs vs channel
        tb=cov("M5")>0
        print(" M6 ovf over M5-OBS (core) gcells: %d ; elsewhere %d ; core-gcell cap median %d, channel cap median %d"%(ovf[tb].sum(),ovf[~tb].sum(),np.median(cap[tb]) if tb.any() else -1,np.median(cap[~tb])))
print(json.dumps(res))
