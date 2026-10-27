"""Attach actual HEAD clock endpoints to the declared continuous metal mesh.

Additive preparation only: emits explicit dbWire Tcl/native diagnostic RC.  Driver
risers are bounded by the existing 2.5um island rule.  Endpoint jogs remain actual
metal, with source names retained; neither a provider nor signoff is invented.
"""
import argparse, copy, json, sys
from pathlib import Path

def main():
    a=argparse.ArgumentParser(); a.add_argument('--tools',required=True);a.add_argument('--build',required=True);a.add_argument('--straps',required=True);a.add_argument('--endpoints',required=True);a.add_argument('--out',required=True);a.add_argument('--tap-reach',type=float,default=450.);x=a.parse_args()
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
    for i,e in enumerate(ep):
        core=e['kind']=='native_core_clock';p=e['mesh_input'] if core else e
        xy=p['die_xy_um'];port=p['port'];mesh['taps'].append(dict(xy=xy,part=e['part'],endpoint_port=port,endpoint_kind=e['kind']))
        cand=[abs(h['y']-xy[1]) for h in mesh['M8'] if h['x0']<=xy[0]<=h['x1']] + [abs(v['x']-xy[0]) for v in mesh['M9'] if v['y0']<=xy[1]<=v['y1']]
        reach=min(cand,default=float('inf'))
        if reach>x.tap_reach+1e-6:errors.append(dict(kind='endpoint_off_mesh_reach',part=e['part'],port=port,xy=xy,nearest_projected_um=reach))
        mapping.append(dict(mesh_port=f'msh_t_{i}',part=e['part'],port=port,xy=xy,functional_port=e['port'] if core else None))
    # Conductor graph itself validates complete crossing/via inventory and connectivity.
    graphmesh=copy.deepcopy(mesh)
    if any(z['kind']=='endpoint_off_mesh_reach' for z in errors):graphmesh['taps']=[]
    graph=E.conductor_graph(graphmesh)
    receipt=dict(status='BLOCKED_ATTACHMENT_GEOMETRY' if errors else 'PREPARED_NOT_ROUTE_QUALIFIED',drivers=len(groups),driver_units=sum(map(len,groups.values())),endpoints=len(ep),core_inputs=sum(e['kind']=='native_core_clock' for e in ep),mesh_via89=len(mesh['vias']),all_graph_vias=graph['vias'],components=graph['connected_components'],max_endpoint_jog_um=max((t['jog_um'] for t in graph['taps']),default=0.),errors=errors,scope='fixed mesh preparation; downstream FT arc/local wires and extraction not signed')
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
