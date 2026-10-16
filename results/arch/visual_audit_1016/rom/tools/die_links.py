import json,sys,collections
d=json.load(open(sys.argv[1])); B={b[0]:b for b in d['blocks']}
def c(n): b=B[n]; return ((b[2]+b[4])/2,(b[3]+b[5])/2)
L=d.get('links',[]); print('links',len(L))
per=collections.defaultdict(lambda:[0,0.0,0.0,set()])
pairs=collections.defaultdict(lambda:[0,0.0,0])
for a,b,bits in L:
    if a not in B or b not in B: continue
    (ax,ay),(bx,by)=c(a),c(b); dist=abs(ax-bx)+abs(ay-by)
    for n in (a,b):
        r=per[B[n][1]]; r[0]+=bits; r[1]+=bits*dist; r[2]=max(r[2],dist); r[3].add(n)
    k=tuple(sorted((B[a][1],B[b][1]))); p=pairs[k]; p[0]+=bits; p[1]+=bits*dist; p[2]+=1
print('== per master: bits, bit-weighted mean dist um, max dist um')
for m,(bits,bd,mx,s) in sorted(per.items(),key=lambda kv:-kv[1][1])[:int(sys.argv[2]) if len(sys.argv)>2 else 20]:
    print(f'{m:38s} insts={len(s):4d} bits={bits:7d} mean={bd/bits:7.0f} max={mx:7.0f}')
print('== master pairs by bit*dist')
for k,(bits,bd,n) in sorted(pairs.items(),key=lambda kv:-kv[1][1])[:int(sys.argv[3]) if len(sys.argv)>3 else 20]:
    print(f'{k[0]:30s} {k[1]:30s} links={n:5d} bits={bits:7d} mean={bd/bits:7.0f}')
