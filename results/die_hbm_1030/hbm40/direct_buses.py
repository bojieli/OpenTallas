import json,sys,collections,re
j=json.load(open(sys.argv[1]))
B=j['buses']; print('buses',len(B), 'keys', list(B[0].keys()))
g=collections.defaultdict(list)
for b in B:
    if b.get('lane') in (None,'') :
        g[(b['src'],b['dst'])].append(b)
print('direct pairs',len(g))
out=[]
for k,bs in sorted(g.items(), key=lambda kv:-sum(b['width'] for b in kv[1])):
    w=sum(b['width'] for b in bs)
    lv=collections.Counter()
    for b in bs:
        for l in b.get('leaves',[]): lv[re.sub(r'\[\d+\]$','',l)]+=b['width'] if len(b.get('leaves',[]))==1 else 0
    names=[ (b.get('leaves') or ['?'])[0]+f"({b['width']})" for b in sorted(bs,key=lambda b:-b['width'])[:5]]
    print(f"{k[0]}->{k[1]}\t{w}\t{len(bs)} buses\t"+'; '.join(names))
