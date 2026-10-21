#!/usr/bin/env python3
"""Repack identical combinational replicas by actual completed-placement sink zones.

No registers, clock connections or protocol edges change. Added identical copies are
allowed only while every input's conservative transparent-inverter load stays <=32.
Unlocated groups stay explicitly unchanged. Native mapped admission remains required.
"""
import re,sys,json,collections,hashlib,csv
src,dst,rec,placement=sys.argv[1:5]
text=open(src).read();lines=text.split('\n')
cell_re=re.compile(r'^(\(\* [^*]*\*\) )?(qfd_bmath_\w+) #\(\.ID\(0\)\) (\\\S+ |[^\s(]+)\((.*)\);$')
pin_re=re.compile(r'\.(\w+)\(([^()]*)\)')
cells={};other_nets=collections.Counter()
for i,l in enumerate(lines):
    m=cell_re.match(l)
    if m: cells[m.group(3).strip()]=(m.group(2),dict(pin_re.findall(m.group(4))),i)
    elif not l.startswith('wire ') :
        for t in re.findall(r'\bn_\d+\b',l): other_nets[t]+=1
def outs(t): return ('Q',) if t.startswith('qfd_bmath_dff') else ('Y',)
sinks=collections.defaultdict(list)
for n,(t,pins,i) in cells.items():
    for p,net in pins.items():
        if p not in outs(t): sinks[net].append((n,p))
_nw={}
def netw(net):
    # mapped dynamic loads of a net: inverters are transparent (absorbed by mapping), MUX S = 2, other pins 1
    if net in _nw: return _nw[net]
    _nw[net]=0
    _nw[net]=sum(w(s,p) for s,p in sinks.get(net,[])) + other_nets[net]
    return _nw[net]
def w(s,p):
    t=cells[s][0]
    if t=='qfd_bmath_not': return max(1,netw(cells[s][1]['Y']))
    return 2 if (t=='qfd_bmath_mux' and p=='S') else 1
def ismux(s,p): return cells[s][0]=='qfd_bmath_mux' and p=='S'
def num(s): m=re.search(r'(\d+)$',s.strip('\\ ')); return int(m.group(1)) if m else 0
# Exact completed safe12c placed coordinates, not a mux-role geography guess.
xyz=collections.defaultdict(list)
for row in csv.DictReader(open(placement),delimiter='\t'):
    root=re.split(r'[/.$]',row['name'],maxsplit=1)[0]
    xyz[root].append((float(row['x_um']),float(row['y_um'])))
xy={n:(sum(p[0] for p in pts)/len(pts),sum(p[1] for p in pts)/len(pts)) for n,pts in xyz.items()}
point_cache={}
def points(s,trail=()):
    if s in point_cache:return point_cache[s]
    if s in xy:return [xy[s]]
    if s in trail:return []
    t,pins,_=cells[s]
    if t!='qfd_bmath_not':return []
    out=[p for k,q in sinks.get(pins['Y'],[]) for p in points(k,trail+(s,))]
    point_cache[s]=out
    return out
def bucket(s,p):
    pts=points(s)
    if not pts:return 'UNKNOWN'
    x=sum(x for x,y in pts)/len(pts);y=sum(y for x,y in pts)/len(pts)
    return ('W0' if y<410.4 else 'W1') if x<453.6 else ('E0' if y<475.2 else 'E1')
def location(sp):
    ps=points(sp[0]);return (sum(x for x,y in ps)/len(ps),sum(y for x,y in ps)/len(ps)) if ps else (0,0)
grp=collections.defaultdict(list)
for n,(t,pins,i) in cells.items():
    if t.startswith('qfd_bmath_dff') or t=='qfd_bmath_not': continue  # NOT copies are transparent: re-dealing them moves weight upstream
    grp[(t,tuple(sorted((p,v) for p,v in pins.items() if p!='Y')))].append(n)
edits={}  # (sink,pin) -> newnet
extra=collections.Counter()
drv={pins['Y']:n for n,(t,pins,i) in cells.items() if 'Y' in pins}
added=[]
stats=collections.Counter();changed=[]
for k,ms in grp.items():
    if len(ms)<2: continue
    nets=[cells[m][1]['Y'] for m in ms]
    if any(other_nets[x] for x in nets): stats['skip_external']+=1; continue
    pool=[(s,p) for x in nets for (s,p) in sinks.get(x,[])]
    roles=[set(bucket(s,p) for s,p in sinks.get(x,[])) for x in nets]
    if any('UNKNOWN' in r for r in roles):stats['unlocated_groups_preserved']+=1;continue
    if not any(len(r)>1 for r in roles): stats['already_coherent']+=1; continue
    cap=32
    order=sorted(pool,key=lambda sp:(bucket(*sp),location(sp)[1],location(sp)[0],num(sp[0]),sp[1]))
    ms_sorted=sorted(ms,key=num)  # original (lowest id) first: keeps the control loads
    def pack(allow_break):
        buckets=[[]];cost=0
        for sp in order:
            role_break=allow_break and buckets[-1] and bucket(*buckets[-1][-1])!=bucket(*sp)
            if buckets[-1] and (cost+w(*sp)>cap or role_break): buckets.append([]);cost=0
            buckets[-1].append(sp);cost+=w(*sp)
        return buckets
    buckets=pack(True)
    def can_add():
        # an extra copy loads each input net once more; inverters are transparent, so walk up NOT drivers too
        for q,v in cells[ms_sorted[0]][1].items():
            if q=='Y': continue
            net=v
            while True:
                if netw(net)+extra[net]+1>32: return False
                d=drv.get(net)
                if d is None or cells[d][0]!='qfd_bmath_not': break
                net=cells[d][1]['A']
        return True
    if len(buckets)>len(ms_sorted) and not can_add():
        buckets=pack(False); stats['packed_one_mixed_input_cap']+=1
        if len(buckets)>len(ms_sorted): stats['left_unchanged_input_cap']+=1; continue
    while len(buckets)>len(ms_sorted):
        for q,v in cells[ms_sorted[0]][1].items():
            if q=='Y': continue
            net=v
            while True:
                extra[net]+=1; d=drv.get(net)
                if d is None or cells[d][0]!='qfd_bmath_not': break
                net=cells[d][1]['A']   # role-coherent copies need one more identical copy
        base=ms_sorted[0];k2=len(added)
        nn=f'n_q13rr_{k2}';cn=f'u_qkorr_13_{k2}'
        t,pins,i=cells[base]
        added.append((i,lines[i].replace(' '+base+'(',' '+cn+'(',1).replace('.Y('+pins['Y']+')','.Y('+nn+')'),nn))
        cells[cn]=(t,dict(pins,Y=nn),None);ms_sorted.append(cn);stats['copies_added']+=1
    while len(buckets)<len(ms_sorted):
        j=max(range(len(buckets)),key=lambda j:(len(buckets[j]),bucket(*buckets[j][0])))
        if len(buckets[j])<2: break
        b=buckets[j];h=len(b)//2;buckets[j:j+1]=[b[:h],b[h:]]
    nets_sorted=[cells[m][1]['Y'] for m in ms_sorted]
    for b,net in zip(buckets,nets_sorted):
        for sp in b: edits[sp]=net
    for m in ms_sorted[len(buckets):]: stats['copy_left_unloaded']+=1
    if len(buckets)<len(ms_sorted): stats['no_fit_unload']+=0
    stats['groups_split']+=1;changed.append(dict(type=k[0],inputs=dict(k[1]),copies=ms_sorted,cap=cap,
        before=[dict(collections.Counter(bucket(s,p) for s,p in sinks.get(x,[]))) for x in nets_sorted],
        after=[dict(collections.Counter(bucket(*sp) for sp in b)) for b in buckets]))
# an unloaded copy would be removed by synthesis and change the census; refuse instead
if stats['copy_left_unloaded']: sys.exit(f"refuse: {stats['copy_left_unloaded']} copies would be left unloaded")
byline=collections.defaultdict(list)
for (s,p),net in edits.items(): byline[cells[s][2]].append((p,net))
moved=0
for i,lst in byline.items():
    l=lines[i]
    for p,net in lst:
        l2=re.sub(r'\.'+p+r'\(n_\d+\)','.'+p+'('+net+')',l,count=1)
        if l2!=l: moved+=1
        l=l2
    lines[i]=l
for i,l,nn in sorted(added,reverse=True):
    lines.insert(i+1,l)
hdr=next(j for j,l in enumerate(lines) if l.startswith('wire '))
if added: lines.insert(hdr,'wire '+', '.join(nn for _,_,nn in added)+';')
out='\n'.join(lines)
open(dst,'w').write(out)
r=dict(schema='opentallas.ctlm13.exact_placed_replica_regions.v1',placement=placement,placement_sha256=hashlib.sha256(open(placement,'rb').read()).hexdigest(),source=src,source_sha256=hashlib.sha256(text.encode()).hexdigest(),
       out_sha256=hashlib.sha256(out.encode()).hexdigest(),stats=dict(stats),sink_pins_moved=moved,groups=changed)
json.dump(r,open(rec,'w'),indent=1)
print(json.dumps(dict(stats=dict(stats),sink_pins_moved=moved)))
