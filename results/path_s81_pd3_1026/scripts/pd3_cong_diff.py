"""M6/M7 guide demand (nets per 10.8um gcell, max over 108-um bin) for plan A vs plan B, + diff. usage: cong_diff.py planA guideA planB guideB out"""
import sys,json,numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
pa,ga,pb,gb,out=sys.argv[1:6]; G=10.8; K=10
def dem(plan,guide):
    P=json.load(open(plan)); W,H=P["die"]["outline_um"]; nx,ny=int(np.ceil(W/G))+1,int(np.ceil(H/G))+1
    D={L:np.zeros((ny+1,nx+1),np.int32) for L in("M6","M7")}
    for ln in open(guide):
        p=ln.split()
        if len(p)!=5 or p[4] not in D: continue
        x0,y0,x1,y1=(int(v)/1000.0 for v in p[:4]); i0,j0,i1,j1=int(x0//G),int(y0//G),int(round(x1/G)),int(round(y1/G))
        A=D[p[4]]; A[j0,i0]+=1;A[j0,i1]-=1;A[j1,i0]-=1;A[j1,i1]+=1
    R={}
    for L,A in D.items():
        A=A.cumsum(0).cumsum(1)[:ny,:nx]; ny2,nx2=ny//K*K,nx//K*K
        R[L]=A[:ny2,:nx2].reshape(ny2//K,K,nx2//K,K).max((1,3))
    return P,W,H,R
A=dem(pa,ga); B=dem(pb,gb)
HOT=("gunit","bk_sel","lk_WS3","s_4N_x06")
def parts(ax,P,lw=0.25):
    for p in P["partitions"]:
        t=P["partition_types"][p["type"]]; w,h=t["outline_um"]; x,y=p["origin_um"]
        hot=any(k in p["name"] for k in HOT)
        ax.add_patch(Rectangle((x,y),w,h,fill=False,lw=1.4 if hot else lw,ec="#0050ff" if hot else "#6080a0"))
        if hot: ax.text(x+w/2,y+h/2,p["name"],fontsize=6,color="#0030c0",ha="center",va="center")
fig,axs=plt.subplots(2,3,figsize=(30,16)); S={}
for r,L in enumerate(("M6","M7")):
    a,b=A[3][L],B[3][L]; ny=min(a.shape[0],b.shape[0]); nx=min(a.shape[1],b.shape[1]); a,b=a[:ny,:nx],b[:ny,:nx]
    vm=168.75*0.25*1.0
    for c,(P,W,H,m,tt) in enumerate(((A[0],A[1],A[2],a,"A g0fix"),(B[0],B[1],B[2],b,"B B5"))):
        ax=axs[r,c]; im=ax.imshow(m,origin="lower",extent=(0,nx*G*K,0,ny*G*K),cmap="inferno_r",vmin=0,vmax=2*vm); parts(ax,P)
        ax.set_title(f"{tt} {L}: max nets/gcell per 108um bin (cap~{vm:.0f}/gcell unblocked); bins>cap {(m>vm).sum()}"); fig.colorbar(im,ax=ax,shrink=.7)
    d=a.astype(float)-b; ax=axs[r,2]; im=ax.imshow(d,origin="lower",extent=(0,nx*G*K,0,ny*G*K),cmap="RdBu_r",vmin=-vm,vmax=vm); parts(ax,A[0]); fig.colorbar(im,ax=ax,shrink=.7)
    ax.set_title(f"{L} g0fix - B5 (blue outlines = g0fix moved parts)")
    S[L]={"A_bins_over_cap":int((a>vm).sum()),"B_bins_over_cap":int((b>vm).sum()),"A_max":int(a.max()),"B_max":int(b.max())}
    # localise A hot bins to parts
    own={}
    ys,xs=np.where(a>vm)
    for y,x in zip(ys,xs):
        cx,cy=(x+.5)*G*K,(y+.5)*G*K; hit="(channel)"
        for p in A[0]["partitions"]:
            t=A[0]["partition_types"][p["type"]]; w,h=t["outline_um"]; px,py=p["origin_um"]
            if px<=cx<px+w and py<=cy<py+h: hit=p["name"]; break
        own[hit]=own.get(hit,0)+1
    S[L]["A_hot_bins_by_part"]=sorted(own.items(),key=lambda kv:-kv[1])[:20]
fig.tight_layout(); fig.savefig(out+".png",dpi=90); json.dump(S,open(out+".json","w"),indent=1); print(json.dumps(S))
