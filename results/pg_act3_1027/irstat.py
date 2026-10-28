import sys,csv,collections
f=sys.argv[1]; vs=float(sys.argv[2]) if len(sys.argv)>2 else 0.7
gnd = vs==0.0
rows=[]; byl=collections.defaultdict(list)
with open(f) as fh:
    r=csv.reader(fh); next(r)
    for row in r:
        v=float(row[5]); d=(v if gnd else vs-v)*1e3
        x=float(row[3]); y=float(row[4])
        rows.append((d,x,y,row[0],row[2]))
rows.sort(reverse=True)
n=len(rows); print('n',n)
for q in [0,0.0001,0.001,0.01,0.05,0.5]:
    print('pct',q,round(rows[int(q*n)][0],3))
print('top', rows[:8])
xs=[r[1] for r in rows]; ys=[r[2] for r in rows]
print('bbox',min(xs),max(xs),min(ys),max(ys))
# worst by 100um bins
b=collections.defaultdict(float)
for d,x,y,_,_ in rows:
    k=(int(x//100),int(y//100)); b[k]=max(b[k],d)
ks=sorted(b.items(), key=lambda t:-t[1])
print('worst bins',ks[:10]); print('best bins', ks[-5:])
# interior: exclude 50um margin
mx0,mx1,my0,my1=min(xs)+50,max(xs)-50,min(ys)+50,max(ys)-50
ins=[r for r in rows if mx0<r[1]<mx1 and my0<r[2]<my1]
print('interior50 worst',ins[0])
