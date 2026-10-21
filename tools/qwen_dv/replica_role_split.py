#!/usr/bin/env python3
"""QKO-CTLM 10-21: role-coherent fan-out replicas.  The native generator splits an overloaded driver into identical
copies (same cell type, same input nets) and fills them in sink order, so one copy can drive both a datapath mux-select
bank (placed by the SRAM columns, W) and control logic (E): every such copy costs a W<->E round trip inside one cycle
(safe10c CTS: u_6176 -> u_68475 x221 -> x549 -> u_39701 x229 -> u_6466, -829 ps).  This pass re-deals the pooled sinks
of every replica group: control (non mux-select) sinks first, then mux selects in instance order, each copy filled to the
group's original maximum weight (MUX S = 2, other pins 1).  Every sink pin still reads a net computed by an identical
cell from the identical input nets, so the function is unchanged; copies, cells and per-copy load weights never grow."""
import re,sys,json,collections,hashlib
src,dst,rec=sys.argv[1:4]
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
    roles=[set(ismux(s,p) for s,p in sinks.get(x,[])) for x in nets]
    if not any(r=={True,False} for r in roles): stats['already_coherent']+=1; continue
    cap=32
    order=sorted(pool,key=lambda sp:(ismux(*sp),num(sp[0]),sp[1]))
    ms_sorted=sorted(ms,key=num)  # original (lowest id) first: keeps the control loads
    def pack(allow_break):
        buckets=[[]];cost=0
        for sp in order:
            role_break=allow_break and buckets[-1] and ismux(*buckets[-1][-1])!=ismux(*sp) and len(buckets)<len(ms_sorted)
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
        nn=f'n_qkorr_{k2}';cn=f'u_qkorr_{k2}'
        t,pins,i=cells[base]
        added.append((i,lines[i].replace(' '+base+'(',' '+cn+'(',1).replace('.Y('+pins['Y']+')','.Y('+nn+')'),nn))
        cells[cn]=(t,dict(pins,Y=nn),None);ms_sorted.append(cn);stats['copies_added']+=1
    while len(buckets)<len(ms_sorted):
        j=max(range(len(buckets)),key=lambda j:(len(buckets[j]),ismux(*buckets[j][0])))
        if len(buckets[j])<2: break
        b=buckets[j];h=len(b)//2;buckets[j:j+1]=[b[:h],b[h:]]
    nets_sorted=[cells[m][1]['Y'] for m in ms_sorted]
    for b,net in zip(buckets,nets_sorted):
        for sp in b: edits[sp]=net
    for m in ms_sorted[len(buckets):]: stats['copy_left_unloaded']+=1
    if len(buckets)<len(ms_sorted): stats['no_fit_unload']+=0
    stats['groups_split']+=1;changed.append(dict(type=k[0],inputs=dict(k[1]),copies=ms_sorted,cap=cap,
        before=[dict(collections.Counter('mux' if ismux(s,p) else 'logic' for s,p in sinks.get(x,[]))) for x in nets_sorted],
        after=[dict(collections.Counter('mux' if ismux(*sp) else 'logic' for sp in b)) for b in buckets]))
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
r=dict(schema='opentallas.qko_ctlm.replica_role_split.v1',source=src,source_sha256=hashlib.sha256(text.encode()).hexdigest(),
       out_sha256=hashlib.sha256(out.encode()).hexdigest(),stats=dict(stats),sink_pins_moved=moved,groups=changed)
json.dump(r,open(rec,'w'),indent=1)
print(json.dumps(dict(stats=dict(stats),sink_pins_moved=moved)))
