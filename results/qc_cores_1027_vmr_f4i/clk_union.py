exec(open('/work/clkdiff.py').read().split('A = load(')[0])
def canonical(s):
    result={}
    for layer in set(r[0] for r in s):
        rr=[r[1:] for r in s if r[0]==layer]
        if layer=='V': result[layer]=tuple(sorted(rr));continue
        xx=sorted(set(v for r in rr for v in (r[0],r[2])))
        slabs=[]
        for x0,x1 in zip(xx,xx[1:]):
            yy=sorted((r[1],r[3]) for r in rr if r[0]<x1 and r[2]>x0)
            merged=[]
            for y0,y1 in yy:
                if merged and y0<=merged[-1][1]:merged[-1]=(merged[-1][0],max(y1,merged[-1][1]))
                else:merged.append((y0,y1))
            val=tuple(merged)
            if slabs and slabs[-1][2]==val and slabs[-1][1]==x0:slabs[-1]=(slabs[-1][0],x1,val)
            elif val:slabs.append((x0,x1,val))
        result[layer]=tuple(slabs)
    return result
A=load(os.environ['A']);B=load(os.environ['B']); changed=[]
for n in A:
    a=canonical(A[n]);b=canonical(B.get(n,set()))
    if a!=b:changed.append(n);print('UNION_DIFFERENT',n,[(l,len(a.get(l,())),len(b.get(l,()))) for l in set(a)|set(b) if a.get(l)!=b.get(l)])
print('CLKUNION changed_nets',len(changed),'of',len(A))
