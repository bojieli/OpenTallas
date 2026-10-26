import json,gzip,re,collections,sys
sys.path.insert(0,'/home/ubuntu/wt/kv-p3-1023/physical/die_plan/qwen_kvsys')
import extract_asbuilt as X
D='/home/ubuntu/scratch/kv-p2-1023/case_kv/'
bc=json.load(gzip.open('/home/ubuntu/scratch/kv-p2-1023/bitcon.json.gz'))
B=bc['blocks']
need=collections.defaultdict(set)
for i,p,idx in bc['leaf_inputs_undriven']: need[i].add(p)
masters=json.load(open(D+'gen_source_ports.json'))['masters']
wires={}; assign={}; bind={}
ASG=re.compile(r"\s*assign\s+(\S+?)(?:\[(\d+)\])?\s*=\s*1'b([01]);")
for ln in open(D+'die.v'):
    m=X.WIRE_RE.match(ln)
    if m:
        wires[m.group(4)]=(int(m.group(2)),int(m.group(3))) if m.group(1) else (0,0); continue
    m=ASG.match(ln)
    if m:
        assign[(m.group(1), int(m.group(2)) if m.group(2) else 0)]=int(m.group(3)); continue
    m=X.INST_RE.match(ln)
    if not m or m.group(1) in ('assign','wire','module'): continue
    mst,name,body=m.groups()
    if name not in need: continue
    for p,e in X.split_ports(body):
        if p in need[name]: bind[(name,p)]=e
print(len(assign),'const assigns', len(bind), file=sys.stderr)
out=collections.defaultdict(dict)
for (name,p),e in bind.items():
    w=len(masters[B[name]]['ports'][p])
    # expr bits MSB first; resolve names
    bits=[]
    for part in reversed(re.split(r',\s*', e.strip().strip('{}'))):   # LSB-first parts
        part=part.strip()
        mm=re.match(r"(\w+)(?:\[(\d+)(?::(\d+))?\])?$",part)
        if not mm: bits.append(('?',part)); continue
        n=mm.group(1)
        if mm.group(2) is None:
            hi,lo=wires.get(n,(0,0))
        else:
            hi=int(mm.group(2)); lo=int(mm.group(3)) if mm.group(3) else hi
        for k in range(lo,hi+1): bits.append(assign.get((n,k),'X'))
    v=''.join(str(b) for b in reversed(bits[:w]))
    out[B[name]+'.'+p][name]=v
json.dump(out,open('strap_values.json','w'),indent=0)
for k,v in sorted(out.items()):
    vals=collections.Counter(v.values())
    print(k, len(v), 'distinct', len(vals), dict(list(vals.most_common(6))))
