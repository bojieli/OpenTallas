import json,sys,os,re,math,collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan,out,label=sys.argv[1],sys.argv[2],sys.argv[3]
cells_est=sys.argv[4] if len(sys.argv)>4 else None
os.makedirs(out,exist_ok=True)
P=json.load(open(plan)); pt=P["partition_types"]; parts=P["partitions"]
W,H=P["die"]["outline_um"]
CE=json.load(open(cells_est)) if cells_est and os.path.exists(cells_est) else {}
A_CELL=0.26   # um2 per std cell (ASAP7 average incl. FF mix) -- stated assumption
def fam(t):
    b=t.split("__")[0]
    return re.sub(r"_p\d+$","",b) if b.startswith("col_h") else b
def swap(o): return o in ("R90","R270","MXR90","MYR90")
def crect(c):
    x,y=c["origin_um"]; w,h=c["outline_um"]
    if swap(c.get("orient","R0")): w,h=h,w
    return x,y,x+w,y+h
def merge(iv):
    iv=sorted(iv); tot=0; cur=None
    for a,b in iv:
        if cur is None: cur=[a,b]
        elif a<=cur[1]: cur[1]=max(cur[1],b)
        else: tot+=cur[1]-cur[0]; cur=[a,b]
    if cur: tot+=cur[1]-cur[0]
    return tot
inst=collections.defaultdict(list)
for p in parts: inst[p["type"]].append(p)
rows=[]
for t,x in pt.items():
    w,h=x["outline_um"]; area=w*h; n=len(inst[t])
    hc=x.get("hard_cores",[]) or []
    rects=[crect(c) for c in hc]
    carea=sum((r[2]-r[0])*(r[3]-r[1]) for r in rects)
    if rects:
        bx0=min(r[0] for r in rects);by0=min(r[1] for r in rects);bx1=max(r[2] for r in rects);by1=max(r[3] for r in rects)
        mg=(bx0,by0,w-bx1,h-by1)
        Xocc=merge([(r[0],r[2]) for r in rects]);Yocc=merge([(r[1],r[3]) for r in rects])
    else:
        bx0=by0=bx1=by1=0;mg=(0,0,0,0);Xocc=Yocc=0
    cells=0
    for p in inst[t]:
        e=CE.get(p["name"])
        if e: cells+=e.get("glue",e.get("cells",0))
    cells=cells/max(n,1)
    Wns=Wew=0.0; bits_ns=bits_ew=0; bands=[]
    for s in x.get("ft_slots",[]) or []:
        iw=s.get("in_window_um") or [0,0]; bw=abs(iw[1]-iw[0])
        face=s.get("in_face","N")
        if face in "NS": Wns+=bw; bits_ns+=s["width"]
        else: Wew+=bw; bits_ew+=s["width"]
        bands.append((face,iw[0],iw[1],s["width"]))
    taps=x.get("clock",{}).get("taps",[]) or []
    st=x.get("internal_stations",[]) or []
    hop_over=0;maxhop=0
    for s in st:
        pts=[s["from_um"]]+[r for r in s.get("regs_um",[])]+[s["to_um"]]
        for a,b in zip(pts,pts[1:]):
            d=abs(a[0]-b[0])+abs(a[1]-b[1]); maxhop=max(maxhop,d)
            if d>405.0: hop_over+=1
    ftst=[s for s in x.get("ft_slots",[]) or []]
    for s in ftst:
        rg=s.get("regs_um") or []
        for a,b in zip(rg,rg[1:]):
            d=abs(a[0]-b[0])+abs(a[1]-b[1]); maxhop=max(maxhop,d)
            if d>405.0: hop_over+=1
    rows.append(dict(type=t,family=fam(t),n_inst=n,w=w,h=h,area=area,aspect=max(w,h)/max(min(w,h),1e-9),
        n_cores=len(hc),core_area=carea,core_fill=carea/area if area else 0,
        bbox_w=bx1-bx0,bbox_h=by1-by0,bbox_frac=((bx1-bx0)*(by1-by0)/area if area else 0),
        marg_w=mg[0],marg_s=mg[1],marg_e=mg[2],marg_n=mg[3],Xocc=Xocc,Yocc=Yocc,
        cells=cells,cell_fill=cells*A_CELL/area if area else 0,
        ft_slots=len(ftst),ft_bits_ns=bits_ns,ft_bits_ew=bits_ew,band_ns=Wns,band_ew=Wew,
        n_taps=len(taps),n_stations=len(st),hops_over_405=hop_over,max_hop=maxhop,bands=bands))
T={r["type"]:r for r in rows}
json.dump(rows,open(out+"/type_table.json","w"))
# family summary
FS={}
for r in rows:
    f=FS.setdefault(r["family"],dict(types=0,inst=0,area=0.0,core_area=0.0,cells=0.0,hops=0,taps=0,fill_min=9,fill_max=0))
    f["types"]+=1;f["inst"]+=r["n_inst"];f["area"]+=r["area"]*r["n_inst"];f["core_area"]+=r["core_area"]*r["n_inst"]
    f["cells"]+=r["cells"]*r["n_inst"];f["hops"]+=r["hops_over_405"]*r["n_inst"];f["taps"]+=r["n_taps"]*r["n_inst"]
    cf=r["core_fill"]+r["cell_fill"]
    f["fill_min"]=min(f["fill_min"],cf);f["fill_max"]=max(f["fill_max"],cf)
for k,f in FS.items():
    f["core_fill"]=f["core_area"]/f["area"]; f["cell_fill"]=f["cells"]*A_CELL/f["area"]
json.dump(FS,open(out+"/family_table.json","w"),indent=1)
tot_area=sum(f["area"] for f in FS.values())
print("die",W,H,"die_area",W*H/1e6,"mm2 partition area",tot_area/1e6,"mm2 util",tot_area/(W*H))
print("%-34s %5s %5s %12s %8s %8s %8s %6s %6s"%("family","types","inst","area_mm2","coreFill","cellFill","tot","hops>405","taps"))
for k,f in sorted(FS.items(),key=lambda kv:-kv[1]["area"]):
    print("%-34s %5d %5d %12.2f %8.3f %8.3f %8.3f %6d %6d"%(k,f["types"],f["inst"],f["area"]/1e6,f["core_fill"],f["cell_fill"],f["core_fill"]+f["cell_fill"],f["hops"],f["taps"]))
# ---- renders
fams=sorted(FS); cm=plt.get_cmap("tab20"); fc={f:cm(i%20) for i,f in enumerate(fams)}
def rect(p):
    w,h=pt[p["type"]]["outline_um"]; x,y=p["origin_um"]; return x,y,w,h
def whole(fn,xlim=None,ylim=None,labels=False,title=""):
    fig,ax=plt.subplots(figsize=(18,14.5),dpi=110)
    ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1.5))
    for p in parts:
        x,y,w,h=rect(p); r=T[p["type"]]
        if xlim and (x+w<xlim[0] or x>xlim[1] or y+h<ylim[0] or y>ylim[1]): continue
        ax.add_patch(Rectangle((x,y),w,h,fc=fc[r["family"]],alpha=0.55,ec="k",lw=0.3))
        if labels:
            tot=r["core_fill"]+r["cell_fill"]
            s="%s\n%dx%d f%.0f%%\nasp%.1f ft%.0f/%.0f\ntap%d hop%d"%(p["name"],w,h,100*tot,r["aspect"],r["band_ns"],r["band_ew"],r["n_taps"],r["hops_over_405"])
            ax.text(x+w/2,y+h/2,s,ha="center",va="center",fontsize=5.5 if w>600 else 4.5)
    for c in P["die"].get("channels",[]):
        r=c.get("rect_um")
        if r: ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fill=False,ec="grey",hatch="//",lw=0.4))
    rt=P["clock"].get("spine",{}).get("root_um")
    if rt: ax.plot(*rt,"r*",ms=14)
    ax.set_xlim(*(xlim or (0,W)));ax.set_ylim(*(ylim or (0,H)));ax.set_aspect("equal")
    ax.set_title(title or "%s %s"%(label,"")); 
    if not xlim:
        hs=[Rectangle((0,0),1,1,fc=fc[f]) for f in fams]; ax.legend(hs,[f for f in fams],fontsize=6,loc="upper left",ncol=3,bbox_to_anchor=(1.0,1.0))
    fig.savefig(fn,bbox_inches="tight");plt.close(fig)
whole(out+"/die_%s.png"%label,title="S81 %s : partitions by family, red star = clock spine root, hatch = die channels"%label)
for i,(xl,yl) in enumerate([((0,W/2),(0,H/2)),((W/2,W),(0,H/2)),((0,W/2),(H/2,H)),((W/2,W),(H/2,H))]):
    whole(out+"/die_%s_q%d.png"%(label,i),xl,yl,True,"S81 %s quadrant %d (label: name, WxH, fill%% = core+cell, aspect, ft band N/S|E/W um, taps, hops>405)"%(label,i))
# leaf closeups
leafs=sorted([r for r in rows if r["family"]=="ot_s81sl_leaf"],key=lambda r:r["core_fill"]+r["cell_fill"])
sel=[leafs[0],leafs[len(leafs)//2],leafs[-1]] if leafs else []
for r in sel:
    x=pt[r["type"]]; w,h=x["outline_um"]
    fig,ax=plt.subplots(figsize=(12,10.5),dpi=100)
    ax.add_patch(Rectangle((0,0),w,h,fill=False,lw=1.5))
    for c in x.get("hard_cores",[]):
        x0,y0,x1,y1=crect(c); ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc="tab:orange",alpha=0.6,ec="k",lw=0.5))
        ax.text((x0+x1)/2,(y0+y1)/2,c["inst"].split(".")[-1],fontsize=5,ha="center")
    for (face,a,b,bits) in r["bands"]:
        if face in "NS": ax.add_patch(Rectangle((a,0 if face=="S" else h-30),b-a,30,fc="tab:blue",alpha=0.4))
        else: ax.add_patch(Rectangle((0 if face=="W" else w-30,a),30,b-a,fc="tab:green",alpha=0.4))
    for s in x.get("internal_stations",[]):
        pts=[s["from_um"]]+list(s.get("regs_um",[]))+[s["to_um"]]
        ax.plot([p[0] for p in pts],[p[1] for p in pts],"-",lw=0.3,c="tab:purple")
    for t in x["clock"].get("taps",[]): ax.plot(*t["xy"],"r.",ms=4)
    ax.set_xlim(-20,w+20);ax.set_ylim(-20,h+20);ax.set_aspect("equal")
    ax.set_title("%s  %dx%d  coreFill %.1f%% cellFill %.1f%%  cores bbox %.0f%% of slot, Xocc %.0f/%.0f Yocc %.0f/%.0f  bandNS %.0f um bandEW %.0f um (blue/green)  taps %d"%(r["type"],w,h,100*r["core_fill"],100*r["cell_fill"],100*r["bbox_frac"],r["Xocc"],w,r["Yocc"],h,r["band_ns"],r["band_ew"],r["n_taps"]),fontsize=8)
    fig.savefig(out+"/leaf_%s_%s.png"%(r["type"],label),bbox_inches="tight");plt.close(fig)
# dataflow: family nodes at centroid, edges by ports
cent={}
pp={p["name"]:p for p in parts}
acc=collections.defaultdict(lambda:[0,0,0.0])
for p in parts:
    x,y,w,h=rect(p); f=T[p["type"]]["family"]; a=acc[f]; a[0]+=x+w/2;a[1]+=y+h/2;a[2]+=1
for f,a in acc.items(): cent[f]=(a[0]/a[2],a[1]/a[2])
lat={l["id"]:l.get("fixed_cycles",0) for l in P["lanes"]}
lane_of={}
for l in P["lanes"]:
    for pid in l["ports"]: lane_of[pid]=l["id"]
E=collections.defaultdict(lambda:[0,0,0])
for po in P["ports"]:
    s=po["src"]["part"];d=po["dst"]["part"]
    if s not in pp or d not in pp: continue
    fs,fd=T[pp[s]["type"]]["family"],T[pp[d]["type"]]["family"]
    if fs==fd: continue
    e=E[(fs,fd)]; e[0]+=po["width"]; e[1]=max(e[1],lat.get(lane_of.get(po["id"]),0)); e[2]+=1
fig,ax=plt.subplots(figsize=(18,14),dpi=100)
for f,(cx,cy) in cent.items():
    ax.text(cx,cy,"%s\n%d types/%d inst"%(f,FS[f]["types"],FS[f]["inst"]),ha="center",va="center",fontsize=6.5,bbox=dict(fc=fc[f],alpha=0.7,boxstyle="round"))
mx=max([e[0] for e in E.values()] or [1])
for (a,b),e in E.items():
    (x0,y0),(x1,y1)=cent[a],cent[b]
    ax.annotate("",xy=(x1,y1),xytext=(x0,y0),arrowprops=dict(arrowstyle="->",lw=0.3+4.5*e[0]/mx,alpha=0.35,color="k",shrinkA=18,shrinkB=18))
    if e[0]>mx*0.04: ax.text((x0+x1)/2,(y0+y1)/2,"%db/%dcyc"%(e[0],e[1]),fontsize=5,color="darkred")
ax.set_xlim(0,W);ax.set_ylim(0,H);ax.set_aspect("equal");ax.set_title("S81 %s data flow: family nodes at die centroids, arrow width ~ crossing bits, label = bits / max lane fixed_cycles"%label)
fig.savefig(out+"/dataflow_%s.png"%label,bbox_inches="tight");plt.close(fig)
json.dump({"%s>%s"%k:v for k,v in E.items()},open(out+"/dataflow_%s.json"%label,"w"),indent=0)
print("done",out)
