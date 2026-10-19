import sys,re,collections
yb=collections.Counter(); cap=collections.Counter(); typ=collections.Counter(); xb=collections.Counter()
t=None;c=None
for l in open(sys.argv[1]):
    if l.startswith('violation type'): t=l.split(':')[1].strip()
    elif 'comment' in l:
        m=re.search(r'capacity:(\d+) usage:(\d+) congestion:(\d+)',l); c=m.groups()
    elif 'bbox' in l:
        m=re.findall(r'[\d.]+',l); x,y=float(m[0]),float(m[1]); o=int(c[2])
        yb[int(y//500)*500]+=o; xb[int(x//2000)*2000]+=o; cap['cap0' if c[0]=='0' else 'cap>0']+=o; typ[t]+=o
print('type',dict(typ)); print('cap',dict(cap))
print('y500',sorted(yb.items(),key=lambda x:-x[1])[:10]); print('x2000',sorted(xb.items(),key=lambda x:-x[1])[:10])
