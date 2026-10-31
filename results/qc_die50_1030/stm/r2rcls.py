import sys,re,math
from collections import Counter,defaultdict,deque
sys.path.insert(0,sys.argv[2])
import geom_rules as G
D=G.Design(sys.argv[1],(),False)
def grp(n):
    n=n.replace('\\','')
    s=n.split('/')[0].split('.')
    k='.'.join(s[:3]); k=re.sub(r'\[\d+\]','[]',k); k=re.sub(r'_\d+(?=$|\.)','_N',k); k=re.sub(r'\$.*','',k)
    return k
# replicate r2r_metrics but record per capture
seq={cid for cid,c in D.cells.items() if c[0]=='S'}
comb={cid for cid,c in D.cells.items() if c[0] in 'BLK'}
st={};indeg=Counter();succ=defaultdict(list)
for cid in comb:
    for n in D.drives.get(cid,[]):
        for s in D.nets[n][2]:
            if s[0]=='i' and not s[2] and s[1] in comb: succ[cid].append(s[1]);indeg[s[1]]+=1
def merge(dst,*e):
    o=st.get(dst)
    if o is None: st[dst]=list(e);return
    if e[0]<o[0]:o[0],o[4]=e[0],e[4]
    if e[1]>o[1]:o[1],o[5]=e[1],e[5]
    if e[2]<o[2]:o[2],o[6]=e[2],e[6]
    if e[3]>o[3]:o[3],o[7]=e[3],e[7]
caps=defaultdict(list)
def b(cid):
    x,y=G.ctr(D.cells[cid]);return x+y,x+y,x-y,x-y
for cid in seq:
    u0,u1,v0,v1=b(cid)
    for n in D.drives.get(cid,[]):
        for s in D.nets[n][2]:
            if s[0]!='i' or s[2]: continue
            if s[1] in seq: caps[s[1]].append((u0,u1,v0,v1,cid,cid,cid,cid))
            elif s[1] in comb: merge(s[1],u0,u1,v0,v1,cid,cid,cid,cid)
dq=deque(c for c in comb if indeg[c]==0)
while dq:
    cid=dq.popleft();e=st.get(cid)
    for n in D.drives.get(cid,[]):
        for s in D.nets[n][2]:
            if s[0]!='i' or s[2]: continue
            if e is not None:
                if s[1] in seq: caps[s[1]].append(tuple(e))
                elif s[1] in comb: merge(s[1],*e)
    for t in succ.get(cid,[]):
        indeg[t]-=1
        if indeg[t]==0: dq.append(t)
C=Counter();W={}
for cap,lst in caps.items():
    u0,u1,v0,v1=b(cap);mx,src=0,None
    for e in lst:
        for val,s in ((u1-e[0],e[4]),(e[1]-u0,e[5]),(v1-e[2],e[6]),(e[3]-v0,e[7])):
            if val>mx: mx,src=val,s
    if mx>405:
        k=(grp(D.cells[src][6]),grp(D.cells[cap][6]));C[k]+=1
        if mx>W.get(k,(0,))[0]: W[k]=(mx,D.cells[src][6],D.cells[cap][6])
for k,v in C.most_common(40): print(v,round(W[k][0]),k[0],'->',k[1],'|',W[k][1][:60],'->',W[k][2][:60])
print('total',sum(C.values()))
