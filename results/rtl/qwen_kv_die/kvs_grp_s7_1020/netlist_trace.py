import re,sys,collections,json
src=open(sys.argv[1]).read()
top=sys.argv[2]
import os
OUTDIR=os.environ.get('OUTDIR','/home/ubuntu/scratch/kv-grp7')
mods={}
for m in re.finditer(r'^module (\S+)\s*\((.*?)\);(.*?)^endmodule',src,re.S|re.M):
    outs=set()
    for d in re.finditer(r'output\s+(?:wire\s+|reg\s+)?(?:\[[^\]]+\]\s*)?([^;]+);',m.group(3)):
        for n in d.group(1).split(','): outs.add(n.strip())
    mods[m.group(1)]=(outs,m.group(3))
body=mods[top][1]
# expand net expr list
def nets(e):
    e=e.strip()
    if e.startswith('{'): e=e[1:-1]
    return [x.strip() for x in e.split(',') if x.strip()]
inst={}
PRIM={'Y','Q','QN','CON','SN','H','L'}
for m in re.finditer(r'^\s*(?:\(\* keep \*\)\s*)?(\S+)\s+(\S+)\s*\((\..*?)\);\s*$',body,re.M):
    typ,name,conns=m.groups()
    pins={}
    for c in re.finditer(r'\.(\w+)\(([^()]*)\)',conns): pins[c.group(1)]=nets(c.group(2))
    inst[name]=(typ,pins)
# assigns
alias={}
for m in re.finditer(r'assign\s+(\S+)\s*=\s*(\S+?)\s*;',body): alias[m.group(1)]=m.group(2)
drv={}; loads=collections.defaultdict(list)
for n,(t,p) in inst.items():
    outs=mods[t][0] if t in mods else PRIM
    for pin,ns in p.items():
        for k,x in enumerate(ns):
            if pin in outs: drv[x]=(n,pin,k)
            else: loads[x].append((n,pin,k))
for a,b in alias.items(): drv.setdefault(a,('ASSIGN',b,0))
json.dump({'types':{n:t for n,(t,p) in inst.items()}},open('/home/ubuntu/scratch/kv-grp7/types.json','w'))
macro_types={t for n,(t,p) in inst.items() if 'rd_out' in p}
print('macro types',{t:sum(1 for n,(tt,p) in inst.items() if tt==t) for t in macro_types})
def back(net,limit=200000):
    # return set of macro instances and input ports reached backward
    seen=set();st=[net];hitm=set();hitp=set()
    while st:
        x=st.pop()
        if x in seen: continue
        seen.add(x)
        if x not in drv:
            hitp.add(re.sub(r'\[\d+\]$','',x)); continue
        n,pin,k=drv[x]
        if n=='ASSIGN': st.append(pin); continue
        t,p=inst[n]
        if t in macro_types: hitm.add(n); continue
        for q,ns in p.items():
            if q not in (mods[t][0] if t in mods else PRIM): st.extend(ns)
    return hitm,hitp
res={}
mode=sys.argv[3]
if mode=='out':
    for port in sys.argv[4:]:
        for i in range(int(port.split(':')[1])):
            nm=f"{port.split(':')[0]}[{i}]"
            hm,hp=back(alias.get(nm,nm))
            res[nm]=sorted(hm)
if mode=='macro_in':
    for n,(t,p) in inst.items():
        if t in macro_types:
            ins=p['wd_in']
            agg=collections.Counter(); aggp=collections.Counter()
            for x in ins[:8]:
                hm,hp=back(x); agg.update(hm); aggp.update(hp)
            res[n]={'type':t,'from_macros':dict(agg),'from_ports':dict(aggp)}
json.dump(res,open(sys.argv[-1] if mode=='x' else f''+OUTDIR+f'/trace_{mode}.json','w'),indent=0)
print(len(res))
