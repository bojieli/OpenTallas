import json, sys, numpy as np
W=sys.argv[1]; LOG=sys.argv[2]
def f32(u): return np.array(u,dtype=np.uint32).view(np.float32)
def w2f(h,n): h=h.rjust(8*n,'0'); return f32([int(h[8*n-8*(q+1):8*n-8*q],16) for q in range(n)])
def bf16(x):
    u=np.asarray(x,dtype=np.float32).view(np.uint32).astype(np.uint64); r=((u>>16)&1)+0x7fff; return (((u+r)>>16)<<16).astype(np.uint32).view(np.float32)
fx='/srv/opentallas-scratch/claude/qw-realstg/fx'
z=np.load(f'{fx}/L0_mat_qkv.npz'); xb=bf16(z['x']); print('qkv x n',len(xb),'absmax',np.abs(xb).max(),'mean abs',np.abs(xb).mean())
g=json.load(open(W+'/prep/gold.json'))
beats=g['qkv']['x_beats']; print('beats',len(beats),beats[0]['eaddr'])
# reconstruct x from beats payload
bx=[]
for b in beats:
    v=int(b['payload'],16); bx+= [ (v>>(16*q))&0xffff for q in range(64)]
bx=f32([u<<16 for u in bx]); print('beat-x == fixture bf16 x:', np.array_equal(bx[:len(xb)],xb))
tx=[]; last=None
for ln in open(LOG):
    p=ln.split()
    if len(p)>=3 and p[1]=='TX' and 135<=int(p[0])<400:
        if p[2]!=last: tx.append((int(p[0])-135,w2f(p[2],4))); last=p[2]
    if len(p)>=3 and p[1]=='TGO' and int(p[0])<400: print('TGO at',int(p[0])-135)
for c,v in tx[:12]:
    idx=[[int(i) for i in np.nonzero(xb==e)[0][:6]] for e in v]
    print(c, v, idx)
print('--- base search: lane i of tuple k == x[b_i + k*s] ?')
T=[v for c,v in tx[:8]]
for i in range(4):
    for s in (1,8,64,512):
        bs=[b for b in range(len(xb)-7*s) if all(xb[b+k*s]==T[k][i] for k in range(8))]
        if bs: print(' lane',i,'stride',s,'bases',bs[:8])
