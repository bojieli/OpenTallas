"""HBM-BIND-2 (2026-10-29): plan-landing homes for the residual scorer / SFU glue (COORD ruling 10-29 for HBM-BIND-2).
Usage: landing_homes.py WT PLAN MANIFEST ELAB OUT_JSON
Rules (whole cells, no FF fracture, no duplication, no semantic edit):
 scorer quarter hb_idx__s_X (ot_hbm_idx_score_quarter_static_h):
  F = partition of ge[0].gc[0] (r0c0 front leaf), T = partition of the ge[*].u_t tails (must be one partition).
  * leaf glue scorer.ge[e].gc[c].leaf.* (W/E pin regs, sum bus, chunk core glue, u_qlate/u_vl/u_rr): with that leaf's
    u_hc partition; a leaf whose 8 u_hc sit in two partitions goes whole to the partition holding most of its u_hc
    bit connections (reported).
  * quarter glue scorer.*: E side = forward-reachable (data nets, quarter glue only) from a gc[NCH-1] leaf, u_t, md or
    keep_pipe -> T (E glue, tail regs, output score regs, score_fault_check); the rest (input pin flops + W glue) -> F.
    reset relay g_delivered_reset.u_rr -> F; ge[e].md / ge[e].keep_pipe / score_fault_check -> T.
  * keybuf glue and the quarter fault $or -> the keybuf line partition (hub).
 sfucore_X: every residual cell -> the partition of u_engine.u_memory (operand store, b113 = SU lane landing L47/L54).
Output: map parts {path: partition} + report."""
import sys,json,re,collections
from pathlib import Path
w,plan,man,elab,out=sys.argv[1:6]
sys.path.insert(0,str(Path(w)/'tools'));sys.path.insert(0,str(Path(w)/'tools/die_plan'));import bind as B
a=json.loads(Path(man).read_text());p=json.loads(Path(plan).read_text());p['asbuilt']=a
b=B.Binder(p,json.loads(Path(elab).read_text()),Path(plan).parent,a['base']);b.map_cells();F=b.F;cp=b.cpart
ctl=lambda pn: bool(re.fullmatch(r'(clk.*|clock.*|ck(_.*)?|rst.*|reset.*|arst.*|srst.*)',pn.lower()))
drv=collections.defaultdict(list);lds=collections.defaultdict(list)
for i,c in enumerate(F.cells):
    for pn,bs in c.ports.items():
        if ctl(pn): continue
        t=drv if b.G.dirs[i].get(pn)=='output' else lds
        for n in bs:
            if isinstance(n,int): t[n].append(i)
un={i for i,c in enumerate(F.cells) if i not in cp and b.G.kind[i] in ('glue','leaf')}
path=lambda i:F.cells[i].path
out_parts={};rep=dict(scorer={},sfu={},split_leaves=[],left=[])
def mapped_under(pre): return collections.Counter(cp[i] for i in cp if path(i).startswith(pre))
for q in sorted({re.match(r'(hb_idx__s_[A-Z]+)\.',path(i)).group(1) for i in un if re.match(r'hb_idx__s_[A-Z]+\.',path(i))}):
    sc=q+'.scorer.'
    Fp=mapped_under(sc+'ge[0].gc[0].').most_common(1)[0][0]
    tails={cp[i] for i in cp if re.fullmatch(re.escape(sc)+r'ge\[\d+\]\.u_t',path(i))}
    assert len(tails)==1,(q,tails); Tp=tails.pop()
    nch=1+max(int(re.search(r'\.gc\[(\d+)\]',path(i)).group(1)) for i in cp if path(i).startswith(sc+'ge[0].gc['))
    cnt=collections.Counter()
    # leaves
    leaves=collections.defaultdict(list)
    for i in un:
        m=re.match(re.escape(sc)+r'(ge\[\d+\]\.gc\[\d+\])\.leaf\.',path(i))
        if m: leaves[m.group(1)].append(i)
    for lf,ids in sorted(leaves.items()):
        pre=sc+lf+'.leaf.'; hp=mapped_under(pre)
        if len(hp)>1:
            idset=set(ids);vote=collections.Counter()
            for i in ids:
                for pn,bs in F.cells[i].ports.items():
                    if ctl(pn): continue
                    isout=b.G.dirs[i].get(pn)=='output'
                    for n in bs:
                        if isinstance(n,int):
                            for o in (lds[n] if isout else drv[n]):
                                if o in cp and path(o).startswith(pre): vote[cp[o]]+=1
            z=vote.most_common(1)[0][0]; rep['split_leaves'].append(dict(leaf=q+'.'+lf,hc_parts=dict(hp),bit_vote=dict(vote),home=z))
        else: z=next(iter(hp))
        for i in ids: out_parts[path(i)]=z; cnt['leaf:'+z]+=1
    # quarter glue: E side by forward reachability
    qg={i for i in un if path(i).startswith(sc) and i not in {j for v in leaves.values() for j in v}}
    def is_esrc(o):
        s=path(o)
        return bool(re.match(re.escape(sc)+r'ge\[\d+\]\.(gc\[%d\]\.leaf\.|u_t$|md$|keep_pipe$)'%(nch-1),s))
    E=set();stack=[]
    for i in qg:
        for pn,bs in F.cells[i].ports.items():
            if ctl(pn) or b.G.dirs[i].get(pn)=='output': continue
            if any(isinstance(n,int) and any(is_esrc(o) for o in drv[n]) for n in bs): E.add(i);stack.append(i);break
    while stack:
        i=stack.pop()
        for pn,bs in F.cells[i].ports.items():
            if ctl(pn) or b.G.dirs[i].get(pn)!='output': continue
            for n in bs:
                if isinstance(n,int):
                    for o in lds[n]:
                        if o in qg and o not in E: E.add(o);stack.append(o)
    for i in qg:
        s=path(i)
        if re.fullmatch(re.escape(sc)+r'(ge\[\d+\]\.(md|keep_pipe)|score_fault_check)',s): z=Tp
        elif s.startswith(sc+'g_delivered_reset.') or s.startswith(sc+'g_legacy_reset.'): z=Fp
        else: z=Tp if i in E else Fp
        out_parts[s]=z; cnt[('E:' if z==Tp else 'W:')+z]+=1
    # keybuf glue + quarter-top glue -> keybuf line partition
    kb=mapped_under(q+'.keybuf.').most_common(1)[0][0]
    for i in un:
        s=path(i)
        if s.startswith(q+'.') and not s.startswith(sc): out_parts[s]=kb; cnt['kb:'+kb]+=1
    rep['scorer'][q]=dict(front=Fp,tail=Tp,nch=nch,cells=dict(cnt))
for r in sorted({path(i).split('.')[0] for i in un if path(i).startswith('sfucore_')}):
    z=mapped_under(r+'.u_core.u_engine.u_memory.').most_common(1)[0][0];n=0
    for i in un:
        if path(i).startswith(r+'.'): out_parts[path(i)]=z;n+=1
    rep['sfu'][r]=dict(home=z,cells=n)
rep['left']=sorted(path(i) for i in un if path(i) not in out_parts)[:50]; rep['n_left']=sum(1 for i in un if path(i) not in out_parts)
rep['n_unmapped_in']=len(un); rep['n_homed']=len(out_parts)
Path(out).write_text(json.dumps(dict(schema='hbm_bind_2.landing_homes.v1',method=__doc__,report=rep,parts=out_parts),indent=0))
print(json.dumps(rep,indent=1)[:5000])
