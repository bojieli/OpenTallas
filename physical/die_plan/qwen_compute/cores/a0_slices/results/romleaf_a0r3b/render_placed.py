import csv,sys,matplotlib;matplotlib.use("Agg");import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
src,out=sys.argv[1],sys.argv[2]
f,ax=plt.subplots(figsize=(14,9.2));ax.add_patch(Rectangle((0,0),172.8,110.16,fill=False,lw=1.5))
col={"std":"#9ab","ff":"#d33","buf":"#2a2","tap":"#ccc"};pins=[]
for r in csv.DictReader(open(src)):
    x,y,w,h=map(float,(r["x"],r["y"],r["w"],r["h"]))
    if r["kind"]=="macro": ax.add_patch(Rectangle((x,y),w,h,fc="#fd8",ec="k",alpha=.6));ax.text(x+w/2,y+h-4,r["master"],ha="center")
    elif r["kind"]=="pin": pins.append((r["name"],x,y))
    else: ax.add_patch(Rectangle((x,y),w,h,fc=col[r["kind"]],ec="none"))
for n,x,y in pins:
    if n=="clk": ax.plot(x,y,"*",ms=22,c="m");ax.annotate("clk M5 (%.2f,%.2f)"%(x,y),(x,y),(x+6,y+5),color="m",fontsize=12)
    else: ax.plot(x,y,"|",c="b",ms=4)
ax.set_xlim(-3,176);ax.set_ylim(-3,113);ax.set_aspect("equal")
ax.set_title("ot_qwen_tile_romleaf_a0r3b placed: red=flop green=buf grey=std blue=pins ("+str(len(pins))+")")
f.savefig(out,dpi=110,bbox_inches="tight")
