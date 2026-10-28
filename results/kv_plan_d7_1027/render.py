import sys,re
import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as pa
p,lef,ox,oy,orient,dx0,dy0,title,out=sys.argv[1:10]; ox,oy,dx0,dy0=map(float,(ox,oy,dx0,dy0)); G=10.8
u4,c4,u6,c6=[np.load(p+f"_{l}_{k}.npy") for l in ("M4","M6") for k in ("use","cap")]
o6=np.clip(u6-c6,0,None); sp4=np.clip(c4-u4,0,None)
L=open(lef).read(); W,H=map(float,re.search(r"SIZE (\S+) BY (\S+)",L).groups())
ob=L[L.index("  OBS"):]; rects=[]; cur=None
for line in ob.splitlines():
    m=re.match(r"\s+LAYER (\S+)",line)
    if m: cur=m.group(1); continue
    m=re.match(r"\s+RECT (\S+) (\S+) (\S+) (\S+)",line)
    if m and cur=="M5":
        a,b,c,d=map(float,m.groups())
        if orient=="MX": b,d=H-d,H-b
        rects.append((a,b,c,d))
st={}
for n,b in re.findall(r"PIN (ot_s_ft\d+_\d+)_[dq]\[\d+\]\n(.*?)END",L,re.S):
    r=re.search(r"RECT ([^;]+);",b); x0,y0,x1,y1=map(float,r.group(1).split())
    if orient=="MX": y0,y1=H-y1,H-y0
    st.setdefault(n,[]).append(((x0+x1)/2,(y0+y1)/2))
fig,ax=plt.subplots(1,2,figsize=(18,11))
ext=[dx0-ox,dx0-ox+G*o6.shape[1],dy0-oy,dy0-oy+G*o6.shape[0]]
for k,(A,t,cm) in enumerate(((o6,"M6 overflow per gcell (use-cap)","Reds"),(u4/np.maximum(c4,1),"M4 usage / capacity (same run)","Blues"))):
    im=ax[k].imshow(np.ma.masked_equal(A,0),origin="lower",extent=ext,cmap=cm,vmin=0,vmax=(60 if k==0 else 1.0),interpolation="nearest")
    plt.colorbar(im,ax=ax[k],fraction=0.03)
    ax[k].add_patch(pa.Rectangle((0,0),W,H,fill=False,ec="k",lw=1.5))
    for a,b,c,d in rects: ax[k].add_patch(pa.Rectangle((a,b),c-a,d-b,fill=True,fc="0.85",ec="0.4",lw=0.6,zorder=0))
    for n,v in st.items():
        xs=[q[0] for q in v]; ys=[q[1] for q in v]
        ax[k].plot(np.mean(xs),np.mean(ys),"g^",ms=4)
        if len(v)>200 and k==0: ax[k].annotate(n[5:],(np.mean(xs),np.mean(ys)),fontsize=6,color="g")
    ax[k].set_title(t); ax[k].set_xlim(-10,W+10); ax[k].set_ylim(-10,H+10); ax[k].set_aspect("equal"); ax[k].set_xlabel("tile x um"); ax[k].set_ylabel("tile y um")
fig.suptitle(title+"  | grey = core OBS M4/M5, green ^ = FT station clusters (big ones labelled)")
plt.tight_layout(); plt.savefig(out,dpi=90)
