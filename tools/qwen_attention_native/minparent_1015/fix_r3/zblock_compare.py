import sys,re,numpy as np
sys.path.insert(0,'/home/ubuntu/wt/codex-q-native-attention2-1014/tools')
import qwen_tp8_attention_native as N
R=N.R;G=R.G;N.configure(3072)
vd='full8192';T=8192
q=np.array([int(x,16) for x in open(vd+'/q.hex').read().split()],dtype=np.uint32).view(np.float32).reshape(4,128)
tab=R.fp8_table();rows=open(vd+'/kv.hex').read().split()
K=np.stack([tab[np.frombuffer(bytes.fromhex(rows[t])[::-1],dtype=np.uint8)] for t in range(T)]).astype(np.float32)
E=[]
for h in range(4):
  sc=G.mul(G.matvec_il(K,G.to_bf16(q[h]),128),R.SCALE);m=sc.max();E.append(G.exp(G.add(sc,G.neg(m))))
E=np.stack(E)  # [4,T]
def block(h,s,k,e=E):
  base=512*k+128*s;ch=[]
  for c in range(16):
    acc=np.float32(0)
    for i in range(8): acc=G.add(np.array([acc],dtype=np.float32),np.array([e[h,base+8*c+i]],dtype=np.float32))[0]
    ch.append(np.array([acc],dtype=np.float32))
  return R.tree(ch)[0]
bad=0;n=0
for line in open('zdump.txt'):
  m=re.search(r's=(\d) type=1 g=0 hh=(\d) k=(\d+) any=1 data=([0-9a-f]+)',line);s,h,k,d=int(m[1]),int(m[2]),int(m[3]),int(m[4],16)
  ref=int(G.bits(np.array([block(h,s,k)],dtype=np.float32))[0]);n+=1
  if ref!=d:
    bad+=1
    if bad<=12: print(f's{s} h{h} k{k} dut={d:08x} ref={ref:08x} dut={np.uint32(d).view(np.float32):.6f} ref={np.uint32(ref).view(np.float32):.6f}')
print('blocks',n,'bad',bad)
# map each DUT entry to the reference (s,h,k) with identical bits
refmap={}
for s in range(4):
  for h in range(4):
    for k in range(16): refmap.setdefault(int(G.bits(np.array([block(h,s,k)],dtype=np.float32))[0]),[]).append((s,h,k))
off={}
for line in open('zdump.txt'):
  m=re.search(r's=(\d) type=1 g=0 hh=(\d) k=(\d+) any=1 data=([0-9a-f]+)',line);s,h,k,d=int(m[1]),int(m[2]),int(m[3]),int(m[4],16)
  r=refmap.get(d)
  key=(k, tuple(r) if r else None)
  if s==0 and h==0: print('dut s0h0 k',k,'->',r)
