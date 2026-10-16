import json,sys,collections,math
P=json.load(open(sys.argv[1])); W,H=31018.4,21277.693
G=20.0
nx,ny=int(W/G)+1,int(H/G)+1
occ=bytearray(nx*ny)
fam=collections.Counter(); 
for k,b in P.items():
    w,h=(b['w'],b['h']) if b.get('orient','R0') in('R0','R180','MX','MY') else (b['h'],b['w'])
    fam[k.split('_')[0]]+=w*h/1e6
    for j in range(int(b['y']/G),min(ny,int((b['y']+h)/G))):
        for i in range(int(b['x']/G),min(nx,int((b['x']+w)/G))): occ[j*nx+i]=1
tot=sum(fam.values())
print('blocks mm2 %.1f of %.1f; empty %.1f mm2'%(tot,W*H/1e6,W*H/1e6-tot))
for f,a in fam.most_common(): print(' %-6s %.1f'%(f,a))
# connected empty regions
seen=bytearray(nx*ny); regs=[]
for s in range(nx*ny):
    if occ[s] or seen[s]: continue
    st=[s]; seen[s]=1; cells=[]
    while st:
        c=st.pop(); cells.append(c); i,j=c%nx,c//nx
        for di,dj in((1,0),(-1,0),(0,1),(0,-1)):
            a,b2=i+di,j+dj
            if 0<=a<nx and 0<=b2<ny:
                q=b2*nx+a
                if not occ[q] and not seen[q]: seen[q]=1; st.append(q)
    xs=[c%nx for c in cells]; ys=[c//nx for c in cells]
    regs.append((len(cells)*G*G/1e6,min(xs)*G,min(ys)*G,(max(xs)+1)*G,(max(ys)+1)*G))
regs.sort(reverse=True)
print('empty regions (4-connected, 20um grid): n=%d'%len(regs))
for r in regs[:12]: print('  %.2f mm2 bbox x %.0f-%.0f y %.0f-%.0f'%r)
# maximal empty rectangles: scan for big empty rectangles by histogram method
hgt=[0]*nx; best=[]
for j in range(ny):
    for i in range(nx): hgt[i]=hgt[i]+1 if not occ[j*nx+i] else 0
    stk=[]
    for i in range(nx+1):
        hh=hgt[i] if i<nx else 0; start=i
        while stk and stk[-1][1]>=hh:
            s0,h0=stk.pop(); area=h0*(i-s0)
            if area*G*G>1.0e6: best.append((area*G*G/1e6,s0*G,(j-h0+1)*G,i*G,(j+1)*G))
            start=s0
        stk.append((start,hh))
best.sort(reverse=True); out=[]
for b in best:
    if all(not(b[1]<o[3] and o[1]<b[3] and b[2]<o[4] and o[2]<b[4]) for o in out): out.append(b)
    if len(out)>=10: break
print('largest disjoint empty rectangles:')
for r in out: print('  %.2f mm2  x %.0f-%.0f y %.0f-%.0f (%.0f x %.0f um)'%(r[0],r[1],r[3],r[2],r[4],r[3]-r[1],r[4]-r[2]))
