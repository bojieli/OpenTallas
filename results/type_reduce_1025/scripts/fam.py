import json,sys,re,collections,itertools
P=json.load(open(sys.argv[1])); T=P['partition_types']
cnt=collections.Counter(p['type'] for p in P['partitions'])
def fam(k):
    k=re.sub(r'_(v\d+|r\d+|s2|b)$','',k); k=re.sub(r'_(v\d+|r\d+)$','',k)
    k=re.sub(r'^sl[we]_','sl_',k); k=re.sub(r'^cb[fnx]_q\d\d$','cb',k)
    k=re.sub(r'^kv3_hub_.*','kv3_hub',k); k=re.sub(r'^coll_ft.*','coll_ft',k); k=re.sub(r'^kv3_io_.*','kv3_io',k)
    return k
def iface(t): return sorted((b['name'],b['dir'],b['width'],b.get('kind'),b.get('leaf')) for b in t['buses'])
def ifw(t): return sorted((b['dir'],b['width'],b.get('kind')) for b in t['buses'])
def geom(t): return sorted((b['name'],b.get('face'),tuple(b.get('window_um') or []),tuple(b.get('layers') or [])) for b in t['buses'])
def fts(t): return sorted((s['width'],s.get('in_face'),s.get('out_face')) for s in t.get('ft_slots',[]))
def cont(t): return sorted((c['inst'],c['module']) for c in t['contents'])
def contm(t): return sorted(collections.Counter(c['module'] for c in t['contents']).items())
def par(t): return sorted((c['inst'],json.dumps(c.get('params'),sort_keys=True)) for c in t['contents'])
def hc(t): return sorted((h['inst'],h['module'],h.get('pins_file')) for h in t.get('hard_cores',[]))
F=collections.defaultdict(list)
for k in T: F[fam(k)].append(k)
for f,ks in F.items():
    if len(ks)<2: continue
    print(f'== {f}: {len(ks)} types, {sum(cnt[k] for k in ks)} inst')
    for k in ks:
        t=T[k]; print(f'  {k:16s} n={cnt[k]:2d} {t["outline_um"]} mod={t["module"]} nbus={len(t["buses"])} ft={len(t.get("ft_slots",[]))}/{sum(s["width"] for s in t.get("ft_slots",[]))}b cont={len(t["contents"])} hc={len(t.get("hard_cores",[]))}')
    for a,b in itertools.combinations(ks,2):
        A,B=T[a],T[b]; d=[]
        if A['outline_um']!=B['outline_um']: d.append('OUTLINE')
        if contm(A)!=contm(B): d.append('CONTMOD')
        elif cont(A)!=cont(B): d.append('contname')
        if par(A)!=par(B): d.append('PARAMS')
        if [x[1] for x in hc(A)]!=[x[1] for x in hc(B)]: d.append('HCMOD')
        elif hc(A)!=hc(B): d.append('hcpins')
        if ifw(A)!=ifw(B): d.append('IFACE')
        elif iface(A)!=iface(B): d.append('ifname')
        elif geom(A)!=geom(B): d.append('WINDOWS')
        if fts(A)!=fts(B): d.append('FT')
        print(f'    {a} ~ {b}: {",".join(d) or "SAME"}')
