#!/usr/bin/env python3
"""HEAD-START-2: placed-cell reach + full-body census of the START vehicle.

Vehicle = final5 driven START netlist (mapped START logic + per-branch BUFx8 data
chains) + legal1 clock tree (ctree) + one local clock-entry BUFx8 per stage
(head_start_local_clock.py). Every net is measured driver-pin -> each sink pin
(cell body centres, port pins at their placed xy); the stage clock net is split
at the local BUF8 (tree driver -> BUF8, BUF8 -> stage FF CLK pins).
Gate: every hop <= 405 um (OWNER repeater reach). Bodies: full-XY rectangle
overlaps among all cells, native row phase (0.27) and site grid (0.054), and
SiteMap legality (no hard-core/halo/PHY domain).  Geometry only; no timing.
"""
import argparse,collections,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2] if len(sys.argv)<2 else None
def man(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('repo','mapped','physical','stages','ctree','lef','plan','out'):p.add_argument('--'+n,required=True)
    p.add_argument('--top',default='ot_die_start_stages');p.add_argument('--limit',type=float,default=405.0)
    a=p.parse_args();R=Path(a.repo)
    sys.path[:0]=[str(R/'tools/die_plan'),str(R/'tools/s81_head')]
    import schema as S,die_trial as D,start_stage_emit as E
    from head_start_pack import lef_sizes
    sizes=lef_sizes(Path(a.lef).read_text())
    plan=S.Plan(json.load(open(a.plan)),Path(a.plan));site=D.SiteMap(plan)
    mod=json.load(open(a.mapped))['modules'][a.top];ph=json.load(open(a.physical));st=json.load(open(a.stages))
    cv=(Path(a.ctree)/'ctree.v').read_text();ct=(Path(a.ctree)/'ctree.tcl').read_text()
    tcells,txy=E.ctree_cells(cv,ct)
    drv=ph['stage_clock_drivers']
    # ---- bodies
    bodies=[]
    for n,c in ph['cells'].items():bodies.append((n,c['cell'],tuple(c['rect_um']),'start'))
    for n,(m,_,_) in tcells.items():
        x,y=txy[n];w,h=sizes[m];bodies.append((n,m,(x,y,round(x+w,3),round(y+h,3)),'clock'))
    for port,d in drv.items():bodies.append((d['inst'],d['cell'],tuple(d['rect_um']),'local_clk'))
    bins=collections.defaultdict(list);B=4.0
    for i,(_,_,r,_) in enumerate(bodies):
        for gx in range(math.floor(r[0]/B),math.floor(r[2]/B)+1):
            for gy in range(math.floor(r[1]/B),math.floor(r[3]/B)+1):bins[gx,gy].append(i)
    ov=set()
    for ids in bins.values():
        for k,i in enumerate(ids):
            ri=bodies[i][2]
            for j in ids[k+1:]:
                rj=bodies[j][2]
                if min(ri[2],rj[2])-max(ri[0],rj[0])>1e-6 and min(ri[3],rj[3])-max(ri[1],rj[1])>1e-6:ov.add((min(i,j),max(i,j)))
    ovk=collections.Counter('/'.join(sorted((bodies[i][3],bodies[j][3]))) for i,j in ov)
    rowbad=[b[0] for b in bodies if abs(b[2][1]/.27-round(b[2][1]/.27))>1e-4]
    sitebad=[b[0] for b in bodies if abs(b[2][0]/.054-round(b[2][0]/.054))>1e-3]
    def forb_hit(r):
        for f in site.forb:
            if min(r[2],f[2])-max(r[0],f[0])>1e-6 and min(r[3],f[3])-max(r[1],f[1])>1e-6:return f[4]
        return None
    # area test (a body edge abutting a halo edge is legal; corner point tests misread float equality)
    illegal=[b[0] for b in bodies if forb_hit(b[2]) or not all(site.in_part((x,y),0) for x in (b[2][0],b[2][2]) for y in (b[2][1],b[2][3]))]
    ctr={b[0]:((b[2][0]+b[2][2])/2,(b[2][1]+b[2][3])/2) for b in bodies}
    # ---- nets of the START netlist
    pdir={n:v['direction'] for n,v in mod['ports'].items()}
    pxy={n:v['xy_um'] for n,v in ph['ports'].items()}
    clkport={s['clock_port']:s for s in st['stages']}
    for cp,s in clkport.items():pxy.setdefault(cp,s['clock_pin_xy_um'])
    drivers={};sinks=collections.defaultdict(list)
    for n,v in mod['ports'].items():
        for b in v['bits']:
            if isinstance(b,str):continue
            (drivers.__setitem__(b,('port',n)) if v['direction']=='input' else sinks[b].append(('port',n,None)))
    for n,c in mod['cells'].items():
        for pin,bits in c['connections'].items():
            for b in bits:
                if isinstance(b,str):continue
                if c['port_directions'][pin]=='output':drivers[b]=('cell',n,pin)
                else:sinks[b].append(('cell',n,pin))
    def loc(e):return pxy[e[1]] if e[0]=='port' else ctr[e[1]]
    hops=collections.defaultdict(list);missing=collections.Counter()
    portbit={v['bits'][0]:n for n,v in mod['ports'].items() if v['direction']=='input'}
    for b,ss in sinks.items():
        d=drivers.get(b)
        if d is None:missing['undriven']+=1;continue
        if d[0]=='port' and d[1] in clkport:
            s=clkport[d[1]];buf=drv[d[1]];bc=ctr[buf['inst']]
            for e in ss:hops['local_clk->FF'].append((round(man(bc,loc(e)),3),buf['inst'],e[1]))
            continue
        kind='reset_port->' if d[0]=='port' else 'cell->'
        for e in ss:
            if e[1] not in ctr and e[0]=='cell':missing['unplaced_sink']+=1;continue
            k=kind+('START_out_pin' if e[0]=='port' else 'cell')
            hops[k].append((round(man(loc(d),loc(e)),3),d[1],e[1]))
    # tree cell driving each stage clock port -> local BUF8
    ydrv={y:n for n,(m,_,y) in tcells.items()}
    for cp,s in clkport.items():
        t=ydrv.get(cp) or ydrv.get(s['clock_net'])
        if t is None:missing['tree_driver_not_found']+=1;continue
        hops['tree->local_clk'].append((round(man(ctr[t],ctr[drv[cp]['inst']]),3),t,drv[cp]['inst']))
    # inside-tree hops (re-measured on centres)
    tin=collections.defaultdict(list)
    for n,(m,A,Y) in tcells.items():tin[A].append(n)
    for n,(m,A,Y) in tcells.items():
        for k in tin.get(Y,()):hops['tree->tree'].append((round(man(ctr[n],ctr[k]),3),n,k))
    summ=dict(limit_um=a.limit,bodies=len(bodies),body_kinds=dict(collections.Counter(b[3] for b in bodies)),
        overlaps=len(ov),overlap_kinds=dict(ovk),off_row_phase=len(rowbad),off_site_grid=len(sitebad),sitemap_illegal=len(illegal),
        missing=dict(missing),
        hops={k:dict(n=len(v),max=max(v)[0] if v else None,worst=max(v) if v else None,over=sum(x[0]>a.limit for x in v)) for k,v in sorted(hops.items())})
    summ['all_hops_over']=sum(h['over'] for h in summ['hops'].values())
    summ['verdict']='PASS' if summ['all_hops_over']==0 and not ov and not illegal and not rowbad and not missing else 'FAIL'
    doc=dict(schema='head_start_placed_reach/1',scope='prebuild placed-cell geometry, no timing',summary=summ,
        overlap_examples=[(bodies[i][0],bodies[j][0]) for i,j in sorted(ov)[:50]],illegal_examples=illegal[:50],rowbad=rowbad[:50],
        over=[x for v in hops.values() for x in v if x[0]>a.limit][:500])
    Path(a.out).write_text(json.dumps(doc,indent=1));print(json.dumps(summ,indent=1))
if __name__=='__main__':main()
