import sys,re,collections
f=sys.argv[1]; by=float(sys.argv[2]) if len(sys.argv)>2 else 200
H=collections.Counter();V=collections.Counter();X=collections.Counter();N=collections.Counter()
typ=None;cong=0;srcs=[]
for line in open(f):
    if line.startswith('violation type'):
        typ='H' if 'Horizontal' in line else 'V'
    elif 'srcs:' in line:
        srcs=re.findall(r'net:(\S+)',line)
    elif 'congestion:' in line:
        cong=int(line.rsplit('congestion:',1)[1])
    elif line.strip().startswith('bbox'):
        m=re.findall(r'[-\d.]+',line.split('=')[1]); x=float(m[0]);y=float(m[1])
        b=int(y//by)
        (H if typ=='H' else V)[b]+=cong
        X[(typ,int(x//100))]+=cong
        for s in srcs:
            k=re.sub(r'_\d+(_\d+)?$','',s); N[k]+=cong/len(srcs)
print('y-bin(um)  H  V')
for b in sorted(set(H)|set(V)): print(f'{b*by:6.0f} {H[b]:8d} {V[b]:8d}')
print('x-bin100 H/V'); 
for t in 'HV': print(t,[ (k[1]*100,X[k]) for k in sorted(X) if k[0]==t])
print('top net groups'); 
for k,v in N.most_common(15): print(f'{k:40s} {v:10.0f}')
print('TOTAL H',sum(H.values()),'V',sum(V.values()))
