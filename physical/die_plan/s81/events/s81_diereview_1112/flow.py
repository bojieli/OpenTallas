import json,sys,collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
E=json.load(open(sys.argv[1])); F=json.load(open(sys.argv[2])); out=sys.argv[3]
grp={"col_h9_r0":"FRAME bank r0 (col_h9/h10)","col_h9_r1":"FRAME bank r1","col_h9_r2":"FRAME bank r2","col_h10_r0":"FRAME bank r0 (col_h9/h10)","col_h10_r1":"FRAME bank r1","col_h10_r2":"FRAME bank r2",
"serdes":"SerDes lk (14)","slice_station":"slice_station (46 ft stations)","ot_s81sl_leaf":"LEAF (75)","ot_s81sl_kv_leaf":"kv_leaf (5)",
"svc_hi_dsdv_svc_rs":"svc hi rs (6)","svc_lo_dsdv_svc_rs":"svc lo rs (7+1)","svc_lo_dsdv_svc_rs_w":"svc lo rs (7+1)","svc_hi_dsdv_svc_pvso_entry":"pvso_entry (2)","phy":"phy_hbm","eng":"eng","bk_sel":"bk_sel / gunit / iqf / seqhost","gunit":"bk_sel / gunit / iqf / seqhost","iqf":"bk_sel / gunit / iqf / seqhost","seqhost":"bk_sel / gunit / iqf / seqhost"}
def g(f): return grp.get(f,"SLICE C/LP (c1x/lepe/lepw/iq/kv512/c3x) (21)")
pos={"FRAME bank r0 (col_h9/h10)":(0.1,0.80),"FRAME bank r1":(0.1,0.50),"FRAME bank r2":(0.1,0.20),
"SerDes lk (14)":(0.42,0.92),"slice_station (46 ft stations)":(0.42,0.66),"LEAF (75)":(0.42,0.40),"SLICE C/LP (c1x/lepe/lepw/iq/kv512/c3x) (21)":(0.42,0.14),
"kv_leaf (5)":(0.68,0.40),"svc hi rs (6)":(0.88,0.80),"svc lo rs (7+1)":(0.88,0.56),"pvso_entry (2)":(0.68,0.80),"phy_hbm":(0.88,0.32),"eng":(0.88,0.10),"bk_sel / gunit / iqf / seqhost":(0.68,0.14)}
A=collections.defaultdict(lambda:[0,0,0])
for k,v in E.items():
    a,b=k.split(">"); a,b=g(a),g(b)
    if a==b: continue
    e=A[(a,b)]; e[0]+=v[0]; e[1]=max(e[1],v[1]); e[2]+=v[2]
inst=collections.defaultdict(lambda:[0,0.0])
for f,v in F.items(): n=inst[g(f)]; n[0]+=v["inst"]; n[1]+=v["area"]/1e6
fig,ax=plt.subplots(figsize=(17,11),dpi=100); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")
mx=max(e[0] for e in A.values())
for (a,b),e in A.items():
    if a not in pos or b not in pos or e[0]<0.02*mx: continue
    (x0,y0),(x1,y1)=pos[a],pos[b]
    ax.annotate("",xy=(x1,y1),xytext=(x0,y0),arrowprops=dict(arrowstyle="-|>",lw=0.5+5*e[0]/mx,alpha=0.35,connectionstyle="arc3,rad=0.12",shrinkA=34,shrinkB=34))
    ax.text((x0+x1)/2+0.01,(y0+y1)/2,"%d b / <=%d cyc"%(e[0],e[1]),fontsize=7,color="darkred")
for n,(x,y) in pos.items():
    i=inst[n]
    ax.text(x,y,"%s\n%d tiles, %.0f mm2"%(n,i[0],i[1]),ha="center",va="center",fontsize=9,bbox=dict(boxstyle="round",fc="lightyellow",ec="k"))
ax.set_title("S81 data flow, family level (ready12f): arrow width ~ bits crossing between families (sum over ports), label = bits / max lane fixed_cycles. FRAME banks = 36 col tiles/side x 2 chains; LEAF<->SLICE C = the x-feed/attention core", fontsize=10)
fig.savefig(out,bbox_inches="tight")
