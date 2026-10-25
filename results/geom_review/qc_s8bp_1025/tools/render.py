import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as mp, collections, statistics as S, sys
k=sys.argv[1]; out=sys.argv[2]
def load(c):
    D=collections.defaultdict(list)
    for l in open(f"/tmp/s8bp/{k}/dump_{c}.tsv"):
        t=l.rstrip("\n").split("\t"); D[t[0]].append(t[1:])
    return D
U=lambda s:s.replace("\\","")
tt=load("tt"); ff=load("ff")
ins={U(r[0]):r for r in tt["INST"]}
macros=[U(r[0]) for r in tt["INST"] if r[2]=="macro"]
ckt={U(r[0]):float(r[1]) for r in tt["CK"] if r[1]}
ckf={U(r[0]):float(r[1]) for r in ff["CK"] if r[1]}
pin=set(U(r[1]) for r in tt["PINREG"])
inst=lambda p:p.rsplit("/",1)[0]
die=[float(x) for x in tt["DIE"][0]]
def P(i):
    r=ins.get(i); return ((float(r[3])+float(r[5]))/2,(float(r[4])+float(r[6]))/2) if r else None
ports={U(r[0]):(float(r[1]),float(r[2])) for r in tt["PORT"]}
cn=[(U(r[1]),[U(s) for s in r[3].split()] if len(r)>3 else []) for r in tt["CNET"]]
drv=set(d for d,_ in cn)
def base(ax,t):
    ax.add_patch(mp.Rectangle((die[0],die[1]),die[2]-die[0],die[3]-die[1],fill=False,lw=1))
    for m in macros:
        r=ins[m]; x0,y0,x1,y1=map(float,r[3:7]); ax.add_patch(mp.Rectangle((x0,y0),x1-x0,y1-y0,color="0.88"))
        ax.text((x0+x1)/2,(y0+y1)/2,m,ha="center",fontsize=7)
        ax.plot(x0,y0,"b^",ms=7)
    ax.set_xlim(die[0]-5,die[2]+5); ax.set_ylim(die[1]-5,die[3]+5); ax.set_aspect("equal"); ax.set_title(t,fontsize=8)
fig,axs=plt.subplots(1,3,figsize=(24,10))
ax=axs[0]; base(ax,f"{k} 5_1_grt: ports(black) pin-regs(green) other flops(grey) clock nets(red) delaybuf(magenta); macro clk pin = blue ^")
ax.scatter(*zip(*ports.values()),s=1,c="k")
regs=[inst(p) for p in ckt if inst(p) not in macros]
g=[P(i) for i in regs if i in pin and P(i)]; o=[P(i) for i in regs if i not in pin and P(i)]
ax.scatter(*zip(*o),s=1,c="0.6"); ax.scatter(*zip(*g),s=1,c="g")
for d,ss in cn:
    a=ports.get(d[5:]) if d.startswith("PORT:") else P(d)
    if not a: continue
    for s in ss:
        si=inst(s)
        if si in drv or si in macros:
            b=P(si); ax.plot([a[0],b[0]],[a[1],b[1]],c="r",lw=0.5)
cb=[P(d) for d in drv if d in ins]; ax.scatter(*zip(*cb),s=5,c="r",marker="s")
db=[P(d) for d in drv if "delaybuf" in d]; 
if db: ax.scatter(*zip(*db),s=14,c="m",marker="s")
if "ck" in ports: ax.plot(*ports["ck"],"k*",ms=14); ax.text(ports["ck"][0]+3,ports["ck"][1],"ck port",fontsize=8)
for idx,(nm,ck) in enumerate((("TT",ckt),("FF",ckf))):
    ax=axs[idx+1]
    fl=[v for p,v in ck.items() if inst(p) not in macros]
    base(ax,f"{nm} GRT clock arrival at sinks (ps, src lat 0); flops {min(fl):.0f}..{max(fl):.0f} mean {S.mean(fl):.0f}; macro clk values in blue")
    ks=[p for p in ck if P(inst(p)) and inst(p) not in macros]
    sc=ax.scatter([P(inst(p))[0] for p in ks],[P(inst(p))[1] for p in ks],c=[ck[p] for p in ks],s=3,cmap="viridis")
    plt.colorbar(sc,ax=ax,fraction=0.04)
    for p,v in ck.items():
        if inst(p) in macros:
            r=ins[inst(p)]; ax.text(float(r[3])+2,float(r[4])+3,f"clk {v:.0f}",fontsize=9,color="b")
plt.tight_layout(); plt.savefig(out,dpi=100); print("ok",out)
