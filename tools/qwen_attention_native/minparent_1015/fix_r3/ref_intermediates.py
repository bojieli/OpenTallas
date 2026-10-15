import sys,numpy as np
sys.path.insert(0,'/home/ubuntu/wt/codex-q-native-attention2-1014/tools')
import qwen_tp8_attention_native as N
R=N.R;G=R.G
N.configure(3072)
vd=sys.argv[1]
q=np.array([int(x,16) for x in open(vd+'/q.hex').read().split()],dtype=np.uint32).view(np.float32).reshape(4,128)
tab=R.fp8_table()
rows=open(vd+'/kv.hex').read().split()
T=8192
def dec(r): b=bytes.fromhex(r)[::-1]; return tab[np.frombuffer(b,dtype=np.uint8)]
K=np.stack([dec(rows[t]) for t in range(T)])[:,None,:].astype(np.float32)
V=np.stack([dec(rows[T+t]) for t in range(T)])[:,None,:].astype(np.float32)
gold=np.array([int(x,16) for x in open(vd+'/gold.hex').read().split()],dtype=np.uint32)
g2=R.golden_die(q,K,V)
print('golden reproduces', (G.bits(g2).reshape(-1)==gold).all())
for h in range(4):
  sc=G.mul(G.matvec_il(K[:,0,:],G.to_bf16(q[h]),R.S_SC),R.SCALE)
  m=sc.max(); e=G.exp(G.add(sc,G.neg(m))); Z=G.lane_sum(e); rz=G.reciprocal(np.array([Z],dtype=np.float32))[0]
  eb=G.to_bf16(e)
  # PV chunks: c = t mod 256, sequential from +0
  ch=np.zeros((256,128),dtype=np.float32)
  for c in range(256):
    acc=np.zeros(128,dtype=np.float32)
    for t in range(c,T,256): acc=G.add(acc,G.mul(V[t,0,:],eb[t]))
    ch[c]=acc
  p0=R.tree([ch[c] for c in range(128)]); p1=R.tree([ch[c] for c in range(128,256)])
  pv=G.add(p0,p1); out=G.mul(pv,rz)
  print(f'h{h} M={int(G.bits(m)):08x} Z={int(G.bits(Z)):08x} rz={int(G.bits(rz)):08x} p0[0:4]={[f"{int(x):08x}" for x in G.bits(p0[:4])]} p1[0:4]={[f"{int(x):08x}" for x in G.bits(p1[:4])]} out[0:4]={[f"{int(x):08x}" for x in G.bits(out[:4])]} gold[0:4]={[f"{x:08x}" for x in gold[h*128:h*128+4]]}')
