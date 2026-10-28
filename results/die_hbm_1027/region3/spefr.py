import json,sys,re,statistics as st
d=sys.argv[1]; P=json.load(open(d+'/place.json'))
cur=None;R={};C={};drv={};ld={};sec=None
for l in open(d+'/native_TT.spef'):
    if l.startswith('*D_NET'): cur=l.split()[1]; R[cur]=0;C[cur]=float(l.split()[2]); sec=None; continue
    if l.startswith('*CONN'): sec='c';continue
    if l.startswith('*CAP'): sec='C';continue
    if l.startswith('*RES'): sec='R';continue
    if l.startswith('*END'): sec=None;continue
    if cur and sec=='R':
        f=l.split()
        if len(f)==4: R[cur]+=float(f[3])
    if cur and sec=='c' and l.startswith('*I'):
        f=l.split(); inst=f[1].split(':')[0]
        if f[2]=='O': drv[cur]=inst
        else: ld.setdefault(cur,[]).append(inst)
rs=[];cs=[]
for n in R:
    if n in drv and len(ld.get(n,[]))==1 and drv[n] in P and ld[n][0] in P:
        a,b=P[drv[n]],P[ld[n][0]]; L=abs(a['x']-b['x'])+abs(a['y']-b['y'])
        if L>200: rs.append(R[n]/L); cs.append(C[n]/L)
print('2-pin nets',len(rs),'R kohm/um median %.3e'%st.median(rs),'C fF/um median %.4f'%st.median(cs))
