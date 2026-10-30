import json,sys,re
import matplotlib;matplotlib.use("Agg");import matplotlib.pyplot as plt;from matplotlib.patches import Rectangle
P=json.load(open(sys.argv[1]));pt=P["partition_types"];rows={r["type"]:r for r in json.load(open("parent_geom.json"))}
def box(c,shift=0,w=None):
    ox,oy=c["origin_um"];dx,dy=c.get("track_offset_um",[0,0]);cw,ch=c["outline_um"]
    if w:cw=w
    return (ox+dx+shift,oy+dy,cw,ch)
def parent(tn,ax):
    t=pt[tn];W,H=t["outline_um"];ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1.5))
    for c in t.get("hard_cores",[])+[c for c in t.get("contents",[]) if "origin_um" in c]:
        x,y,w,h=box(c);ve=c["module"]=="ot_s81sl_ve_s"
        if ve:
            o=c.get("orient","R0");sh=-8.64 if o in("MY","R180") else 0
            ax.add_patch(Rectangle((x,y),w,h,fill=False,ec="gray",ls="--",lw=1))
            nx,ny,nw,nh=box(c,sh,172.8);ax.add_patch(Rectangle((nx,ny),nw,nh,fc="red",alpha=.35,ec="red",lw=1.5))
            ax.text(nx+3,ny+nh/2,"VES W172.8 "+o,color="darkred",fontsize=7)
            # E strip (grown side)
            sx=nx+164.16 if sh==0 else nx
            ax.add_patch(Rectangle((sx,ny),8.64,nh,fc="orange",alpha=.8))
        else:
            ax.add_patch(Rectangle((x,y),w,h,fc="lightblue" if "sram" not in c["module"] else "khaki",ec="b",lw=.5,alpha=.7))
            if w*h>8000: ax.text(x+2,y+2,c["inst"].split(".")[-1],fontsize=5)
    for tp in t.get("clock",{}).get("taps",[]):
        if "u_ve.u_s" in tp["name"]: ax.plot(*tp["xy"],"k*",ms=9)
    ax.set_xlim(-10,W+10);ax.set_ylim(-10,H+10);ax.set_aspect("equal");ax.set_title(tn+" (min gap %.2f um)"%rows[tn]["min_gap_um"],fontsize=8)
types=sys.argv[2:]
fig,axs=plt.subplots(1,len(types),figsize=(9*len(types),8))
for tn,ax in zip(types,axs): parent(tn,ax)
plt.tight_layout();plt.savefig("ves_parents.png",dpi=110)
# zoom
fig,axs=plt.subplots(1,len(types),figsize=(7*len(types),7))
for tn,ax in zip(types,axs):
    parent(tn,ax);c=[c for c in pt[tn]["hard_cores"] if c["module"]=="ot_s81sl_ve_s"][0];x,y,w,h=box(c);ax.set_xlim(x-120,x+w+220);ax.set_ylim(y-60,y+h+60)
plt.tight_layout();plt.savefig("ves_parents_zoom.png",dpi=110)
# internal
newp=json.load(open("ot_s81sl_ve_s_tpl_w1728.json"))["pins"];oldp={p["name"]:p for p in json.load(open("old_pins.json"))["pins"]}
fig,ax=plt.subplots(1,1,figsize=(7,12))
ax.add_patch(Rectangle((0,0),164.16,345.6,fill=False,ec="gray",ls="--"));ax.add_patch(Rectangle((0,0),172.8,345.6,fill=False,ec="r",lw=1.5))
sx=[];sy=[];mx=[];my=[]
for l in open("geo.txt"):
    f=l.split()
    if f[0]=="SINK":
        stem=f[4].replace(chr(92),"").split("[")[0].split("$_")[0]
        (mx if stem in ["mhh","mkk","mdd","mv","mpre_q"] else sx).append(float(f[1])+(8.64 if stem in ["mhh","mkk","mdd","mv","mpre_q"] else 0));(my if stem in ["mhh","mkk","mdd","mv","mpre_q"] else sy).append(float(f[2]))
ax.scatter(sx,sy,s=.05,c="lightgray");ax.scatter(mx,my,s=2,c="orange",label="386 forecast E captures (+8.64)")
sl=json.load(open("old_master_slice.json"))["core_tree"]["nodes"]
ax.scatter([n["xy_um"][0] for n in sl],[n["xy_um"][1] for n in sl],s=1,c="b",label="2611 clock buffers (frozen homes)")
for p in newp:
    col="r" if p["x"]!=oldp[p["name"]]["x"] else "g"
    ax.plot(p["x"],p["y"],"s" if col=="r" else ".",c=col,ms=3 if col=="r" else 4)
c=[p for p in newp if p["name"]=="clk"][0];ax.plot(c["x"],c["y"],"k*",ms=12,label="clk entry 82.092,172.8")
lef=open("ot_s81sl_ve_s_tpl_w1728.lef").read()
for net in ["VDD","VSS"]:
    body=re.search(r"  PIN "+net+r"\n(.*?)  END "+net,lef,re.S)[1]
    for m in re.finditer(r"RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ;",body):
        a=list(map(float,m.groups()))
        if a[0]>150: ax.add_patch(Rectangle((a[0],a[1]),a[2]-a[0],a[3]-a[1],fc="purple" if net=="VDD" else "teal",alpha=.6))
ax.set_xlim(-5,180);ax.set_ylim(-5,352);ax.set_aspect("equal");ax.legend(fontsize=6,loc="lower left");ax.set_title("VES W172.8 internal: gray=old 164.16 outline; red pins moved E +8.64; PG M5 >150um",fontsize=7)
plt.tight_layout();plt.savefig("ves_internal.png",dpi=120)
