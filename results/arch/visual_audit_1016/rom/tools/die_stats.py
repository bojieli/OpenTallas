import json,sys,collections
d=json.load(open(sys.argv[1])); x0,y0,x1,y1=d['die']; A=(x1-x0)*(y1-y0)
bl=d['blocks']; print('die',round(x1-x0),round(y1-y0),'mm2',round(A/1e6,1),'blocks',len(bl),'stats',d.get('stats'))
bym=collections.defaultdict(lambda:[0,0.0,None])
for n,m,a,b,c,e in bl:
    r=bym[m]; r[0]+=1; r[1]+=(c-a)*(e-b); r[2]=(round(c-a,1),round(e-b,1))
for m,(k,ar,sz) in sorted(bym.items(),key=lambda kv:-kv[1][1])[:int(sys.argv[2]) if len(sys.argv)>2 else 30]:
    print(f'{m:40s} n={k:5d} area_mm2={ar/1e6:8.2f} size={sz}')
# empty area: grid 100um, cell empty if no block overlaps
G=100; nx=int((x1-x0)/G)+1; ny=int((y1-y0)/G)+1
occ=bytearray(nx*ny)
for n,m,a,b,c,e in bl:
    for j in range(int((b-y0)/G),min(ny,int((e-y0)/G)+1)):
        for i in range(int((a-x0)/G),min(nx,int((c-x0)/G)+1)): occ[j*nx+i]=1
print('block-covered frac (100um grid)',round(sum(occ)/len(occ),3))
