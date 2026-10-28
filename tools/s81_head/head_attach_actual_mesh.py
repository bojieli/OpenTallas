"""Attach actual HEAD clock endpoints to the declared continuous metal mesh.

Additive preparation only: emits explicit dbWire Tcl/native diagnostic RC.  Driver
risers are bounded by the existing 2.5um island rule.  Endpoint jogs remain actual
metal, with source names retained; neither a provider nor signoff is invented.
"""
import argparse, copy, json, sys
from pathlib import Path

def jog_tracks(plan, mesh, eps, tools, reach=450., tree_wires=()):
    """HEAD-R23 (COORD-approved fix a): one PG-aware M8 jog track per endpoint.

    Every endpoint jogs on M8 to the nearest M9 strap spanning the track (M9 PG stripes are 12.96 um wide,
    so M9 jogs are not used).  The track is the M8 routing track nearest the endpoint y whose drawn-shield
    envelope (clock 8w + one NDR space + VSS shield on each side, shields running ext past both ends) keeps
    the NDR space to every die M8 PG stripe (core grid + PHY domains, die_infra.pg_rects) over the whole
    jog span, keeps the same clearance to every M8 mesh strap envelope and to every jog already placed on a
    different track.  An endpoint whose own y is legal keeps it (stub 0); otherwise the port node moves to
    the chosen track and the <= 1.08-um remainder is the local stub to the published pin (reported)."""
    import bisect, schema as S, die_infra as DI, die_clock_128 as C, die_clock_mesh as D
    nd = D.NDR['8w']; hw, off, ext = C.shield_geom(nd); half = off + hw; sp = nd['space']
    P = S.Plan(S.load(plan))
    pg = sorted((y0, y1, x0, x1) for net, L, x0, y0, x1, y1 in DI.pg_rects(P, C.pg_grid(P, None)) if L == 'M8')
    ys = [r[0] for r in pg]
    straps = [(h['y'] - half, h['y'] + half, h['x0'] - ext, h['x1'] + ext) for h in mesh['M8']]
    # the shielded M8 legs of the fixed H-tree (build mesh.json fixed_wires) are obstacles too
    straps += [(y0 - half, y0 + half, min(x0, x1) - ext, max(x0, x1) + ext)
               for w in tree_wires for L, x0, y0, x1, y1 in (sg[:5] for sg in w.get('segs', []))
               if L == 'M8' and abs(y0 - y1) < 1e-9]
    placed = {}
    pitch, offs = P.layers['M8']['pitch_um'], P.layers['M8']['offset_um']
    def hits(lo, hi, a0, a1, rects):
        return any(r0 - sp < hi and lo < r1 + sp and q0 - sp < a1 and a0 < q1 + sp for r0, r1, q0, q1 in rects)
    def pg_hit(lo, hi, a0, a1):
        i = bisect.bisect_left(ys, lo - 2.0)
        while i < len(pg) and pg[i][0] < hi + sp:
            r0, r1, q0, q1 = pg[i]
            if r0 - sp < hi and lo < r1 + sp and q0 - sp < a1 and a0 < q1 + sp: return True
            i += 1
        return False
    out = []
    for xy in eps:
        x, y = xy
        k0 = round((y - offs) / pitch); best = None
        on = sorted((abs(h['y'] - y), h['y']) for h in mesh['M8'] if abs(h['y'] - y) <= 1.08 + 1e-6 and h['x0'] <= x <= h['x1'])
        if on:                                         # an M8 mesh strap within one PG half-pitch: port on it, no jog
            out.append(round(on[0][1], 4)); continue
        for dk in sorted(range(-20, 21), key=abs):
            ty = round(offs + (k0 + dk) * pitch, 4)
            if abs(ty - y) > 1.08 + 1e-6: continue
            if any(abs(h['y'] - ty) < 1e-6 and h['x0'] <= x <= h['x1'] for h in mesh['M8']):
                best = ty; break                       # the track is an M8 mesh strap: port on it, no jog
            cand = [(abs(v['x'] - x), v['x']) for v in mesh['M9'] if v['y0'] - 1e-6 <= ty <= v['y1'] + 1e-6]
            if not cand or min(cand)[0] > reach + 1e-6: continue
            xx = min(cand)[1]
            a0, a1 = min(x, xx) - ext, max(x, xx) + ext
            lo, hi = ty - half, ty + half
            if pg_hit(lo, hi, a0, a1) or hits(lo, hi, a0, a1, straps): continue
            if any(abs(py - ty) > 1e-6 and hits(lo, hi, a0, a1, [(py - half, py + half, q0, q1)])
                   for py, spans in placed.items() if abs(py - ty) < 2 * half + sp for q0, q1 in spans):
                continue
            best = ty; placed.setdefault(ty, []).append((a0, a1)); break
        out.append(best)
    return out

def main():
    a=argparse.ArgumentParser(); a.add_argument('--tools',required=True);a.add_argument('--build',required=True);a.add_argument('--straps',required=True);a.add_argument('--endpoints',required=True);a.add_argument('--out',required=True);a.add_argument('--tap-reach',type=float,default=450.);a.add_argument('--plan',help='HEAD-R23: plan for the PG-aware M8 jog track (die PG grid incl. PHY domains)');x=a.parse_args()
    sys.path.insert(0,x.tools)
    import explicit_clock_mesh as E,die_clock_mesh as D,clock_routed as C,die_clock as DC
    b=Path(x.build);o=Path(x.out);o.mkdir(parents=True,exist_ok=True)
    read=lambda p:json.loads(Path(p).read_text())
    cells=read(b/'place.json');ns=read(b/'nets.json');out=read(b/'mesh.json');ss=read(x.straps);ep=read(x.endpoints)['endpoints']
    mesh=dict(ndr='8w',M8=[],M9=[],vias=[],drivers=[],taps=[],tap_jog_um=x.tap_reach)
    for l,q,lo,hi,*rest in ss:
        mesh[l].append(dict(y=q,x0=lo,x1=hi) if l=='M8' else dict(x=q,y0=lo,y1=hi))
    mesh['vias']=[dict(x=v['x'],y=h['y']) for h in mesh['M8'] for v in mesh['M9'] if h['x0']<=v['x']<=h['x1'] and v['y0']<=h['y']<=v['y1']]
    groups={};errors=[]
    for n,c in cells.items():
        if c.get('plan_kind')=='mesh_driver':groups.setdefault(c['group'],[]).append(n)
    for group,units in sorted(groups.items()):
        pts=[C.pin_point(cells,n,'Y',cells[n].get('lib',D.BUF)) for n in units]
        xx=sum(p[0] for p in pts)/len(pts);yy=sum(p[1] for p in pts)/len(pts)
        candidates=[h for h in mesh['M8'] if h['x0']<=xx<=h['x1']]
        if not candidates:raise ValueError(f'no mesh conductor under group {group}')
        h=min(candidates,key=lambda h:abs(h['y']-yy));dist=max(abs(p[1]-h['y']) for p in pts)
        mesh['drivers'].append(dict(group='g'+str(group),xy=[xx,h['y']],actual_units=units,max_pin_riser_um=dist))
        if dist>2.5+1e-6:errors.append(dict(kind='driver_riser_over_2p5',group=group,max_um=dist))
    mapping=[]
    pts=[(e['mesh_input'] if e['kind']=='native_core_clock' else e)['die_xy_um'] for e in ep]
    tracks=jog_tracks(x.plan,mesh,pts,x.tools,x.tap_reach,out.get('fixed_wires',[])) if x.plan else [None]*len(ep)
    for i,e in enumerate(ep):
        core=e['kind']=='native_core_clock';p=e['mesh_input'] if core else e
        xy=p['die_xy_um'];port=p['port'];mesh['taps'].append(dict(xy=xy,part=e['part'],endpoint_port=port,endpoint_kind=e['kind'],**({'jog_y':tracks[i]} if tracks[i] is not None else {})))
        if x.plan and tracks[i] is None:errors.append(dict(kind='no_pg_legal_m8_jog_track',part=e['part'],port=port,xy=xy))
        cand=[abs(h['y']-xy[1]) for h in mesh['M8'] if h['x0']<=xy[0]<=h['x1']] + [abs(v['x']-xy[0]) for v in mesh['M9'] if v['y0']<=xy[1]<=v['y1']]
        reach=min(cand,default=float('inf'))
        if reach>x.tap_reach+1e-6:errors.append(dict(kind='endpoint_off_mesh_reach',part=e['part'],port=port,xy=xy,nearest_projected_um=reach))
        mapping.append(dict(mesh_port=f'msh_t_{i}',part=e['part'],port=port,xy=xy,functional_port=e['port'] if core else None))
    # Conductor graph itself validates complete crossing/via inventory and connectivity.
    graphmesh=copy.deepcopy(mesh)
    if any(z['kind']=='endpoint_off_mesh_reach' for z in errors):graphmesh['taps']=[]
    graph=E.conductor_graph(graphmesh)
    receipt=dict(status='BLOCKED_ATTACHMENT_GEOMETRY' if errors else 'PREPARED_NOT_ROUTE_QUALIFIED',drivers=len(groups),driver_units=sum(map(len,groups.values())),endpoints=len(ep),core_inputs=sum(e['kind']=='native_core_clock' for e in ep),mesh_via89=len(mesh['vias']),all_graph_vias=graph['vias'],components=graph['connected_components'],max_endpoint_jog_um=max((t['jog_um'] for t in graph['taps']),default=0.),jog_policy=('pg_aware_m8_track' if x.plan else 'nearest_conductor'),stub_um_max=max((t.get('stub_um',0.) for t in graph['taps']),default=0.),stubs_nonzero=sum(1 for t in graph['taps'] if t.get('stub_um',0.)>1e-6),stub_by_kind={k:sum(1 for t in graph['taps'] if t.get('stub_um',0.)>1e-6 and t['endpoint_kind']==k) for k in ('native_core_clock','published_grid_clock')},errors=errors,scope='fixed mesh preparation; downstream FT arc/local wires and extraction not signed')
    for name,data in [('mesh_spec',mesh),('endpoint_bindings',mapping),('attachment_receipt',receipt)]: (o/(name+'.json')).write_text(json.dumps(data,indent=1)+'\n')
    if errors:print(json.dumps(receipt));return 2
    cells,nets,ports,out=E.attach_mesh(dict(mesh=mesh),cells,ns['nets'],ns['ports'],out)
    D.write_verilog(cells,nets,ports,o/'ctree.v')
    pd={t['port']:dict(layer=t.get('layer','M8'),xy=t['xy']) for t in out['taps']};pd['root']=dict(layer='M9',xy=out['meta']['root_um'])
    lines,rec=C.routed_tcl(out['fixed_wires'],cells,pd,D.BUF,'ot_mesh_ndr')
    (o/'clock_routed.tcl').write_text('\n'.join(lines)+'\n');(o/'encoder_receipt.json').write_text(json.dumps(rec)+'\n')
    (o/'native_mesh_diagnostic.spef').write_text(E.native_spef(out['fixed_wires'],cells,D.BUF,D.NDR['8w'],DC.LAYER_RC,DC.VIA_KOHM))
    for name,data in [('place',cells),('nets',dict(nets=nets,ports=ports)),('mesh',out)]: (o/(name+'.json')).write_text(json.dumps(data)+'\n')
    print(json.dumps(receipt));return 0
if __name__=='__main__':sys.exit(main())
