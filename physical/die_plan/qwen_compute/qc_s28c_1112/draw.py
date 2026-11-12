import sys, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
out=sys.argv[1]
W,H=1235.52,2531.52
cores={"u_t20 NK MY":(86.4,77.76),"u_t30 NL R0":(691.2,77.76),"u_t21 NK MY":(86.4,1304.64),"u_t31 NK R0":(691.2,1304.64)}
cw,ch=457.92,1157.76
fig,axs=plt.subplots(1,2,figsize=(14,14))
for k,ax in enumerate(axs):
    ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1.5))
    for n,(x,y) in cores.items():
        ax.add_patch(Rectangle((x,y),cw,ch,color="#d9b38c",alpha=.5))
        ax.text(x+cw/2,y+ch/2,n,ha="center",fontsize=9)
        sx = x+cw if "MY" in n else x   # signal face (R0 W face) after orient
        ax.plot([sx,sx],[y+699.6,y+1102.6],color="red",lw=4)
        tx = x if "MY" in n else x+cw
        ax.plot([tx,tx],[y+561,y+660],color="blue",lw=4)
    for nm,(a,b),c in [("a22_o",(4.32,93.17),"orange"),("bc_o21",(94.13,183.38),"orange"),("y_o21",(184.34,272.77),"orange"),("bc_o31",(617.76,706.94),"orange")]:
        ax.plot([a,b],[H,H],color=c,lw=6); ax.text((a+b)/2,H+12,nm,ha="center",fontsize=7)
    for nm,(a,b) in [("bc_i20",(47.52,140.75)),("bc_i30",(617.76,706.94))]:
        ax.plot([a,b],[0,0],color="cyan",lw=6); ax.text((a+b)/2,-30,nm,ha="center",fontsize=7)
    ax.plot([0,0],[2438,2527],color="cyan",lw=6); ax.text(5,2400,"a22_i in",fontsize=7)
    ax.add_patch(Rectangle((17.28,2425.15),51.84,89.09,color="purple",alpha=.6)); ax.text(20,2380,"a22_i landing ring\n2880 flops",fontsize=7,color="purple")
    pin=(544.224,2356.871); win=(228.552,2531.52)
    reg=(34.56,2522.88) if k==0 else (557.28,2496.96)
    ax.plot([pin[0],reg[0],reg[0]],[pin[1],pin[1],reg[1]] if k==0 else [pin[1],pin[1],reg[1]],color="green",lw=3)
    ax.plot([reg[0],win[0],win[0]],[reg[1],reg[1],win[1]],color="green",lw=3)
    ax.plot(*reg,"s",color="black",ms=10)
    ax.set_title(("BEFORE s28: y_o21 station reg (34.56,2522.88) in NW landing corner\n(stale pre-s22 W-face site); route 544 -> 34 -> 228 um"
                  if k==0 else "AFTER s28c: reg (557.28,2496.96) centre-street/top-band junction\nhops 153 / 363 um <= 405, +0 cycles"),fontsize=10)
    ax.set_xlim(-60,W+60); ax.set_ylim(1700,H+60); ax.set_aspect("equal")
    ax.text(10,1720,"red = core signal face (n_a/n_b/n_y/t_out 4x514b), blue = tap 508b (bc column station)",fontsize=7)
fig.suptitle("cbx_q10 (both clusters) top half, plan_qc99_s28 vs s28c (QC-S28-C)")
fig.savefig(out,dpi=110,bbox_inches="tight")
