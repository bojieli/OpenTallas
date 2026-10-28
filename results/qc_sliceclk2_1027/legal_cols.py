import sys,json,collections
sys.path.insert(0,sys.argv[1])
import schema as S, die_trial as DT
from pathlib import Path
P=S.Plan(S.load(sys.argv[2]),Path(sys.argv[2]))
R=json.load(open(sys.argv[3]))["part_region"]
site=DT.SiteMap(P)
# slice boxes
box=collections.defaultdict(lambda:[1e9,1e9,-1e9,-1e9])
for n,p in P.parts.items():
    r=R.get(n); w,h=P.types[p["type"]]["outline_um"]; ox,oy=p["origin_um"]
    b=box[r]; b[0]=min(b[0],ox);b[1]=min(b[1],oy);b[2]=max(b[2],ox+w);b[3]=max(b[3],oy+h)
for r in sorted(box): print(r,[round(v) for v in box[r]])
rn=sys.argv[4]; x0,y0,x1,y1=box[rn]
# columns: fraction of y legal
ys=[y0+5+i*10 for i in range(int((y1-y0-10)/10))]
best=[]
x=x0+1
while x<x1-1:
    ok=sum(site.legal((x,y)) for y in ys)/len(ys)
    best.append((ok,round(x,2)))
    x+=2.16
best.sort(reverse=True)
print("top columns (legal frac, x):",best[:15])
# rows: per y, fraction legal across x
xs=[x0+2+i*4 for i in range(int((x1-x0-4)/4))]
rows=[]
y=y0+1
while y<y1-1:
    rows.append((sum(site.legal((xx,y)) for xx in xs)/len(xs),round(y,1))); y+=4.32
fully=[r[1] for r in rows if r[0]>0.999]
print("full-width legal rows:",len(fully),"of",len(rows))
# cluster rows into bands
bands=[];
for yv in fully:
    if bands and yv-bands[-1][1]<=4.33: bands[-1][1]=yv
    else: bands.append([yv,yv])
print("bands",[(round(a),round(b-a)) for a,b in bands][:80])
# per-part types in slice ordered by y
pl=sorted([(p["origin_um"][1],n,P.types[p["type"]]["outline_um"],p["origin_um"][0]) for n,p in P.parts.items() if R.get(n)==rn])
for yv,n,o,xv in pl: print(round(xv),round(yv),n,o)
