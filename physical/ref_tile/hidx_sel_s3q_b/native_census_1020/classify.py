# classify census violations: trace each violating driver back to its nearest named flop/port inputs (light; netlist text)
import json,re,sys,collections
rep=json.load(open(sys.argv[1])); nl=open(sys.argv[2]).read()
inst={}
for m in re.finditer(r'^\s+(\S+)\s+(\\?\S+)\s*\((.*?)\);',nl,re.M|re.S):
    cell,name,body=m.groups()
    pins=dict((p,n.strip()) for p,n in re.findall(r'\.(\w+)\(([^()]*)\)',body))
    inst[name]=(cell,pins)
drv={}
for n,(c,p) in inst.items():
    for pin,net in p.items():
        if pin in ('Y','Q','QN','CON','SN','Z') : drv[net]=n
def origin(net,depth=0,seen=None):
    seen=seen or set()
    if net in seen or depth>6: return set()
    seen.add(net); i=drv.get(net)
    if i is None: return {net}
    c,p=inst[i]
    if 'DFF' in c or 'SDF' in c or 'ASYNC' in c: return {i}
    out=set()
    for pin,n in p.items():
        if pin not in ('Y','Q','QN','CON','SN'): out|=origin(n,depth+1,seen)
    return out
cnt=collections.Counter(); ex={}
for v in rep['violations']:
    d=v['driver'].rsplit('/',1)[0]
    c,p=inst.get(d,('?',{}))
    if 'DFF' in c: o={d}
    else:
        o=set()
        for pin,n in p.items():
            if pin not in ('Y','Q','QN','CON','SN'): o|=origin(n)
    key=' + '.join(sorted(set(re.sub(r'\[\d+\]','[]',re.sub(r'\$_.*','',x)) for x in o)))[:240]
    cnt[key]+=1; ex[key]=max(ex.get(key,0),v['loads'])
for k,n in cnt.most_common(60): print(n,'max',ex[k],'|',k)
print('--- empty-origin examples')
k=0
for v in rep['violations']:
    d=v['driver'].rsplit('/',1)[0]; c,p=inst.get(d,('?',{}))
    if d not in inst or not any(True for _ in [1]):
        pass
    o=set()
    if 'DFF' in c: continue
    for pin,n in p.items():
        if pin not in ('Y','Q','QN','CON','SN'): o|=origin(n)
    if not o:
        print(v['driver'],c,v['loads'],v['driver_role'],str(p)[:200]); k+=1
        if k>12: break
