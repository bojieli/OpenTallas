import csv,collections,sys
R=list(csv.DictReader(open(sys.argv[1]),delimiter='\t'))
B=20.0;a=collections.Counter()
macro=0
for r in R:
    if r['bucket'] in('macro','pma_data_pin'):continue
    x,y,w,h=map(float,(r['x'],r['y'],r['w'],r['h']))
    if 'TAP' in r['master'] or 'FILL' in r['master']: continue
    a[(int((x+w/2)//B),int((y+h/2)//B))]+=w*h
def st(box):
    x0,y0,x1,y1=box;v=[]
    for i in range(int(x0//B),int(x1//B)):
        for j in range(int(y0//B),int(y1//B)):v.append(a[(i,j)]/(B*B))
    v.sort();return dict(n=len(v),mean=round(sum(v)/len(v),3),p95=round(v[int(.95*len(v))],3),max=round(v[-1],3),over70=sum(u>.7 for u in v),over85=sum(u>.85 for u in v))
print('enc_box',st((2065,466,2265,666)))
print('east40',st((2225,466,2265,666)))
top=sorted(a.items(),key=lambda kv:-kv[1])[:12]
print('top bins',[(k[0]*20,k[1]*20,round(v/400,2)) for k,v in top])
print('all>.7',sum(v/400>.7 for v in a.values()), 'outside enc >.7',sum(v/400>.7 and not(2065<=k[0]*20<2265 and 466<=k[1]*20<666) for k,v in a.items()))
