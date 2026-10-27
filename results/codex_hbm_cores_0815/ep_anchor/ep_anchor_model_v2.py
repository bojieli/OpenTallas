"""Read-only EP anchor diagnosis: exact connectivity, proposed FF box move only.
MODELS ARE NOT ACTUAL PLACED RESULTS. No pin, RTL or pipeline change.
"""
import collections, functools, importlib.util, json, math, sys
from pathlib import Path

base, helper, out = map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=True)
sp=importlib.util.spec_from_file_location('geom',helper);g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
D=g.Design(base);active=set();sys.setrecursionlimit(100000)
@functools.lru_cache(None)
def sources(n):
    if n in active:raise ValueError('combinational cycle')
    dr=D.nets[n][1]
    if not dr or dr[0]!='i':return frozenset()
    c=dr[1]
    if D.kind(c)=='S':return frozenset([c])
    if D.kind(c) not in 'BLK':return frozenset()
    active.add(n);r=set()
    for nn,clk in D.cell_in[c]:
        if not clk:r.update(sources(nn))
    active.remove(n);return frozenset(r)
hist=collections.Counter();viol=[]
for cap,c in D.cells.items():
    if c[0]!='S':continue
    st=set()
    for n,clk in D.cell_in[cap]:
        if not clk:st.update(sources(n))
    x,y=g.ctr(c)
    for src in st:
        sx,sy=g.ctr(D.cells[src]);d=abs(sx-x)+abs(sy-y)
        if d>405:
            name=D.cells[src][6];hist[name]+=1;viol.append((d,name,c[6]))
print('violating launch histogram',hist)
report=dict(scope=__doc__,original_over405_pairs=len(viol),original_launch_histogram=dict(hist),
            original_worst=sorted(viol,reverse=True)[:24],models=[])
# Reset drivers are existing native DFFs. Relocate the actual offending one
# to a free row site in the E edge of the central macro channel.
names=set(hist)
to_move={cid:c for cid,c in D.cells.items() if c[6] in names and
         (c[6].startswith('u_fcore.rn_') or
          c[6].replace(chr(92),'')=='u_fcore.u_rxb.g_block[0].u_block.vp[1]$_DFF_PN0_')}
occupied=[c for cid,c in D.cells.items() if cid not in to_move]
moves={}
for cid,c in to_move.items():
    w,h=c[4]-c[2],c[5]-c[3]
    cand=[]
    for iy in range(math.ceil(179.844/.27),math.floor((190.62-h)/.27)+1):
        for ix in range(math.ceil(188.568/.054),math.floor((198.72-w)/.054)+1):
            x,y=round(ix*.054,6),round(iy*.27,6)
            cand.append((abs(x-190.08)+abs(y-185.76),x,y))
    found=None
    local=[p for p in occupied if p[4]>188.4 and p[2]<198.8 and p[5]>179.7 and p[3]<190.8]
    for _,x,y in sorted(cand):
        if not any(x+w+.108>p[2] and x-.108<p[4] and y+h>p[3] and y<p[5] for p in local):
            found=x,y;break
    if found is None:raise ValueError('no legal proposed reset-driver site')
    x,y=found;moves[cid]=[x,y,x+w,y+h]
    occupied.append((c[0],c[1],*moves[cid],c[6]))
lines=[]
for line in base.read_text().splitlines():
    f=line.split('\t')
    if f[0]=='C' and int(f[1]) in moves:f[4:8]=[f'{v:.6f}' for v in moves[int(f[1])]]
    lines.append('\t'.join(f))
p=out/'reset_anchor_model.tsv';p.write_text('\n'.join(lines)+'\n')
m=g.metrics(p,odb='3_place.odb');rules,verdict=g.judge(m,None,[203.04,375.84])
report['models'].append(dict(kind='PROPOSED BOX ANCHORS ONLY',moves={D.cells[n][6]:v for n,v in moves.items()},
                            auto_geom_prediction=verdict,rules=rules,metrics=m))
(out/'report.json').write_text(json.dumps(report,indent=1)+'\n')
print('MODEL',verdict,{k:m[k] for k in ('r2r_max','r2r_captures_gt405','pin_reg_max','pin_reg_p90','fill','empty_frac') if k in m})
