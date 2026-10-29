"""HBM-BIND-2: neighbour census of unmapped cells: per group, bits to/from each mapped partition (non clk/rst nets)."""
import sys,json,re,collections
from pathlib import Path
w,plan,man,elab,out=sys.argv[1:6]
sys.path.insert(0,str(Path(w)/'tools'));sys.path.insert(0,str(Path(w)/'tools/die_plan'));import bind as B
a=json.loads(Path(man).read_text());p=json.loads(Path(plan).read_text());p['asbuilt']=a
b=B.Binder(p,json.loads(Path(elab).read_text()),Path(plan).parent,a['base']);b.map_cells();F=b.F
ctl=lambda pn: bool(re.fullmatch(r'(clk.*|clock.*|ck(_.*)?|rst.*|reset.*|arst.*|srst.*)',pn.lower()))
def grp(path):
    m=re.match(r'(hb_idx__s_\w+\.scorer\.ge\[\d+\]\.gc\[\d+\]\.leaf)(\.core\.g_col\[\d+\])?',path)
    if m: return m.group(1)+(m.group(2) or '')
    m=re.match(r'(hb_idx__s_\w+\.scorer\.ge\[\d+\]\.\w+)',path)
    if m and '$' not in m.group(1): return m.group(1)
    s=path.split('$')[0].rstrip('.')
    return s
drv=collections.defaultdict(list);lds=collections.defaultdict(list)
for i,c in enumerate(F.cells):
    for pn,bs in c.ports.items():
        if ctl(pn): continue
        t=drv if b.G.dirs[i].get(pn)=='output' else lds
        for n in bs:
            if isinstance(n,int): t[n].append(i)
un=[i for i,c in enumerate(F.cells) if i not in b.cpart and b.G.kind[i] in ('glue','leaf')]
G=collections.defaultdict(lambda: dict(cells=0,inb=collections.Counter(),outb=collections.Counter(),ug=collections.Counter()))
gof={i:grp(F.cells[i].path) for i in un}
for i in un:
    g=G[gof[i]]; g['cells']+=1
    for pn,bs in F.cells[i].ports.items():
        if ctl(pn): continue
        isout=b.G.dirs[i].get(pn)=='output'
        for n in bs:
            if not isinstance(n,int): continue
            for o in (lds[n] if isout else drv[n]):
                if o==i: continue
                z=b.cpart.get(o)
                if z is not None: (g['outb'] if isout else g['inb'])[z]+=1
                elif o in gof and gof[o]!=gof[i]: g['ug'][('>' if isout else '<')+gof[o]]+=1
res={k:dict(cells=v['cells'],inb=dict(v['inb']),outb=dict(v['outb']),ug=dict(v['ug'].most_common(12))) for k,v in sorted(G.items())}
Path(out).write_text(json.dumps(res,indent=0))
for k,v in res.items(): print(v['cells'],k,'IN',v['inb'],'OUT',v['outb'],'UG',list(v['ug'].items())[:6])
