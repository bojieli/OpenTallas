import re,collections,math,json,sys
Q=[];N=[]
for line in open('cf_trace.tsv'):
    p=line.rstrip('\n').split('\t')
    if p[0]=='Q': Q.append(p[:4]+['\t'.join(p[4:])])
    elif p[0]=='N': N.append(p[:3]+[p[3]+'\t'+p[4], '\t'.join(p[5:])])
def sinks(s):
    out=[]
    for x in s.split(' ;; '):
        if not x: continue
        a=x.split('|'); xs=a[2].split('\t'); out.append((a[0],a[1],float(xs[0]),float(xs[1])))
    return out
def mst(pts):
    pts=list(set(pts))
    if len(pts)<2: return 0.0
    inT=[pts[0]]; rest=pts[1:]; L=0
    d={q:abs(q[0]-pts[0][0])+abs(q[1]-pts[0][1]) for q in rest}
    while d:
        q=min(d,key=d.get); L+=d.pop(q)
        for r in d: d[r]=min(d[r],abs(r[0]-q[0])+abs(r[1]-q[1]))
    return L
print('Q',len(Q),'N',len(N))
lane_rx=re.compile(r'u_u_vp_g_ln_(\d+)_u_l')
before_q=[];lanes_of_word={}
for p in Q:
    nm=p[1]; fx,fy=float(p[2]),float(p[3]); S=sinks(p[4]) if len(p)>4 else []
    pts=[(fx,fy)]+[(s[2],s[3]) for s in S]
    xs=[q[0] for q in pts]; ys=[q[1] for q in pts]
    lanes=sorted(set(int(m.group(1)) for s in S for m in [lane_rx.search(s[0])] if m))
    w=re.search(r'native_memory\\\\\[(\d+)\\\\\]\\\\\[(\d+)\\\\\]',nm) or re.search(r'native_memory.*?(\d+).*?(\d+)',nm)
    lanes_of_word[nm]=lanes
    lp=[(s[2],s[3]) for s in S if lane_rx.search(s[0])]
    before_q.append(dict(flop=nm,fanout=len(S),lanes=lanes,spread=max(xs)-min(xs)+max(ys)-min(ys),mst=mst(pts),lane_pts=lp))
print('word bits',len(before_q),'lanes per bit',collections.Counter(len(b['lanes']) for b in before_q))
print('before Q nets: spread>100:',sum(b['spread']>100 for b in before_q),' total MST um %.0f'%sum(b['mst'] for b in before_q),' mean spread %.0f'%(sum(b['spread'] for b in before_q)/len(before_q)))
# D side: data nets (q1r) = nets feeding the AO21 enable muxes whose source is NOT another cf flop feedback, and with sinks >1
dn=[p for p in N if p[1] not in ('VDD','VSS')]
data=[]
for p in dn:
    S=sinks(p[4]) if len(p)>4 else []
    src=p[3].split('|'); sx,sy=[float(v) for v in src[2].split('\t')]
    pts=[(sx,sy)]+[(s[2],s[3]) for s in S]
    xs=[q[0] for q in pts]; ys=[q[1] for q in pts]
    data.append(dict(net=p[1],pin=p[2],src=src[0],n=len(S),spread=max(xs)-min(xs)+max(ys)-min(ys),mst=mst(pts),srcxy=(sx,sy)))
big=[d for d in data if d['n']>2]
print('D-side input nets',len(data),' with >2 sinks',len(big),' spread>100:',sum(d['spread']>100 for d in data),' MST %.0f'%sum(d['mst'] for d in data))
# AFTER estimate: each lane gets its copy at its lane-pin centroid; word nets local (MST lane pins of that word bit within lane + copy) ;
# D side: each multi-sink D-side net (data q1r bits, enables) now must reach the copies of the lanes it serves.
lane_c=collections.defaultdict(list)
for b in before_q:
    for (x,y),l in zip(b['lane_pts'],[]): pass
# lane pin centroid per lane from Q sinks
for p in Q:
    for s in sinks(p[4]) if len(p)>4 else []:
        m=lane_rx.search(s[0])
        if m: lane_c[int(m.group(1))].append((s[2],s[3]))
cent={l:(sum(x for x,_ in v)/len(v),sum(y for _,y in v)/len(v)) for l,v in lane_c.items()}
print('lane pin centroids',{l:(round(c[0]),round(c[1])) for l,c in sorted(cent.items())})
after_q=0.0
for b in before_q:
    # per lane: copy flop at centroid of that lane's pins, net = copy -> that lane's pins (the bit's pin on that lane)
    for (x,y) in b['lane_pts']:
        l=min(cent,key=lambda k: abs(cent[k][0]-x)+abs(cent[k][1]-y))
        after_q+=abs(cent[l][0]-x)+abs(cent[l][1]-y)
# D side after: data/enable nets whose sinks are cf muxes: sinks move to the lanes served by those flops
# map mux -> flop -> lanes ; approximate per D-side net: the lanes = union of lanes of all cf flops this net feeds
mux2flop={}
for p in N: pass
srcs=[d['srcxy'] for d in big]
sx=sum(x for x,_ in srcs)/len(srcs); sy=sum(y for _,y in srcs)/len(srcs)
print('D-side multi-sink nets: sinks histogram',collections.Counter(d['n'] for d in big).most_common(6),' source centroid (%.0f,%.0f)'%(sx,sy))
after_d=0; nets_after=0
for K in range(4):
    pts=[cent[l] for l in range(4*K,4*K+4)]
    # 32 data bits of K at their measured source, 5 word enables of K
    for d in big:
        pass
    m=mst([(sx,sy)]+pts)
    after_d+=37*m; nets_after+=37
print('AFTER estimate: word nets local %.0f um (copy at lane pin centroid); D side %d nets (32 data + 5 enables per K) MST %.0f um'%(after_q,nets_after,after_d))
print('BEFORE: %d word nets MST %.0f + %d D-side nets MST %.0f = %.0f um; nets >100um spread: %d'%(len(before_q),sum(b['mst'] for b in before_q),len(big),sum(d['mst'] for d in big),sum(b['mst'] for b in before_q)+sum(d['mst'] for d in big),640+len(big)))
print('AFTER : %.0f um; nets >100um: %d'%(after_q+after_d,nets_after))
kspan={K:round(mst([cent[l] for l in range(4*K,4*K+4)])) for K in range(4)}
print('K-group lane MST',kspan)
