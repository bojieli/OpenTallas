#!/usr/bin/env python3
"""Export all planned QC mesh3 tree stages and the segmented A0 mesh.

This is a geometry export, not clock sign-off.  The tree carries its per-edge
NDR: dropping a band tree or replacing its selected width is an error.  The
existing die_clock_mesh.build_explicit adapter supports one NDR per build;
``build_adapter`` reports that limitation and never silently changes widths.

Run with the same add_common arguments as qc_clk_mesh3 plan, plus --out DIR.
The input B must have legalize()'s cells/site_of for all t/c/b tree namespaces.
"""
import argparse
import bisect
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import qc_clk_mesh3 as M

SITE_X, ROW_Y = 0.054, 0.27


class ExportError(ValueError):
    pass


def snap(v, q):
    return round(round(v / q) * q, 6)


def dbu(x):
    """ASAP7 1x OpenDB integer grid, matching clock_routed.q()."""
    return int(round(float(x)*1000))


def body_inside(rect,x,y,w,h):
    a,b,c,d=map(dbu,rect[:4]); xx,yy=map(dbu,(x,y))
    return a<=xx and xx+dbu(w)<=c and b<=yy and yy+dbu(h)<=d


def body_overlap(rect,x,y,w,h):
    a,b,c,d=map(dbu,rect[:4]); xx,yy=map(dbu,(x,y))
    return xx<c and a<xx+dbu(w) and yy<d and b<yy+dbu(h)


def tree_groups(B):
    """Every physical group edge, including band roots sharing a top-tree cell."""
    cells, sites = B['cells'], B['site_of']
    edges, coverage = [], Counter()
    for ns, rep, nodes in (('t', 'top_rep', B['top_nodes']),
                            ('c', 'col_rep', B['cnodes']),
                            ('b', 'band_rep', B.get('bnodes', []))):
        for n in nodes:
            if not n.get('parent'):
                continue
            try:
                chain = [sites[(ns, n['parent'])]]
                chain += [sites[(rep, n['tag'], k)] for k in range(1, n['nseg'])]
                chain += [sites[(ns, n['tag'])]]
            except KeyError as e:
                raise ExportError(f'missing legalized {ns} cell/repeater: {e}') from e
            et = n.get('et', B['et']['top' if ns == 't' else 'col'])
            coverage[ns] += 1
            for k, (u, v) in enumerate(zip(chain, chain[1:])):
                if u == v:
                    raise ExportError(f'{ns}:{n["tag"]}: self-connected group {u}')
                pu, pv = cells[u]['site'], cells[v]['site']
                vertical = abs(pv[1] - pu[1]) > abs(pv[0] - pu[0])
                edges.append(dict(drv=f'g{u}', load=f'g{v}', layer='M9' if vertical else 'M8',
                                  ndr=et.w, edge=f'{ns}:{n["tag"]}:{k}',
                                  namespace=ns, model_stages=n['nseg'],
                                  pin_to_pin_um=round(M.net_um(cells[u], cells[v]), 6)))
    if B.get('btrees') and not B.get('bnodes'):
        raise ExportError('band trees exist but bnodes/physical legalization are absent')
    # The band-root cell is an alias of its anchor; it is never an undriven extra root.
    for bt in B.get('btrees', []):
        try:
            r, a = sites[('b', bt['root'])], sites[('t', bt['anchor_tag'])]
        except KeyError as e:
            raise ExportError(f'missing physical band-root/anchor: {e}') from e
        if r != a:
            raise ExportError(f'band root {bt["root"]} is not merged into {bt["anchor_tag"]}')
    loads = Counter(e['load'] for e in edges)
    bad = {k: v for k, v in loads.items() if v != 1}
    if bad:
        raise ExportError(f'groups driven by multiple logical edges: {list(bad.items())[:5]}')
    used = {int(e[k][1:]) for e in edges for k in ('drv', 'load')}
    roots = sorted(f'g{k}' for k in used if f'g{k}' not in loads)
    if len(roots) != 1:
        raise ExportError(f'expected one tree root, got {roots[:8]} ({len(roots)} total)')
    graph = defaultdict(list)
    for e in edges:
        graph[e['drv']].append(e['load'])
    seen, todo = set(roots), list(roots)
    for u in todo:
        for v in graph[u]:
            if v not in seen:
                seen.add(v); todo.append(v)
    if len(seen) != len(used):
        raise ExportError('tree graph contains an unreachable cycle or group')
    return edges, used, dict(coverage), roots[0]


def mesh_geometry(A0, driver_groups=None):
    """One VIA89 record per physical M8/M9 crossing, with segmented-line connectivity."""
    hs, vs = A0['H8'], A0['V9']
    if not hs or not vs:
        raise ExportError('segmented mesh needs both M8 and M9 straps')
    parent = list(range(len(hs) + len(vs)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    def join(i, j):
        i, j = find(i), find(j)
        if i != j: parent[i] = j
    ys, byy = [], defaultdict(list)
    for i, (y, x0, x1) in enumerate(hs):
        if x1 <= x0: raise ExportError(f'nonpositive M8 segment {i}')
        byy[round(y, 3)].append(i)
    ys = sorted(byy)
    crosses = defaultdict(lambda: dict(M8=set(), M9=set()))
    for j, (x, y0, y1) in enumerate(vs):
        if y1 <= y0: raise ExportError(f'nonpositive M9 segment {j}')
        for y in ys[bisect.bisect_left(ys, y0 - 1e-6):bisect.bisect_right(ys, y1 + 1e-6)]:
            for i in byy[y]:
                if hs[i][1] - 1e-6 <= x <= hs[i][2] + 1e-6:
                    q = (round(x, 3), round(y, 3))
                    crosses[q]['M8'].add(i); crosses[q]['M9'].add(j)
                    join(i, len(hs) + j)
    if not crosses:
        raise ExportError('mesh has no M8/M9 crossings')
    components = len({find(i) for i in range(len(parent))})
    if components != 1:
        raise ExportError(f'mesh has {components} disconnected conductor components')
    attachments = []
    for k, d in enumerate(A0['drivers']):
        x, y = d['x'], d['y']
        hi = [i for i, (yy, x0, x1) in enumerate(hs) if abs(yy-y) <= 1e-6 and x0-1e-6 <= x <= x1+1e-6]
        vi = [i for i, (xx, y0, y1) in enumerate(vs) if abs(xx-x) <= 1e-6 and y0-1e-6 <= y <= y1+1e-6]
        if not hi and not vi:
            raise ExportError(f'mesh driver {k} at {(x,y)} has no physical strap')
        attachments.append(dict(index=k, xy=[x,y], M8=hi, M9=vi,
                                group=(driver_groups or {}).get(k), kind=d['kind'], mult=d['mult']))
    return dict(schema='opentallas.qc_mesh_conductors.v1',
                M8=[dict(id=i, y=y, x0=x0, x1=x1) for i,(y,x0,x1) in enumerate(hs)],
                M9=[dict(id=i, x=x, y0=y0, y1=y1) for i,(x,y0,y1) in enumerate(vs)],
                vias=[dict(x=x,y=y,M8=sorted(c['M8']),M9=sorted(c['M9'])) for (x,y),c in sorted(crosses.items())],
                drivers=attachments, connected_components=components,
                geometric_crossings=len(crosses), emitted_vias=len(crosses),
                build_state='PLAN_GEOMETRY_ONLY: no dbWire or extraction claim')


def frame_xy(P, host, x, y):
    r = P.rect(host)
    o = P.parts[host].get('orient', 'R0')
    xx, yy = x-r[0], y-r[1]
    if o in ('MY','R180'): xx = r[2]-r[0]-xx
    if o in ('MX','R180'): yy = r[3]-r[1]-yy
    return round(xx,6), round(yy,6)


def export(B):
    edges, used, coverage, root = tree_groups(B)
    P, cells = B['P'], B['cells']
    part_rects = {n:P.rect(n) for n in P.parts}
    site_rows, errors, examples = {}, Counter(), defaultdict(list)
    adapter_constraints = Counter()
    islands = defaultdict(set)
    inst_footprints = defaultdict(lambda: defaultdict(set))
    widths = {}
    for k in sorted(used):
        c = cells[k]
        if not c.get('masters'):
            errors['empty_cell_group'] += 1
            continue
        if len(set(c['masters'])) != 1:
            adapter_constraints['mixed_master_stack_needs_general_pin_tie'] += 1
        # The model is authoritative for every physical unit and transformed pin.
        host = (c.get('island') or {}).get('part') or c.get('body_host')
        for u, unit in enumerate(M.unit_sites(c)):
            m, orient = unit['master'], unit['orient']
            x, y = unit['origin_um']
            w = M.LEF_BUF[m][0]
            widths[m] = w
            hs = [n for n,r in part_rects.items() if dbu(r[0])<=dbu(x+w/2)<=dbu(r[2]) and dbu(r[1])<=dbu(y+ROW_Y/2)<=dbu(r[3])]
            if host is None: host = hs[0] if hs else None
            r = part_rects.get(host)
            why = []
            if r is None:
                channels = [ch['rect_um'] for ch in P.die.get('channels',[]) if ch.get('clock_channel')]
                if not c['kind'].startswith('chan') or not any(body_inside(q,x,y,w,ROW_Y) for q in channels):
                    why.append('no_host')
            elif not body_inside(r,x,y,w,ROW_Y):
                why.append('body_crosses_host_seam')
            for q in B['cores']:
                if body_overlap(q,x,y,w,ROW_Y):
                    why.append('body_on_hard_core'); break
            if not body_inside((0,0,P.W,P.H),x,y,w,ROW_Y): why.append('body_outside_die')
            nm = f'ckt_{k}_{u}'
            for e in why:
                errors[e] += 1
                if len(examples[e]) < 5: examples[e].append(dict(cell=nm,origin_um=[x,y],host=host))
            site_rows[nm] = dict(origin_um=[x,y],part=host,master=m+'_ASAP7_75t_R',
                                 w=w,orient=orient,group=k,kind=c['kind'])
            if host is not None:
                # Bounding box transformed into the master frame: reserved island
                # footprint is the union, shared by every instance of the type.
                p0,p1 = frame_xy(P,host,x,y),frame_xy(P,host,x+w,y+ROW_Y)
                fp=(min(p0[0],p1[0]),min(p0[1],p1[1]),max(p0[0],p1[0]),max(p0[1],p1[1]))
                islands[P.parts[host]['type']].add(fp)
                inst_footprints[P.parts[host]['type']][host].add(fp+(m,))
    from die_clock_mesh import placement_overlaps
    ov = placement_overlaps({n:dict(x=v['origin_um'][0],y=v['origin_um'][1],lib=v['master']) for n,v in site_rows.items()})
    if ov:
        errors['physical_cell_overlap'] = len(ov)
        examples['physical_cell_overlap'] = ov[:5]
    ndrs = sorted({e['ndr'] for e in edges})
    reach = sorted(edges,key=lambda e:-e['pin_to_pin_um'])
    reach_summary = dict(max_um=reach[0]['pin_to_pin_um'] if reach else 0,over_450=sum(dbu(e['pin_to_pin_um'])>450000 for e in edges),
                         worst=[dict(edge=e['edge'],pin_to_pin_um=e['pin_to_pin_um']) for e in reach[:8]],
                         status='PLAN_GEOMETRY; track jogs and extracted RC still required')
    if reach_summary['over_450']:
        errors['clock_stage_over_450_um']=reach_summary['over_450']
        examples['clock_stage_over_450_um']=reach_summary['worst']
    identity = {}
    for t,members in inst_footprints.items():
        allparts=[n for n,d in P.parts.items() if d['type']==t]
        sets={frozenset(members.get(n,set())) for n in allparts}
        identity[t]=dict(instances=len(allparts),hosting=len(members),distinct_footprint_master_sets=len(sets),
                         identical=len(sets)==1,union_sites=len(islands[t]))
    adapter_reasons = []
    import die_clock_mesh as D
    if adapter_constraints:
        import die_clock_mesh as D
        if not hasattr(D,'_explicit_v2_wires'): adapter_reasons.append('V2 heterogeneous pin-tie importer missing')
    if any(n not in D.NDR for n in ndrs): adapter_reasons.append('physical NDR not yet modelled: '+','.join(n for n in ndrs if n not in D.NDR))
    if errors: adapter_reasons.append('physical geometry gate fails')
    if B.get('a0'):
        import importlib.util
        if importlib.util.find_spec('explicit_clock_mesh') is None:
            adapter_reasons.append('continuous mesh dbWire/pin-stack importer missing; tree-only build is incomplete')
    driver_groups = {}
    mesh_form = None
    if B.get('a0'):
        mesh_form = dict(B['a0'])
        mesh_form['drivers'] = [dict(d) for d in B['a0']['drivers']]
        for k,(bt,leaf) in B['bleaf'].items():
            driver_groups[k] = f'g{B["site_of"][("b",leaf)]}'
        # Fine column outputs are mesh drivers too.  Omitting them would export
        # only the new band feeds while silently discarding the original mesh.
        for ct in B['ctrees']:
            for n in ct['nodes']:
                if n['kids']: continue
                idx = B['site_of'][('c',n['tag'])]
                c = cells[idx]
                k = len(mesh_form['drivers'])
                mesh_form['drivers'].append(dict(kind='fine',x=M.r3(n['xy'][0]),y=M.r3(n['xy'][1]),
                                                 mult=sum(M.BUF_STRENGTH[m] for m in c['masters'])))
                driver_groups[k] = f'g{idx}'
        for k,d in enumerate(mesh_form['drivers']):
            idx = int(driver_groups[k][1:])
            d['physical_site'] = list(cells[idx]['site'])
            d['physical_Y_pin'] = list(M.pin_xy(cells[idx],'Y')[0])
    spec = dict(clock_topology_version=2,summary=dict(schema='opentallas.qc_mesh3_all_tree_sites.v1',
                             geometry_verdict='PASS' if not errors else 'FAIL',errors=dict(errors),examples=dict(examples),
                             adapter_constraints=dict(adapter_constraints),
                             groups=len(used),instances=len(site_rows),nets=len(edges),edge_coverage=coverage,root=root,
                             ndrs=ndrs,post_legal_reach=reach_summary,per_type_placement=identity,
                             declared_timing='NOT RUN',declared_clock_signoff='NOT RUN'),
                cell_sites=site_rows,nets=edges,channel_hosts=True,exact_reserve=True,
                build_adapter=dict(verdict='BLOCKED' if adapter_reasons else 'READY',reasons=adapter_reasons,
                                   required_features=['explicit_clock_v2','per_edge_ndr','heterogeneous_M7_ties','complete_continuous_mesh'],
                                   policy='No edge/NDR is discarded or substituted; no route admission from this export.'),
                per_type_island_footprints={t:[list(q) for q in sorted(v)] for t,v in sorted(islands.items())})
    mesh = mesh_geometry(mesh_form,driver_groups) if mesh_form else None
    if mesh is not None:
        for a,d in zip(mesh['drivers'],mesh_form['drivers']):
            a['physical_site'] = d['physical_site']
            a['physical_Y_pin'] = d['physical_Y_pin']
        mesh['ndr'] = B.get('mesh_ndr','8w')
        mesh['partition_taps'] = [dict(t) for t in B['rec']['taps']]
        mesh['core_drops'] = [dict(d) for d in B['a0']['drops']]
        # Parent attach_mesh consumes this same complete graph; the standalone
        # artifact remains useful for independent geometry review.
        for d in mesh['drivers']:
            gi=int(d['group'][1:])
            d['members']=[nm for nm,v in site_rows.items() if v['group']==gi]
        spec['mesh'] = mesh
    return spec,mesh


def prepare_legal(B, a):
    """Use precisely the nominal fine-driver sizing of cmd_solve --geometry legal."""
    if B.get('a0') and a.a0_size == 'drive':
        raise ExportError('model-only a0-size drive has no legalized physical contract')
    rec = B['rec']
    xs, ys = [M.r3(x) for x in rec['xs']], [M.r3(y) for y in rec['ys']]
    taps = [(M.r3(t['tap'][0]), M.r3(t['tap'][1])) for t in rec['taps']]
    fd0 = sorted({(M.r3(n['xy'][0]), M.r3(n['xy'][1])) for ct in B['ctrees'] for n in ct['nodes'] if not n['kids']})
    N0 = M.mesh([(y,xs[0],xs[-1]) for y in ys], [(x,ys[0],ys[-1]) for x in xs],
                fd0,taps,M.RC3[a.fine_w],(M.RC3[a.stub_w],a.stub_um))
    m0 = M.size(M.voronoi_c(N0),a.fine_m,a.sizing)
    B['cells'], stats = M.legalize(B,{q:M.decompose(float(m)) for q,m in zip(fd0,m0)})
    return stats


def render(B, spec, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(15,13))
    for q in B['cores']:
        ax.add_patch(Rectangle((q[0],q[1]),q[2]-q[0],q[3]-q[1],fc='#eeeeee',ec='none'))
    for n in B['P'].parts:
        q=B['P'].rect(n)
        ax.add_patch(Rectangle((q[0],q[1]),q[2]-q[0],q[3]-q[1],fc='none',ec='#bbbbbb',lw=.2))
    cells=B['cells']
    for e in spec['nets']:
        u,v=cells[int(e['drv'][1:])]['site'],cells[int(e['load'][1:])]['site']
        ax.plot([u[0],v[0]],[u[1],v[1]],c='#c65b22' if e['namespace']=='b' else '#1b6d9b',lw=.25,alpha=.65)
    for k,col in [('band_driver','#b3003c'),('band_node','#ed9b00'),('band_rep','#7c3000')]:
        q=[c['site'] for c in cells if c['kind']==k]
        if q: ax.scatter([p[0] for p in q],[p[1] for p in q],s=2,c=col,label=k)
    for k,ex in spec['summary']['examples'].items():
        q=[x['origin_um'] for x in ex if isinstance(x,dict) and 'origin_um' in x]
        if q: ax.scatter([p[0] for p in q],[p[1] for p in q],s=30,facecolors='none',edgecolors='magenta')
    ax.set_aspect('equal'); ax.set_xlim(0,B['P'].W); ax.set_ylim(0,B['P'].H)
    ax.legend(loc='upper left',fontsize=7)
    ax.set_title('QC R26 all tree stages: '+spec['summary']['geometry_verdict']+' '+str(spec['summary']['errors']))
    fig.savefig(path,dpi=130,bbox_inches='tight'); plt.close(fig)


def common_slot_failure(B, path, error):
    """Diagnose the actual failed allocator frame; no placement is retried here."""
    tb=error.__traceback__; loc=None
    while tb:
        if tb.tb_frame.f_code.co_name=='assign_periodic': loc=tb.tb_frame.f_locals
        tb=tb.tb_next
    if not loc or 'key' not in loc or 'mem' not in loc: return None
    key,mem,I=loc['key'],loc['mem'],loc['I']
    typ,fx,fy,_=key; gx,gy,valid=I.tgrid[typ]
    used=loc['used'][typ]; ov=loc['ov']
    candidates=[]
    for k,j in zip(*valid.nonzero()):
        sites=[I.to_die(n,float(gx[k]),float(gy[j])) for _,n in mem]
        blocked=[n for (_,n),(x,y) in zip(mem,sites) if ov(x,y)]
        state='used' if (int(k),int(j)) in used else 'blocked' if blocked else 'free'
        candidates.append(dict(k=int(k),j=int(j),x=float(gx[k]),y=float(gy[j]),state=state,
                               d=abs(float(gx[k])+I.CW/2-fx)+abs(float(gy[j])+ROW_Y/2-fy),blocked_by_instances=blocked))
    nearest={(int(k),int(j)) for _,k,j in loc.get('cand',[])}
    counts=Counter(c['state'] for c in candidates)
    bounded=Counter(c['state'] for c in candidates if (c['k'],c['j']) in nearest)
    free=sorted((c for c in candidates if c['state']=='free'),key=lambda c:c['d'])
    result=dict(type=typ,failed_class=list(key),members=[n for _,n in mem],
                 bounded_candidates=dict(bounded),all_valid_slots=dict(counts),
                 nearest_free_slots=free[:8],rule='same site must be unused and clear in every member; no island growth or placement change',slots=candidates)
    (path/'common_slot_failure.json').write_text(json.dumps(result,indent=1)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(12,9))
    colors={'used':'#004d99','blocked':'#c62828','free':'#2e7d32'}
    for state,col in colors.items():
        q=[c for c in candidates if c['state']==state]
        if q: ax.scatter([c['x']+I.CW/2 for c in q],[c['y']+ROW_Y/2 for c in q],s=10,c=col,label=state+' '+str(len(q)))
    ax.scatter([fx],[fy],marker='x',s=80,c='black',label='failing class')
    cells=loc['cells']; members={n for _,n in mem}
    # Show the actual non-top cell footprints causing slot exclusion, in each
    # member's master frame. The union is precisely what common-slot fit sees.
    for c in cells:
        if c['kind'] in loc['topk'] or not c['masters']: continue
        w=max(M.LEF_BUF[m][0] for m in c['masters']); h=ROW_Y*len(c['masters'])
        x,y=c['site'][0]-w/2,c['site'][1]-ROW_Y/2
        for n in members:
            r=B['P'].rect(n)
            if x>=r[2] or x+w<=r[0] or y>=r[3] or y+h<=r[1]: continue
            a,b=frame_xy(B['P'],n,x,y),frame_xy(B['P'],n,x+w,y+h)
            xx,yy=min(a[0],b[0]),min(a[1],b[1]); ww,hh=abs(a[0]-b[0]),abs(a[1]-b[1])
            ax.add_patch(Rectangle((xx,yy),ww,hh,fc='#777777',alpha=.35,ec='none'))
    ax.set_xlim(fx-180,fx+180);ax.set_ylim(fy-180,fy+180);ax.set_aspect('equal');ax.legend(fontsize=8)
    ax.set_title(f'Common slot FAIL {key}: nearest {dict(bounded)}, whole type {dict(counts)}')
    fig.savefig(path/'common_slot_failure.png',dpi=150,bbox_inches='tight');plt.close(fig)
    return {k:v for k,v in result.items() if k!='slots'}


def failed_placement(B, path, error):
    """Keep a useful raw-geometry failure artifact if placement cannot complete."""
    rows=[]
    for ns,nodes in (('t',B['top_nodes']),('c',B['cnodes']),('b',B.get('bnodes',[]))):
        by={n['tag']:n for n in nodes}
        for n in nodes:
            if not n.get('parent'): continue
            p=by[n['parent']]['xy']
            for k in range(1,n['nseg']+1):
                q=[p[j]+(n['xy'][j]-p[j])*k/n['nseg'] for j in (0,1)]
                hit=any(c[0]<q[0]<c[2] and c[1]<q[1]<c[3] for c in B['cores'])
                rows.append(dict(namespace=ns,tag=n['tag'],stage=k,xy=q,on_core=hit,
                                 plan_stage_reach_um=M.md(p,n['xy'])/n['nseg']))
    slot=common_slot_failure(B,path,error)
    rec=dict(verdict='FAIL',stage='legalization',error=str(error),common_slot=slot,
             raw_buffer_sites=len(rows),raw_sites_on_hard_core=sum(r['on_core'] for r in rows),
             raw_stage_reach_over_450=sum(r['plan_stage_reach_um']>450.0001 for r in rows),sites=rows)
    (path/'placement_failure.json').write_text(json.dumps(rec,indent=1)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(15,13))
    for q in B['cores']:
        ax.add_patch(Rectangle((q[0],q[1]),q[2]-q[0],q[3]-q[1],fc='#eeeeee',ec='none'))
    for ns,col in [('t','#1b6d9b'),('c','#9e9e9e'),('b','#c65b22')]:
        pts=[r['xy'] for r in rows if r['namespace']==ns]
        if pts: ax.scatter([q[0] for q in pts],[q[1] for q in pts],s=1,c=col,label=ns)
    pts=[r['xy'] for r in rows if r['on_core']]
    if pts: ax.scatter([q[0] for q in pts],[q[1] for q in pts],s=8,c='magenta',label='raw site on hard core')
    ax.set_aspect('equal'); ax.legend(fontsize=8)
    ax.set_title('QC R26 legalization FAIL: raw candidate sites (not legal placement)')
    fig.savefig(path/'placement_failure.png',dpi=130,bbox_inches='tight'); plt.close(fig)
    return rec


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    M.add_common(ap); ap.add_argument('--out',required=True)
    ap.add_argument('--thev'); ap.add_argument('--slew-sens')
    a=ap.parse_args(argv)
    B=M.build(a,M.Stage(a.stage))
    B['mesh_ndr']=a.fine_w
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    # The parent planner owns plan-computed sizing and legalization.  This tool
    # refuses to infer or substitute missing band driver sizing/placement.
    if B.get('a0') and not hasattr(M,'legalize'):
        raise ExportError('planner has no physical legalization')
    try:
        stats=prepare_legal(B,a)
    except (RuntimeError,ExportError) as error:
        rec=failed_placement(B,out,error)
        print(json.dumps({k:v for k,v in rec.items() if k!='sites'},indent=1))
        return 2
    spec,mesh=export(B)
    spec['summary']['planner_legalization']=stats
    spec['summary']['tool_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    spec['summary']['planner_tool_sha256']=hashlib.sha256(Path(M.__file__).read_bytes()).hexdigest()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    (out/'all_tree_sites.json').write_text(json.dumps(spec,indent=1)+'\n')
    if mesh is not None: (out/'mesh_conductors.json').write_text(json.dumps(mesh,indent=1)+'\n')
    render(B,spec,out/'all_tree_geometry.png')
    print(json.dumps(dict(summary=spec['summary'],build_adapter=spec['build_adapter']),indent=1))
    return 0 if spec['summary']['geometry_verdict']=='PASS' else 2


if __name__=='__main__':
    try: raise SystemExit(main())
    except ExportError as e:
        print(f'QC_MESH3_EXPORT_FAIL: {e}',file=sys.stderr); raise SystemExit(2)
