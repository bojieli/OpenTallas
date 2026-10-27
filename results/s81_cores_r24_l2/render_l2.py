import json,sys,re
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
D=sys.argv[1]
d=json.load(open(f"{D}/plan_new.json")); pt=d["partition_types"]["gunit__t1"]
l2=json.load(open(f"{D}/l2_new.json"))["pins"]; l1={p["name"]:p for p in json.load(open(f"{D}/l1.json"))["pins"]}
l0={p["name"]:p for p in json.load(open(f"{D}/l0.json"))["pins"]}
fig,(a,b)=plt.subplots(1,2,figsize=(18,8),gridspec_kw={"width_ratios":[1.3,1]})
for c in pt["hard_cores"]:
    x,y=c["origin_um"]; w,h=c["outline_um"]; l2c=c["module"]=="dsdv_gunit_l2"
    a.add_patch(Rectangle((x,y),w,h,fill=True,fc="#f6c" if l2c else "#cde",ec="k",lw=1.2,alpha=.6))
    a.text(x+w/2,y+h/2,c["inst"].split(".")[-1]+f"\n{w}x{h}",ha="center",va="center",fontsize=8)
a.add_patch(Rectangle((1175.04,17.28),345.6,172.8,fill=False,ec="r",ls="--",lw=1.5)); a.text(1180,25,"old L2 345.6x172.8",color="r",fontsize=8)
for bx in pt["buses"]:
    if bx["face"]=="S": a.plot(bx["window_um"],[0,0],lw=4); a.text(bx["window_um"][0],-25,bx["name"],fontsize=7)
ox,oy=1175.04,155.52
# L2.S -> L1.N bundle (sampled) and L2.N -> L0.S
pairs21=[("rs_o","rn_i"),("rs_i","rn_o"),("cws_d","cw_d"),("rct_b","ct_b"),("dl_a","dl_a"),("dl_b","dl_b")]
n=0
for p in l2:
    for s,t in pairs21:
        m=re.match(re.escape(s)+r"(\[\d+\])$",p["name"])
        if m and t+m.group(1) in l1 and int(m.group(1)[1:-1])%24==0:
            q=l1[t+m.group(1)]; a.plot([ox+p["x"],812.16+q["x"]],[oy+p["y"],207.36+q["y"]],c="orange",lw=.5); n+=1
a.set_xlim(650,2100); a.set_ylim(-40,700); a.set_aspect("equal"); a.set_title(f"gunit__t1 candidate: L2 345.6x34.56 @ (1175.04,155.52); orange = sampled L2.S->L1.N bundle (parent defect, unchanged)",fontsize=9)
col={"N":"r","S":"b","E":"g","W":"m"}
W,H=345.6,34.56
for p in l2:
    f="E" if abs(p["x"]-W)<2.5 else "S" if p["y"]<2.5 else "N" if abs(p["y"]-H)<2.5 else "C"
    b.plot(p["x"],p["y"],".",ms=1.5,c=col.get(f,"k"))
b.add_patch(Rectangle((0,0),W,H,fill=False,ec="k")); b.add_patch(Rectangle((4.32,4.32),W-8.64,H-8.64,fill=False,ec="gray",ls=":"))
b.set_xlim(-10,360); b.set_ylim(-10,45); b.set_aspect("equal")
b.set_title("L2 candidate pin table: N 1403 (red, M5), S 1469 (blue, M5), E 272 (green, M4 0.096 pitch)\ncore area dotted 336.96x25.92: any flop pair <= 362.9 um",fontsize=9)
b2=b.inset_axes([0.62,-1.25,0.36,1.1]); 
for p in l2:
    if abs(p["x"]-W)<2.5: b2.plot(p["x"],p["y"],".",ms=2,c="g")
b2.add_patch(Rectangle((300,0),W-300,H,fill=False,ec="k")); b2.set_xlim(335,350); b2.set_ylim(-2,37); b2.set_title("E face zoom",fontsize=8)
plt.tight_layout(); plt.savefig(f"{D}/l2_candidate.png",dpi=110)
print("bundle lines",n)
