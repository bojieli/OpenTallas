import json,re,collections,sys,gzip
sys.path.insert(0,'/home/ubuntu/wt/kv-p3-1023/physical/die_plan/qwen_kvsys')
import extract_asbuilt as X
D='/home/ubuntu/scratch/kv-p2-1023/case_kv/'
masters=json.load(open(D+'gen_source_ports.json'))['masters']
wires={}; drv={}; rly={}
lines=open(D+'die.v').read().splitlines()
for ln in lines:
    m=X.WIRE_RE.match(ln)
    if m: wires[m.group(4)]=(int(m.group(2)),int(m.group(3))) if m.group(1) else (0,0)
insts={}
for ln in lines:
    m=X.INST_RE.match(ln)
    if not m or m.group(1) in ('assign','wire','module'): continue
    mst,name,body=m.groups()
    pdef=masters[mst]['ports']
    ports=dict(X.split_ports(body))
    insts[name]=mst
    for p,e in ports.items():
        bits=X.expr_bits(e,wires); w=len(pdef[p])
        if mst=='qkd_rlyi_258s':
            rly.setdefault(name,{})[p]=bits
        for k,nb in enumerate(bits):
            if pdef[p][w-1-k]=='OUTPUT' and nb is not None: drv[nb]=(name,p)
cmap=json.load(open('/home/ubuntu/wt/kv-p3-1023/physical/die_plan/qwen_kvsys/census/census_map_v31.json'))['parts']
out={}
for n,ps in sorted(rly.items()):
    ydrv=collections.Counter(drv.get(b,('?','?'))[0] for b in ps['y'][2:])
    adrv=collections.Counter(drv.get(b,('?','?'))[0] for b in ps['a'][2:])
    sdrv=drv.get(ps['s'][0],('?','?'))
    yd=ydrv.most_common(1)[0][0]
    out[n]=dict(y_src=yd, y_part=cmap.get(yd), a_src=adrv.most_common(1)[0][0], s_src=sdrv[0], s_part=cmap.get(sdrv[0]),
                b_sinks=None)
# sinks of b
sinkof=collections.defaultdict(set)
for ln in lines:
    m=X.INST_RE.match(ln)
    if not m or m.group(1) in ('assign','wire','module'): continue
    mst,name,body=m.groups(); pdef=masters[mst]['ports']
    for p,e in X.split_ports(body):
        bits=X.expr_bits(e,wires); w=len(pdef[p])
        for k,nb in enumerate(bits):
            if pdef[p][w-1-k]!='OUTPUT' and nb is not None and nb in drv and drv[nb][0] in rly: sinkof[drv[nb][0]].add((name,p))
for n in out: out[n]['b_sinks']=sorted(sinkof[n])
json.dump(out,open('relays_rtl6.json','w'),indent=0)
c=collections.Counter((v['y_part'],v['s_part']) for v in out.values()); print(c.most_common(40))
print(collections.Counter(insts[s[0]] for v in out.values() for s in v['b_sinks']))
for n in list(out)[:6]: print(n,out[n])
