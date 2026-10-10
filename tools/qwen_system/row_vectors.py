"""Independent golden row grant/packet vectors from actual option-M placement."""
import argparse,random
from collections import defaultdict,deque
from qwen_kv_landing_fabric import placement_m

def pack(values,width):
    return sum(v<<(i*width) for i,v in enumerate(values))

def vectors(path,count=2048):
    pos=placement_m();r=random.Random(711932);credits=[8]*32;returns=defaultdict(deque)
    pool=[t for t,(c,y) in pos.items() if c<32 and y<12]
    target=[t for t in pool if pos[t][1]==0]
    with open(path,'w') as f:
      for cy in range(count):
        rr=r.randrange(128);heads=[]
        for p in range(32):
          isk=r.randrange(2);v=r.random()<.8
          if isk:
            t0=r.choice(target if r.random()<.8 else pool);t1=0;need=1
          else:
            t0=r.randrange(128);t1=t0+128;need=r.choice([1,2,3])
          heads.append(dict(v=int(v),need=need,data=r.getrandbits(256),t0=t0,t1=t1,
            a0=r.randrange(7),a1=r.randrange(7),s0=r.randrange(2)*2 if isk else r.randrange(4),
            s1=r.randrange(4),isk=isk,tail=isk and r.randrange(2),lanes=r.randrange(16)))
        if cy==0:
          rr=0;heads=[dict(v=0,need=0,data=0,t0=0,t1=0,a0=0,a1=0,s0=0,s1=0,isk=0,tail=0,lanes=0) for _ in range(32)]
          heads[0].update(v=1,need=3,data=r.getrandbits(256),t1=128)
        cr=0
        for col in range(32):
          if returns[col] and returns[col][0]<=cy and cy%7!=0:
            returns[col].popleft();cr|=1<<col
        candidates=[]
        for p in sorted(range(32),key=lambda p:(p-rr)%128):
          h=heads[p]
          for half in range(2):
            if not h['v'] or not(h['need']>>half&1):continue
            col,row=pos[h['t'+str(half)]]
            if row!=0:continue
            sel=h['s'+str(half)];q=0 if h['isk'] and h['tail'] and h['lanes']==0 else (3 if h['isk'] else 1)<<sel
            candidates.append((p,half,col,h['a'+str(half)],q))
        # Golden merge first word per tile, and all earlier VALID quarters.
        first={};seen=defaultdict(int);eligible=[]
        for p,half,col,loc,q in candidates:
          first.setdefault(col,loc)
          if first[col]!=loc:continue
          if not(seen[col]&q) and credits[col]>0:eligible.append((p,half,col,loc))
          seen[col]|=q
        chosen=eligible[:3];grant=0;out=0;reserved=set()
        for slot,(p,half,col,loc) in enumerate(chosen):
          h=heads[p];grant|=1<<(2*p+half);reserved.add(col)
          data=h['data'] if h['isk'] else (h['data']>>(half*128))&((1<<128)-1)
          packet=data|(h['lanes']<<256)|(h['s'+str(half)]<<260)|(int(h['tail'])<<262)|(h['isk']<<263)|(loc<<264)|(p<<271)|(col<<276)
          out|=packet<<(281*slot)
        for col in range(32):
          credits[col]+=(cr>>col&1)-int(col in reserved)
          assert 0<=credits[col]<=8
          if col in reserved:returns[col].append(cy+80+col)
        fields=[rr,pack([h['v'] for h in heads],1),pack([h['need'] for h in heads],2),pack([h['data'] for h in heads],256)]
        fields += [pack([h[k] for h in heads],w) for k,w in [('t0',11),('t1',11),('a0',7),('a1',7),('s0',2),('s1',2),('isk',1),('tail',1),('lanes',4)]]
        fields +=[cr,grant,(1<<len(chosen))-1,out]
        f.write(' '.join(format(v,'x') for v in fields)+'\n')
    print(f'VECTORS full32-PC cycles{count}, independent option-M map, rotating grants, per-tile merged-word credits')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',required=True);a.add_argument('--count',type=int,default=2048);x=a.parse_args();vectors(x.out,x.count)
