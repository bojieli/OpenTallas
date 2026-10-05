import re,sys,collections
c=collections.Counter(); w={}
for l in open(sys.argv[1]):
    m=re.match(r'^(\S+)\s.*\s(-?\d+\.\d+) \(VIOLATED\)',l)
    if not m: continue
    n=m.group(1); s=float(m.group(2))
    k=re.sub(r'\[\d+\]','[]',n); k=re.sub(r'\$_.*','',k); k=k.rsplit('.',1)[0] if '.' in k else k
    k=re.sub(r'g_mac\[\]','g_mac[*]',k)
    c[k]+=1; w[k]=min(w.get(k,0),s)
tot=sum(c.values()); print('violating endpoints',tot)
for k,v in sorted(c.items(), key=lambda x:w[x[0]])[:40]: print(f'{w[k]:9.1f} {v:6d} {k}')
