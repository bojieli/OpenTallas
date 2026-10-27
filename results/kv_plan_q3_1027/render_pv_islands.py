import json,sys,matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
pd,out=sys.argv[1],sys.argv[2]
W,H=380.16,190.08
P=json.load(open(f"{pd}/hm_r26q3.json"))
ci=P["clock"]["mesh"]["core_islands"]["kv3_pv_pair"]["rects_um"]
# RTLMP macros from the PV2 runs (2_floorplan.odb dumps, 10-27 R0 FAIL / fMX PASS)
MAC={"R0 view (PV2 GPL FAIL)":[(8.64,122.076,60.048,142.866),(68.688,122.076,120.096,142.866),(68.688,142.908,120.096,163.698),(8.64,142.908,60.048,163.698),(320.112,4.35,371.52,25.14),(320.112,25.182,371.52,45.972),(320.112,46.062,371.52,66.852),(320.112,66.876,371.52,87.666)],
     "fMX view (PV2 GPL PASS)":[(8.64,144.108,60.048,164.898),(68.688,144.108,120.096,164.898),(128.736,144.108,180.144,164.898),(188.784,144.108,240.192,164.898),(320.112,144.108,371.52,164.898),(260.064,144.108,311.472,164.898),(320.112,164.988,371.52,185.778),(260.064,164.988,311.472,185.778)]}
RES=[(185.76,90.72,194.4,99.36),(90.72,90.72,99.36,99.36),(280.8,90.72,289.44,99.36)]
fig,axs=plt.subplots(2,2,figsize=(16,10))
for ax,(t,ms) in zip(axs[0],MAC.items()):
    ax.add_patch(Rectangle((0,0),W,H,fill=False,ec="k"))
    ax.add_patch(Rectangle((4.32,4.32),W-8.64,H-8.64,fill=False,ec="gray",ls="--"))
    for m in ms: ax.add_patch(Rectangle(m[:2],m[2]-m[0],m[3]-m[1],fc="tab:blue",alpha=.35,ec="tab:blue"))
    for m in ms: ax.add_patch(Rectangle((m[0]-2,m[1]-2),m[2]-m[0]+4,m[3]-m[1]+4,fill=False,ec="tab:blue",ls=":"))
    for r in RES: ax.add_patch(Rectangle(r[:2],8.64,8.64,fc="tab:green",alpha=.3))
    for r in ci:
        hit=any(m[0]-2<r[2] and r[0]<m[2]+2 and m[1]-2<r[3] and r[1]<m[3]+2 for m in ms)
        ax.add_patch(Rectangle((r[0]-1,r[1]-1),r[2]-r[0]+2,r[3]-r[1]+2,fc="red" if hit else "orange",ec="red"))
        ax.annotate(f"{r[0]:g},{r[1]:g}"+(" IN MACRO" if hit else ""),(r[0],r[1]),xytext=(r[0]+5,r[1]+6 if r[1]<100 else r[1]-12),fontsize=8,color="red" if hit else "k")
    ax.set_xlim(-5,W+5);ax.set_ylim(-5,H+5);ax.set_aspect("equal");ax.set_title(f"kv3_pv_pair core frame, {t}\nblue=RTLMP SRAM (+2um tap halo), green=kvr2 reserve, orange/red=island_ft cells")
# zoom on island 1 rows, R0 view
ax=axs[1][0]
r0=[m for m in MAC["R0 view (PV2 GPL FAIL)"]]
for j in range(486,505):
    y=4.32+j*0.27
    for x0,x1 in ((4.32,6.588),(62.1,66.636),(122.148,130)): ax.add_patch(Rectangle((x0,y),x1-x0,0.27,fc="lightgray" if j%2 else "whitesmoke",ec="gray",lw=.3))
for m in r0: ax.add_patch(Rectangle(m[:2],m[2]-m[0],m[3]-m[1],fc="tab:blue",alpha=.35))
for r in ci: ax.add_patch(Rectangle(r[:2],r[2]-r[0],r[3]-r[1],fc="red"))
ax.set_xlim(55,130);ax.set_ylim(135.5,140);ax.set_title("R0 view zoom: rows (gray) cut by SRAM g_mem[1] x68.7-120.1; island_ft row 496 (y138.24) exists only outside the macro")
# images
ax=axs[1][1]
ax.add_patch(Rectangle((0,0),W,H,fill=False,ec="k"))
cols={"R0":"red","MX":"tab:purple","MY":"tab:orange","R180":"tab:brown"}
for o,c in cols.items():
    for r in ci:
        x0,y0,x1,y1=r
        xs=(x0,x1) if o in("R0","MX") else (W-x1,W-x0); ys=(y0,y1) if o in("R0","MY") else (H-y1,H-y0)
        okr=abs(((ys[0]-4.32)/0.27)-round((ys[0]-4.32)/0.27))<1e-4; oks=abs(((xs[0]-4.32)/0.054)-round((xs[0]-4.32)/0.054))<1e-4
        ax.add_patch(Rectangle((xs[0]-1.5,ys[0]-1.5),xs[1]-xs[0]+3,ys[1]-ys[0]+3,fc=c))
        ax.annotate(f"{o} row{(ys[0]-4.32)/0.27:.0f} site{(xs[0]-4.32)/0.054:.0f} {'ON' if okr and oks else 'OFF'}",(xs[0],ys[0]),xytext=(xs[0]+4,ys[0]+3),fontsize=7,color=c)
ax.set_xlim(-5,W+5);ax.set_ylim(-5,H+5);ax.set_aspect("equal");ax.set_title("hm_r26q3 island_ft cells in R0/MX/MY/R180 images: all on row/site grid")
plt.tight_layout();plt.savefig(out,dpi=110)
