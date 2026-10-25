import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as mp, sys
exec(open("an.py").read())
D=load("dump_cts_ff.tsv"); T=load("dump_cts_tt.tsv")
ins={U(r[0]):r for r in D["INST"]}
macros=[k for k,r in ins.items() if r[2]=="macro"]
ckt={U(r[0]):float(r[1]) for r in T["CK"] if r[1]}
pin=set(U(r[1]) for r in D["PINREG"])
inst=lambda p:p.rsplit("/",1)[0]
def pos(i):
    r=ins.get(i); return ((float(r[3])+float(r[5]))/2,(float(r[4])+float(r[6]))/2) if r else None
die=[float(x) for x in D["DIE"][0]]
R=mif("mif_cts.tsv")
cn=[(U(r[1]),[U(s) for s in r[3].split()] if len(r)>3 else []) for r in D["CNET"]]
drv=set(d for d,_ in cn)
def base(ax,t):
    ax.add_patch(mp.Rectangle((die[0],die[1]),die[2]-die[0],die[3]-die[1],fill=False,lw=1))
    for m in macros:
        x0,y0,x1,y1=map(float,ins[m][3:7]); ax.add_patch(mp.Rectangle((x0,y0),x1-x0,y1-y0,color="0.88")); ax.text((x0+x1)/2,(y0+y1)/2,m,ha="center",fontsize=8)
    ax.set_xlim(-5,die[2]+5); ax.set_ylim(-5,die[3]+5); ax.set_aspect("equal"); ax.set_title(t,fontsize=9)
fig,axs=plt.subplots(1,3,figsize=(25,9))
ax=axs[0]; base(ax,"rp1 rw100+leaf 4_1_cts: macro interface regs -> pin (wd blue<=20um / red >20um, w_addr/ce orange, r_addr cyan, rd_out capture green); ck pin *")
for r in R:
    if r["rx"] is None: continue
    d=abs(r["px"]-r["rx"])+abs(r["py"]-r["ry"]); p=r["pin"].split("[")[0]
    col={"wd_in":"b" if d<=20 else "r","w_addr_in":"orange","w_ce_in":"orange","r_addr_in":"c","r_ce_in":"c","rd_out":"g"}.get(p)
    if col: ax.plot([r["rx"],r["px"]],[r["ry"],r["py"]],c=col,lw=0.5 if col in "bg" else 0.9)
ax.plot(19.9,0,"k*",ms=14)
ax=axs[1]; base(ax,"clock tree (placement RC): buffer->buffer edges red, macro clk pin feed blue; sinks colored by TT arrival ps")
ks=[k for k in ckt if pos(inst(k)) and inst(k) not in macros]
sc=ax.scatter([pos(inst(k))[0] for k in ks],[pos(inst(k))[1] for k in ks],c=[ckt[k] for k in ks],s=3,cmap="viridis")
plt.colorbar(sc,ax=ax,fraction=0.04)
for d,s in cn:
    if d not in ins: continue
    a=pos(d)
    for x in s:
        i=inst(x)
        if i in macros:
            b=(float(ins[i][3]),float(ins[i][4])+0.8); ax.plot([a[0],b[0]],[a[1],b[1]],c="b",lw=1.5); ax.text(b[0]+2,b[1]+3,"clk TT %.0f"%ckt.get(i+"/clk",0),color="b",fontsize=8)
        elif i in drv: b=pos(i); ax.plot([a[0],b[0]],[a[1],b[1]],c="r",lw=0.4)
ax.plot(19.9,0,"k*",ms=14)
ax=axs[2]; base(ax,"FF hold violators at CTS (launch->capture): macro wd_in magenta, pin-reg->out port grey")
for ep,sp,sl in D["HOLD"]:
    ei,si=inst(U(ep)),inst(U(sp)); a=pos(si)
    if not a: continue
    if ei in macros:
        nm=U(ep).split("/")[-1]; pr=[r for r in R if r["m"]==ei and r["pin"]==nm]
        b=(pr[0]["px"],pr[0]["py"]) if pr else pos(ei); ax.annotate("",xy=b,xytext=a,arrowprops=dict(arrowstyle="->",color="m",lw=0.5))
    else: ax.plot(*a,".",c="0.5",ms=2)
plt.tight_layout(); plt.savefig(sys.argv[1],dpi=100); print("ok")
