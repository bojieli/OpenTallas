# XT1 tile (0,0) face trace analysis: ib fields at the tile, x window vs the op's x, t_out vs tile-level gold
import json, sys, numpy as np
W=sys.argv[1]; LOG=sys.argv[2]
sys.path.insert(0, W+'/src/rtl/test/qwen_dv/xhead'); import ibdec as I
g=json.load(open(W+'/prep/gold.json')); sch=json.load(open(LOG.replace('log_','ev_')+'.sched.json'))
ev=[]
for ln in open(LOG):
    p=ln.split()
    if len(p)>=3 and p[1] in ('TGO','TX','TOUT','RS'): ev.append((int(p[0]),p[1],p[-1]))
def f32(u): return np.array(u,dtype=np.uint32).view(np.float32)
def w2f(h,n=16):
    h=h.rjust(8*n,'0'); return f32([int(h[8*n-8*(q+1):8*n-8*q],16) for q in range(n)])
def bf16(x):
    u=np.asarray(x,dtype=np.float32).view(np.uint32).astype(np.uint64); r=((u>>16)&1)+0x7fff; return (((u+r)>>16)<<16).astype(np.uint32).view(np.float32)
fx='/srv/opentallas-scratch/claude/qw-realstg/fx'
for name in ('qkv','o','gu','down'):
    if name in ('qkv','gu'): z=np.load(f'{fx}/L0_mat_{name}.npz'); w=z['w']; x=z['x']
    else: z=np.load(f'{fx}/L0_mat_od.npz'); w=z[name+'_w']; x=z[name+'_x']
    xb=bf16(x); op=g[name]['op']; S=1<<op['split']; kc=op['k']; nblk=3072//S
    go=sch[name]['go']; lo,hi=go-40,go+1400
    tg=[(c,h) for c,t,h in ev if t=='TGO' and lo<=c<hi]
    tx=[(c,w2f(h,4)) for c,t,h in ev if t=='TX' and lo<=c<hi]
    to=[(c,w2f(h)) for c,t,h in ev if t=='TOUT' and lo<=c<hi]
    print(f'== {name} S {S} kc {kc} hr go {go}: TGO {len(tg)} TX {len(tx)} TOUT {len(to)}')
    for c,h in tg[:2]:
        f=I.dec_ib(int(h,16)); print('  TGO', c-go, {k:f[k] for k in ('nout','tiles','k','wbase','ts','ks','js','xbase','xks','xjs','xcs','split','round','jsh','mmode')})
    # expected x per group 64..67 per k: element xbase + c*xcs + k*xks (c = g mod S); fixture x index = element - xbase
    exp_x=np.array([[xb[(gg%S)*op['xcs']+k*op['xks']] for gg in range(64,68)] for k in range(kc)])
    for c,v in tx[:min(len(tx),kc+2)]:
        hit=[k for k in range(kc) if np.array_equal(v,exp_x[k])]
        print('  TX', c-go, v, 'matches k', hit)
    # tile-level gold: per (r,j) lane accumulate over k in order, then pairwise tree over 4 groups
    gold=[]
    for r in range(op['tiles']):
        for j in range(8):
            parts=[]
            for gg in range(64,68):
                row0=128*(r*nblk+gg//S)+16*j; acc=np.zeros(16,dtype=np.float32)
                for k in range(kc):
                    col=kc*(gg%S)+k
                    acc=(acc+np.float32(w[row0:row0+16,col]).astype(np.float32)*np.float32(xb[col])).astype(np.float32)
                parts.append(acc)
            gold.append(((parts[0]+parts[1])+(parts[2]+parts[3])).astype(np.float32))
    ok=sum(1 for i,(c,v) in enumerate(to) if i<len(gold) and np.array_equal(v,gold[i]))
    print(f'  TOUT exact {ok}/{len(gold)} (got {len(to)})')
    for i,(c,v) in enumerate(to[:3]):
        print('  TOUT', c-go, v[:4], 'gold', gold[i][:4] if i<len(gold) else None)
