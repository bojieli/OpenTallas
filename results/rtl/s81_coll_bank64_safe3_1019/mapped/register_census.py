# every register / combinational driver in the mapped safe3 netlist: loads counted transparently through BUF/INV
# (a buffer tree is not a copy); reports every driver > 32 loads, split into reset-leaf, register and combinational.
import re,glob,collections,json,sys
net=glob.glob('map_safe3/work/orfs/results/asap7/*/base/1_2_yosys.v')[0]
t=open(net).read()
cells=[]
for m in re.finditer(r'\n\s*([A-Za-z0-9_]+)\s+(\\?\S+)\s*\((.*?)\);',t,re.S):
    pins=dict((p,n.strip()) for p,n in re.findall(r'\.(\w+)\(([^()]*)\)',m.group(3)))
    cells.append((m.group(1),m.group(2),pins))
byname={c[1]:c for c in cells}
OUT=('Y','QN','Q','CON','SN')
loads=collections.defaultdict(list)
for typ,name,pins in cells:
    for p,n in pins.items():
        if p not in OUT: loads[n].append((name,p))
def tl(n,depth=0):
    r=[]
    for ln,p in loads[n]:
        c=byname[ln]
        if c[0].startswith(('BUF','INV')) and depth<20: r+=tl(c[2]['Y'],depth+1)
        else: r.append((ln,p))
    return r
rows=[]
for typ,name,pins in cells:
    if typ.startswith(('BUF','INV','TIE')): continue
    for p,n in pins.items():
        if p in OUT and n not in ("1'h0","1'h1"):
            L=tl(n)
            if len(L)>32:
                kind='reset' if any(pp in ('RESETN','SETN','RN','SN') for _,pp in L) and typ.startswith('DFF') else ('register' if typ.startswith('DFF') else 'combinational')
                rows.append({'driver':name,'type':typ,'pin':p,'loads':len(L),'kind':kind,
                             'sample':sorted(set(re.sub(r'\[\d+\]','[]',x) for x,_ in L))[:6]})
rows.sort(key=lambda r:-r['loads'])
flops=sum(1 for c in cells if c[0].startswith('DFF'))
res={'netlist':net,'cells':len(cells),'flops':flops,'over32':rows,
     'max_loads_by_kind':{k:max([r['loads'] for r in rows if r['kind']==k] or [0]) for k in ('reset','register','combinational')}}
json.dump(res,open('map_safe3/register_census.json','w'),indent=1)
print('REGISTER_CENSUS cells',len(cells),'flops',flops,'over32',len(rows),res['max_loads_by_kind'])
for r in rows[:40]: print(' ',r['loads'],r['kind'],r['type'],r['driver'],r['sample'][:3])
