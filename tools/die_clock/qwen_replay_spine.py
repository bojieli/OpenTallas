#!/usr/bin/env python3
"""Replay the entire required spine on an immutable actual regional ODB.

Preserves all regional cells and native targets. Failed plans retain complete
partial station coordinates and the precise next-bay witness. No STA/admission.
"""
import argparse
import hashlib
import json
from pathlib import Path
import regtree as rt
from qwen_exact_corridor import ExactBayGrid,ExactForwardedBuilder,check_reach,routed_bound


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def main(a):
    import odb
    from openroad import Tech,Design
    tech=Tech();design=Design(tech);design.readDb(a.odb);block=design.getBlock();u=block.getDbUnitsPerMicron()
    rec=json.loads(Path(a.manifest).read_text());out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    sp=rec['spec']['spine'];source=sp['source'];source_pin=block.findITerm(source)
    if source_pin is None:raise ValueError('missing actual spine source')
    rows=[]
    for obj in block.getInsts():
        if obj.getMaster().isBlock() or obj.isPlaced():
            q=obj.getBBox();rows.append((obj.getName(),(q.xMin()/u,q.yMin()/u,q.xMax()/u,q.yMax()/u)))
    power_sites=None
    if rec['spec'].get('pg_safe_clock_bays',False):
        from qwen_clock_power_sites import ClockPowerSites
        power_sites=ClockPowerSites.from_block(block,odb,[design.getDb().findMaster(n) for n in (rt.BUF,rt.PAD)])
        # A PG-constrained spine cannot repair an already unsafe regional tree.
        bad=[n for n,_,x,y in rec['cells'] if not power_sites(x,y)]
        if bad:raise ValueError('regional clock sites violate actual PG model: '+str(bad[:20]))
        rows=power_sites.occupied_rows(block)
        rec['clock_power_site_model']=power_sites.identity()
    die=block.getDieArea();g=ExactBayGrid(die.xMax()/u,die.yMax()/u,rows,site_validator=power_sites)
    members=rt.spine_members(rec['spec']['trees'],set(rec['trees']),rec['root_buffer'],sp)
    cell_xy={c[0]:(c[2],c[3]) for c in rec['cells']};sbn='dc_spine_src'
    source_box=source_pin.getBBox();sxy=((source_box.xMin()+source_box.xMax())/2/u,(source_box.yMin()+source_box.yMax())/2/u)
    source_xy=g.reserve(g.nearest_free(*sxy))
    builder=ExactForwardedBuilder(g,'dc_spine')
    identity=dict(tool_source=a.tool_source,regional_odb_sha256=sha(a.odb),regional_manifest_sha256=sha(a.manifest),
                  planner_sha256=sha(Path(__file__).parent/'qwen_exact_corridor.py'))
    try:
        model=builder.build(source,source_xy,rt.spine_leaves(members,cell_xy))
    except (ValueError,SystemExit) as e:
        failure=dict(schema='opentallas.qwen.full_spine_plan_failure.v1',identity=identity,error=str(e),
                     required_endpoints=[rb+'/A' for _,rb in members],partial_stations=builder.bufs,
                     emitted_edges=builder.edges,failure=getattr(builder,'failure',None),
                     timing_qualified=False,production_admitted=False)
        (out/'plan_fail.json').write_text(json.dumps(failure,indent=1)+'\n')
        raise
    master=design.getDb().findMaster(rt.BUF)
    if master is None or master.getWidth()/u>1.62 or master.getHeight()/u>.27:raise ValueError('unsupported clock footprint')
    def create(n,cell,x,y):
        m=design.getDb().findMaster(cell);obj=odb.dbInst.create(block,m,n)
        obj.setOrient('R0' if round(y/.27)%2==0 else 'MX');obj.setLocation(round(x*u),round(y*u));obj.setPlacementStatus('PLACED')
        rec['cells'].append([n,cell,x,y]);rec['cell_tree'][n]='spine'
        return obj
    source_obj=create(sbn,rt.BUF,*source_xy)
    for n,cell,x,y in builder.bufs:create(n,cell,x,y)
    net=source_pin.getNet()
    if net is None:net=odb.dbNet.create(block,'n_dc_spine_gen');source_pin.connect(net)
    required_root_buffers={rb for _,rb in members}
    for pin in list(net.getITerms()):
        if pin.getIoType()=='INPUT':
            if pin.getInst().getName() not in required_root_buffers:
                raise ValueError('spine generator also drives nonmember '+pin.getInst().getName())
            pin.disconnect()
    source_obj.findITerm('A').connect(net)
    snet=odb.dbNet.create(block,'n_dc_spine_src');snet.setSigType('CLOCK');source_obj.findITerm('Y').connect(snet)
    def term(ref,output):
        kind,n=ref
        p=(sbn+'/Y' if n==source else n) if kind=='pin' else n+('/Y' if output else '/A')
        result=block.findITerm(p)
        if result is None:raise ValueError('missing actual planned endpoint '+p)
        return result
    for name,driver,loads in builder.nets:
        driver_pin=term(driver,True)
        n=snet if driver==('pin',source) else odb.dbNet.create(block,name)
        n.setSigType('CLOCK');driver_pin.connect(n)
        for ref in loads:
            pin=term(ref,False);pin.disconnect();pin.connect(n)
    def xy(pin):
        q=pin.getBBox();return ((q.xMin()+q.xMax())/2/u,(q.yMin()+q.yMax())/2/u)
    rec['geometry_only']=True;rec['timing_qualified']=False;rec['production_admitted']=False
    rec['spine_replay_identity']=identity
    rec['spine']=dict(source=source,topology='forwarded',period=sp['period'],members=[t['name'] for t,_ in members],
                     cells=len(builder.bufs)+1,model=model,exact_bay_edges=builder.edges,
                     source_input_routed_bound_um=None)
    try:
        for e in builder.edges:
            start,end=xy(term(e['driver'],True)),xy(term(e['load'],False))
            e['placed_pin_routed_bound_um']=routed_bound(e['route_cells'],start,end,g)
            check_reach(e['route_cells'],start,end,g)
        entry=xy(source_obj.findITerm('A'))
        source_reach=check_reach(g.route_reserved(g.cell(*sxy),g.cell(*entry)),sxy,entry,g)
    except ValueError:
        design.writeDb(str(out/'placed_reach_fail.odb'))
        (out/'placed_reach_fail.json').write_text(json.dumps(rec)+'\n')
        raise
    rec['spine']['source_input_routed_bound_um']=source_reach
    rec['parent'].update({(k[:-2] if k.endswith('/A') and k[:-2] in {rb for _,rb in members} else k):
                          (sbn if v==source else v) for k,v in builder.parent.items()})
    rec['parent'][sbn]=source
    (out/'geometry_manifest.json').write_text(json.dumps(rec)+'\n');design.writeDb(str(out/'geometry.odb'))
    print(json.dumps(dict(identity=identity,regional_clock_cells=len(rec['cells'])-len(builder.bufs)-1,
                         spine_cells=len(builder.bufs)+1,endpoints=len(members),model=model,
                         timing_qualified=False,production_admitted=False),indent=1),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('odb','manifest','tool-source','out'):p.add_argument('--'+arg,required=True)
    main(p.parse_args())
