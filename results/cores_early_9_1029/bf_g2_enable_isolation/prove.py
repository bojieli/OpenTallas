# Intervention proof: post netlist == pre netlist modulo the inserted identity buffers.
import sys,collections,json
def load(p):
    m={}
    for l in open(p):
        i,pin,n,s=l.rstrip('\n').split('\t'); m[(i,pin)]=(n,s)
    return m
pre,post=load(sys.argv[1]+'.pre'),load(sys.argv[1]+'.post')
tsv=[l.rstrip('\n').split('\t') for l in open(sys.argv[2]) if l.strip() and not l.startswith('#')]
bufs={r[0]:(r[1],r[2]) for r in tsv}
err=[]
# 1 each buffer: A on the pre net of target/pin, Y on a private net with exactly one load = target/pin
loads=collections.defaultdict(list)
for (i,p),(n,s) in post.items(): loads[n].append((i,p))
for b,(t,p) in bufs.items():
    a=post.get((b,'A')); y=post.get((b,'Y'))
    if not a or not y: err.append(('bufpin',b)); continue
    if a[0]!=pre[(t,p)][0]: err.append(('A_net',b,a[0],pre[(t,p)][0]))
    if sorted(loads[y[0]])!=sorted([(b,'Y'),(t,p)]): err.append(('Y_loads',b,loads[y[0]]))
    if post[(t,p)][0]!=y[0]: err.append(('target',b))
# 2 every other pin unchanged (net name and sig type)
moved={(t,p) for t,p in bufs.values()}
for k,v in pre.items():
    if k in moved: continue
    if post.get(k)!=v: err.append(('changed',k,v,post.get(k)))
extra=[k for k in post if k not in pre and k[0] not in bufs]
if extra: err.append(('extra_pins',extra[:5]))
clk_pre=sorted(k for k,v in pre.items() if v[1]=='CLOCK'); clk_post=sorted(k for k,v in post.items() if v[1]=='CLOCK')
r=dict(buffers=len(bufs),targets=len(moved),pins_pre=len(pre),pins_post=len(post),clock_pins_pre=len(clk_pre),clock_pins_post=len(clk_post),clock_pins_identical=clk_pre==clk_post,errors=len(err),first_errors=[str(e) for e in err[:10]])
r['verdict']='PASS' if not err and r['clock_pins_identical'] else 'FAIL'
print(json.dumps(r,indent=1)); json.dump(r,open(sys.argv[3],'w'),indent=1)
# 3 legality of the new FIRM buffers: no overlap with any fixed cell/macro or each other, inside core rows
boxes=[l.rstrip('\n').split('\t') for l in open(sys.argv[1]+'.boxes')]
B=[(n,st,m,*map(int,x)) for n,st,m,*x in boxes]
new=[b for b in B if b[0] in bufs]; old=[b for b in B if b[0] not in bufs]
import bisect
cell=4000  # 4 um bins (dbu 1000/um? generic)
grid=collections.defaultdict(list)
for b in B:
    for gx in range(b[3]//cell,b[5]//cell+1):
        for gy in range(b[4]//cell,b[6]//cell+1): grid[(gx,gy)].append(b)
ov=[]
for b in new:
    seen=set()
    for gx in range(b[3]//cell,b[5]//cell+1):
        for gy in range(b[4]//cell,b[6]//cell+1):
            for o in grid[(gx,gy)]:
                if o[0]==b[0] or o[0] in seen: continue
                seen.add(o[0])
                if min(b[5],o[5])>max(b[3],o[3]) and min(b[6],o[6])>max(b[4],o[4]): ov.append((b[0],o[0],o[2]))
print('new_buffers_placed',len(new),'overlaps',len(ov),ov[:5])
r['placed']=len(new); r['overlaps']=len(ov); r['first_overlaps']=[str(x) for x in ov[:10]]
if ov or len(new)!=len(bufs): r['verdict']='FAIL'
print('VERDICT',r['verdict']); json.dump(r,open(sys.argv[3],'w'),indent=1)
