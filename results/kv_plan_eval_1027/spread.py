import json,sys,numpy as np
e=json.load(open(sys.argv[1]))
DX=DY=5.0; cap=32*0.6
def demand(t, mode):
    W,H=t["outline_um"]; nx,ny=int(W//DX)+1,int(H//DY)+1; V=np.zeros((ny,nx)); bits=0
    for s in t.get("ft_slots",[]) or []:
        bs=s.get("bit_sites_um")
        if not bs: continue
        w=int(s["width"]); bits+=w
        for k in range(len(bs)-1):
            A,B=bs[k],bs[k+1]
            for b in range(w):
                a,c=A[b%len(A)],B[b%len(B)]
                if abs(a[1]-c[1])<DY: continue
                i0,i1=sorted((int(a[1]//DY),int(c[1]//DY)))
                if mode=="HV" or abs(a[0]-c[0])<15: j=min(int(c[0]//DX),nx-1)
                else:  # router spreads jogs over the x span: bit b of w at fraction (b+0.5)/w
                    x=min(a[0],c[0])+abs(a[0]-c[0])*(b+0.5)/w; j=min(int(x//DX),nx-1)
                V[i0:i1,j]+=1
    k=3; cs=np.cumsum(np.pad(V,((0,0),(1,0))),axis=1); S=cs[:,k:]-cs[:,:-k]
    i,j=np.unravel_index(np.argmax(S),S.shape)
    return round(S[i,j]/(cap*15),2),int(S[i,j]),j*DX,i*DY,bits,V
out=[]
for tn,t in e["partition_types"].items():
    if not any(s.get("bit_sites_um") for s in t.get("ft_slots",[]) or []): continue
    a=demand(t,"HV"); b=demand(t,"spread")
    out.append((b[0],a[0],tn,b[1],b[2],b[3],a[1],a[2]))
out.sort(reverse=True)
print("ratio_spread ratio_HV type bits_spread x y | bits_HV x")
for r in out[:12]: print(r)
print("types with spread ratio >1:",sum(1 for r in out if r[0]>1),"of",len(out))
