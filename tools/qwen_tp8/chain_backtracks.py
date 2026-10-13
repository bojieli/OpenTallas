# usage: python3 tools/qwen_tp8/chain_backtracks.py ITDIR/rom_tp8b.json [N]  -> relay chains that double back (each back-and-forth hop is counted again by the cut scan)
import sys, json, collections, re
d=json.load(open(sys.argv[1])); I={i['n']:i for i in d['insts']}
cen=lambda n:(I[n]['x']+I[n]['w']/2, I[n]['y']+I[n]['h']/2)
ch=collections.defaultdict(list)
for b,c,bits,eps in d['buses']:
    base=re.sub(r'__r\d+$','',b); k=int(b.rsplit('__r',1)[1]) if '__r' in b else 0
    if len(eps)==2 and all(e in I for e in eps): ch[(base,c,bits)].append((k,eps))
out=[]
for (b,c,bits),L in ch.items():
    L.sort(); pts=[cen(L[0][1][0])]+[cen(e[1]) for _,e in L]
    mh=lambda a,q:abs(a[0]-q[0])+abs(a[1]-q[1])
    n=sum(1 for i in range(1,len(pts)-1) if mh(pts[i],pts[i+1])>mh(pts[i-1],pts[i+1])+20)
    if n: out.append((n*bits,n,b,c,bits,[tuple(map(round,p)) for p in pts[:3]]))
out.sort(reverse=True)
print(len(out),'chains double back')
for o in out[:int(sys.argv[2]) if len(sys.argv)>2 else 25]: print(o)
