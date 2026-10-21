import re,sys
cell_re=re.compile(r'^(\(\* [^*]*\*\) )?(qfd_bmath_\w+) #\(\.ID\(0\)\) (\\\S+ |[^\s(]+)\((.*)\);$')
pin_re=re.compile(r'\.(\w+)\(([^()]*)\)')
def load(f):
    C={};D={};other=[]
    for l in open(f):
        l=l.rstrip('\n');m=cell_re.match(l)
        if not m:
            if not l.startswith('wire '): other.append(l)
            continue
        t=m.group(2);pins=dict(pin_re.findall(m.group(4)));n=m.group(3).strip();C[n]=(t,pins)
        o=('Q',) if t.startswith('qfd_bmath_dff') else ('Y',)
        for p in o:
            if p in pins: D[pins[p]]=(t,tuple(sorted((q,v) for q,v in pins.items() if q not in o)))
    return C,D,other
a,da,oa=load(sys.argv[1]);b,db,ob=load(sys.argv[2])
assert oa==ob, 'non-cell lines differ'
import hashlib
sys.setrecursionlimit(100000)
def canon(D,memo):
    def c(net):
        if net in memo: return memo[net]
        d=D.get(net)
        if d is None or d[0].startswith('qfd_bmath_dff'): r=net
        else: r=hashlib.sha1((d[0]+'|'+'|'.join(q+'='+c(v) for q,v in d[1])).encode()).hexdigest()
        memo[net]=r; return r
    return c
ca=canon(da,{});cb=canon(db,{})
bad=0;moved=0
for n,(t,pins) in a.items():
    t2,p2=b[n]; assert t2==t
    for p,v in pins.items():
        if p2[p]!=v:
            moved+=1
            if ca(v)!=cb(p2[p]):
                bad+=1
                if bad<5: print("BAD",n,p,v,da.get(v),p2[p],db.get(p2[p]))
for n in b:
    if n not in a: assert n.startswith('u_qkorr_'), n
print('pins re-pointed',moved,'non-identical drivers',bad,'new cells',len(b)-len(a))
sys.exit(1 if bad else 0)
