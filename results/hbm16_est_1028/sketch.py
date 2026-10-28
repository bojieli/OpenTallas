import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as P, sys
out=sys.argv[1]
fig,axs=plt.subplots(1,2,figsize=(13,8))
def tile(ax,x,y,w,h,flip,sm_w,sm_h,label):
    # rows from PHY side: SM, SU, band, SU, SM ; flip = PHY below
    rows=[("SM",sm_h,"#7aa6d6"),("SU",1.565,"#a7d68f"),("band(hub/HC/IDX)",4.32,"#e8b26a"),("SU",1.555,"#a7d68f"),("SM",sm_h,"#7aa6d6")]
    yy=y+h if not flip else y
    for n,rh,c in rows:
        if n=="SM":
            for k in range(2):
                xx=x+(0 if k==0 else w-sm_w)
                ry=yy-rh if not flip else yy
                ax.add_patch(P.Rectangle((xx,ry),sm_w,rh,fc=c,ec="k",lw=.5)); ax.text(xx+sm_w/2,ry+rh/2,"SM",ha="center",va="center",fontsize=7)
            ry=yy-rh if not flip else yy
            ax.add_patch(P.Rectangle((x+sm_w,ry),w-2*sm_w,rh,fc="#dddddd",ec="k",lw=.5))
        else:
            ry=yy-rh if not flip else yy
            ax.add_patch(P.Rectangle((x,ry),w,rh,fc=c,ec="k",lw=.5)); ax.text(x+w/2,ry+rh/2,n,ha="center",va="center",fontsize=7)
        yy = yy-rh if not flip else yy+rh
    ax.text(x+0.3,y+0.3 if not flip else y+h-0.8,label,fontsize=8,weight="bold")
for ax,(title,smw) in zip(axs,[("A16-today: 4 x today's quad tile (SM 5.77 x 4.51)",5.7715),("A16-squeezed: SM col channels removed (SM 5.05 wide)",5.046)]):
    TW=2*smw+1.814; TH=16.47; PH=2.074; ws=1.685; hs=1.0
    W=2*TW+ws; H=2*(TH+PH)+hs
    # PHY rows
    for (yy) in (0, H-PH):
        ax.add_patch(P.Rectangle((0,yy),W,PH,fc="#f2f2f2",ec="k",lw=.5))
        ax.add_patch(P.Rectangle((W/2-4.4,yy),8.8,PH,fc="#c79be0",ec="k",lw=.5)); ax.text(W/2,yy+PH/2,"HBM3E PHY (1 stack / tile pair)",ha="center",va="center",fontsize=7)
    # note: one PHY per tile? A uses one stack per tile pair; draw one per tile pair centred
    tile(ax,0,PH,TW,TH,True,smw,4.51,"SW"); tile(ax,TW+ws,PH,TW,TH,True,smw,4.51,"SE")
    tile(ax,0,PH+TH+hs,TW,TH,False,smw,4.51,"NW"); tile(ax,TW+ws,PH+TH+hs,TW,TH,False,smw,4.51,"NE")
    ax.add_patch(P.Rectangle((TW,PH),ws,2*TH+hs,fc="#ff9999",ec="k",lw=.5)); ax.add_patch(P.Rectangle((0,PH+TH),W,hs,fc="#ff9999",ec="k",lw=.5))
    ax.text(W/2,PH+TH+hs/2,"root/seam",ha="center",va="center",fontsize=7)
    ax.add_patch(P.Rectangle((0,0),26,33,fill=False,ec="red",lw=2,ls="--")); ax.text(0.2,33.3,"reticle 26 x 33 mm",color="red",fontsize=9)
    ax.set_xlim(-1,max(W,26)+1); ax.set_ylim(-1,max(H,33)+2); ax.set_aspect("equal")
    ax.set_title(f"{title}\n die {W:.1f} x {H:.1f} mm = {W*H:.0f} mm2",fontsize=9)
plt.tight_layout(); plt.savefig(out,dpi=110)
