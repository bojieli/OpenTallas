import csv,sys,collections,matplotlib;matplotlib.use("Agg");import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
src,out=sys.argv[1],sys.argv[2]
# rotated view: plot x = die y (0..432), plot y = die x (0..47.52)
f,ax=plt.subplots(figsize=(26,4.6));ax.add_patch(Rectangle((0,0),432,47.52,fill=False,lw=1.5))
ax.add_patch(Rectangle((4.32,4.32),427.68-4.32,43.2-4.32,fill=False,lw=.6,ls="--"))
col={"std":"#9ab","ff":"#d33","buf":"#2a2","tap":"#ccc"};pins=[];cnt=collections.Counter()
for r in csv.DictReader(open(src)):
    x,y,w,h=map(float,(r["x"],r["y"],r["w"],r["h"]));cnt[r["kind"]]+=1
    if r["kind"]=="macro": ax.add_patch(Rectangle((y,x),h,w,fc="#fd8",ec="k",alpha=.6))
    elif r["kind"]=="pin": pins.append((r["name"],x,y))
    else: ax.add_patch(Rectangle((y,x),h,w,fc=col.get(r["kind"],"#000"),ec="none"))
for n,x,y in pins:
    if n=="clk": ax.plot(y,x,"*",ms=18,c="m");ax.annotate("clk (%.2f,%.2f)"%(x,y),(y,x),(y+4,x+3),color="m")
    elif n=="rst_n": ax.plot(y,x,"s",ms=6,c="k")
    else: ax.plot(y,x,"_" if x<1 or x>46.5 else "|",c="b",ms=3)
ax.set_xlim(-3,435);ax.set_ylim(-3,50.5);ax.set_aspect("equal")
ax.set_xlabel("die y (um)");ax.set_ylabel("die x (um)")
ax.set_title("ot_qwen_tile_node_a0r3 placed (rotated 90: left=y0). red=flop green=buf grey=std blue=pins %d  %s"%(len(pins),dict(cnt)))
f.savefig(out,dpi=100,bbox_inches="tight")
