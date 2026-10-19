import json, sys, numpy as np
W=sys.argv[1]; LOG=sys.argv[2]
def f32(u): return np.array(u,dtype=np.uint32).view(np.float32)
def w2f(h,n): h=h.rjust(8*n,'0'); return f32([int(h[8*n-8*(q+1):8*n-8*q],16) for q in range(n)])
def bf16(x):
    u=np.asarray(x,dtype=np.float32).view(np.uint32).astype(np.uint64); r=((u>>16)&1)+0x7fff; return (((u+r)>>16)<<16).astype(np.uint32).view(np.float32)
fx='/srv/opentallas-scratch/claude/qw-realstg/fx'
z=np.load(f'{fx}/L0_mat_qkv.npz'); w=z['w'].astype(np.float32); xb=bf16(z['x'])
to=[(int(p[0])-135,w2f(p[-1],16)) for p in (l.split() for l in open(LOG)) if len(p)>=3 and p[1]=='TOUT' and int(p[0])<1500]
print('TOUT edges', [c for c,_ in to][:10], '...', to[-1][0])
kc=8
def grp(gg, chunk, j, k): return w[16*j:16*j+16, kc*(gg%512)+k]*xb[kc*chunk+k]
for label, chunks in (('served x (tid 26 chunks 104..107)',[104,105,106,107]),('intended (chunks 64..67)',[64,65,66,67])):
    A={}; B={}
    for j in range(8):
        acc=[np.zeros(16,np.float32) for _ in range(4)]
        for k in range(kc):
            pr=[grp(64+i,chunks[i],j,k).astype(np.float32) for i in range(4)]
            A[(k,j)]=((pr[0]+pr[1])+(pr[2]+pr[3]))
            acc=[(acc[i]+pr[i]).astype(np.float32) for i in range(4)]
            B[(k,j)]=((acc[0]+acc[1])+(acc[2]+acc[3]))
    for name,H in (('per-issue',A),('running acc',B)):
        hits=[]
        for n,(c,v) in enumerate(to):
            m=[key for key in H if np.array_equal(H[key],v)]
            hits.append(m[0] if m else None)
        print(label, name, 'exact', sum(h is not None for h in hits), '/', len(to), hits[:10])
