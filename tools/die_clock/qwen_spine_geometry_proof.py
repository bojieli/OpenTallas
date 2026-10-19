#!/usr/bin/env python3
"""Independently audit a completed exact-bay geometry ODB; no timing waiver."""
import argparse
from bisect import bisect_left,bisect_right
from collections import defaultdict,Counter
import hashlib
import json
from pathlib import Path


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def overlaps(a,b):
    return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]


def propose_rows(block,names,u):
    """Readonly row/rail requirements. No dbRow/PDN mutation or approval."""
    hard=[];wanted=defaultdict(list);existing=defaultdict(list)
    for obj in block.getInsts():
        q=obj.getBBox();r=(q.xMin(),q.yMin(),q.xMax(),q.yMax())
        if obj.getMaster().isBlock():hard.append(r)
        if obj.getName() in names:wanted[r[1]].append((obj.getName(),r))
    for row in block.getRows():
        q=row.getBBox();existing[q.yMin()].append((row.getName(),(q.xMin(),q.yMin(),q.xMax(),q.yMax())))
    die=block.getDieArea();site=round(.054*u);height=round(.27*u)
    needed={y:[(n,r) for n,r in cells if not any(q[0]<=r[0] and q[2]>=r[2] and q[3]>=r[3] for _,q in existing[y])]
            for y,cells in wanted.items()}
    needed={y:cells for y,cells in needed.items() if cells}
    ys=sorted(needed);hard_by_y=defaultdict(list)
    for r in hard:
        lo=bisect_right(ys,r[1]-height);hi=bisect_left(ys,r[3])
        for y in ys[lo:hi]:hard_by_y[y].append((max(die.xMin(),r[0]),min(die.xMax(),r[2])))
    proposed={};uncovered=[]
    for y,need in needed.items():
        intervals=sorted(hard_by_y[y])
        merged=[]
        for lo,hi in intervals:
            if merged and lo<=merged[-1][1]:merged[-1][1]=max(hi,merged[-1][1])
            else:merged.append([lo,hi])
        left=die.xMin();free=[]
        for lo,hi in merged+[[die.xMax(),die.xMax()]]:
            lo_site=((left+site-1)//site)*site;hi_site=(lo//site)*site
            if hi_site>lo_site:free.append((lo_site,hi_site))
            left=max(left,hi)
        for name,r in need:
            fits=[(lo,hi) for lo,hi in free if lo<=r[0] and hi>=r[2]]
            if len(fits)!=1:uncovered.append(name);continue
            lo,hi=fits[0];key=(y,lo,hi)
            if key not in proposed:
                proposed[key]=dict(y_um=y/u,x0_um=lo/u,x1_um=hi/u,site_width_um=site/u,
                                   site_count=(hi-lo)//site,orientation='R0' if (y//height)%2==0 else 'MX',
                                   supersedes_existing_rows=[n for n,q in existing[y] if q[0]<hi and q[2]>lo],
                                   new_clock_cells=[])
            proposed[key]['new_clock_cells'].append(name)
    rows=list(proposed.values())
    return dict(schema='opentallas.qwen.clock_corridor_row_requirements.v1',
                readonly_proposal=True,rows=rows,new_row_segments=len(rows),
                horizontal_rail_length_um=sum(r['x1_um']-r['x0_um'] for r in rows),
                row_area_mm2=sum((r['x1_um']-r['x0_um'])*height/u for r in rows)/1e6,
                proposed_new_clock_cells=sum(len(r['new_clock_cells']) for r in rows),
                clock_cells_without_hard_free_row_segment=uncovered,
                remaining=['ROOT approval of top clock-corridor row/rail/PDN integration',
                           'Generate actual physical rows and power rails; verify continuity to top PDN',
                           'Reaudit all overlaps/sites/reach and sign off clock timing'],
                physical_rows_created=False,power_qualified=False,timing_qualified=False)


def audit(odb_path,manifest_path,tool_source,row_plan=None,regional_only=False):
    from openroad import Tech,Design
    tech=Tech();design=Design(tech);design.readDb(odb_path)
    block=design.getBlock();u=block.getDbUnitsPerMicron()
    m=json.loads(Path(manifest_path).read_text());sp={} if regional_only else m['spine']
    errors=[];names={n for n,t in m['cell_tree'].items() if t=='spine'}
    if not regional_only and not m.get('geometry_only'):errors.append('not a geometry-only replay')
    if not regional_only and not m['spec']['spine'].get('exact_footprint_bays'):errors.append('not exact footprint topology')
    boxes={};fixed={};grid=defaultdict(list);pitch=round(100*u)
    rows_by_y=defaultdict(list)
    for row in block.getRows():
        q=row.getBBox();rows_by_y[q.yMin()].append((q.xMin(),q.yMin(),q.xMax(),q.yMax()))
    for inst in block.getInsts():
        if not (inst.getMaster().isBlock() or inst.isPlaced()):continue
        q=inst.getBBox();r=(q.xMin(),q.yMin(),q.xMax(),q.yMax());n=inst.getName()
        (boxes if n in names else fixed)[n]=r
        for x in range(r[0]//pitch,(r[2]-1)//pitch+1):
            for y in range(r[1]//pitch,(r[3]-1)//pitch+1):grid[x,y].append(n)
    if names-set(boxes):errors.append('missing placed spine cells: '+str(sorted(names-set(boxes))))
    hits=set();off_rows=[]
    for n,r in boxes.items():
        for x in range(r[0]//pitch,(r[2]-1)//pitch+1):
            for y in range(r[1]//pitch,(r[3]-1)//pitch+1):
                for other in grid[x,y]:
                    if other==n:continue
                    rr=boxes.get(other,fixed.get(other))
                    if overlaps(r,rr):hits.add(tuple(sorted((n,other))))
        if r[2]-r[0]>round(1.62*u) or r[3]-r[1]>round(.27*u):errors.append('spine footprint exceeds reserved site: '+n)
        if not any(q[0]<=r[0] and q[2]>=r[2] and q[3]>=r[3] for q in rows_by_y[r[1]]):off_rows.append(n)
    if hits:errors.append('actual placed footprint overlaps: '+str(len(hits)))
    if off_rows:errors.append('actual spine cells without a containing physical placement row: '+str(len(off_rows)))
    all_clock_off_rows=[]
    all_clock_hits=set()
    for name,*_ in m['cells']:
        r=boxes.get(name,fixed.get(name))
        if r is None or not any(q[0]<=r[0] and q[2]>=r[2] and q[3]>=r[3] for q in rows_by_y[r[1]]):
            all_clock_off_rows.append(name)
        if r is not None:
            for x in range(r[0]//pitch,(r[2]-1)//pitch+1):
                for y in range(r[1]//pitch,(r[3]-1)//pitch+1):
                    for other in grid[x,y]:
                        if other!=name and overlaps(r,boxes.get(other,fixed.get(other))):
                            all_clock_hits.add(tuple(sorted((name,other))))
    if all_clock_hits:errors.append('all-clock actual footprint overlaps: '+str(len(all_clock_hits)))
    if regional_only and all_clock_off_rows:errors.append('regional clock cells without physical rows: '+str(len(all_clock_off_rows)))
    regional_long=[];max_regional_direct=0.0;max_regional_fanout=0
    for name,*_ in m['cells']:
        if name in names:continue
        inst=block.findInst(name);output=inst.findITerm('Y') if inst else None
        if output is None or output.getNet() is None:continue
        max_regional_fanout=max(max_regional_fanout,sum(p.getIoType()=='INPUT' for p in output.getNet().getITerms()))
        q=output.getBBox();xy=((q.xMin()+q.xMax())/2/u,(q.yMin()+q.yMax())/2/u)
        for sink in output.getNet().getITerms():
            if sink.getIoType()!='INPUT':continue
            q=sink.getBBox();dest=((q.xMin()+q.xMax())/2/u,(q.yMin()+q.yMax())/2/u)
            distance=sum(abs(xy[i]-dest[i]) for i in (0,1))
            max_regional_direct=max(max_regional_direct,distance)
            if distance>405+1e-7:
                regional_long.append(dict(source=name+'/Y',sink=sink.getInst().getName()+'/'+sink.getMTerm().getName(),
                                          direct_distance_um=distance))
    source=sp.get('source');sbn='dc_spine_src'
    def iterm(ref,output):
        kind,n=ref
        pn=(sbn+'/Y' if n==source else n) if kind=='pin' else n+('/Y' if output else '/A')
        p=block.findITerm(pn)
        if p is None:raise ValueError('missing physical endpoint '+pn)
        q=p.getBBox();xy=((q.xMin()+q.xMax())/2/u,(q.yMin()+q.yMax())/2/u)
        return p,pn,xy
    delivered=[];reaches=[];fanouts={};edge_count=0
    for e in sp.get('exact_bay_edges',[]):
        a,an,axy=iterm(e['driver'],True);b,bn,bxy=iterm(e['load'],False)
        net=a.getNet()
        if net is None or b.getNet()!=net:errors.append('physical edge disconnected: '+an+' -> '+bn)
        if net is not None:
            fanouts[net.getName()]=sum(p.getIoType()=='INPUT' for p in net.getITerms())
        path=e['route_cells']
        if any(abs(a[0]-b[0])+abs(a[1]-b[1])!=1 for a,b in zip(path,path[1:])):
            errors.append('nonadjacent declared route cells: '+an+' -> '+bn)
        polyline=[axy]+[tuple((v+.5)*10 for v in c) for c in path[1:-1]]+[bxy]
        length=sum(sum(abs(a[i]-b[i]) for i in (0,1)) for a,b in zip(polyline,polyline[1:]))
        reaches.append(length);edge_count+=1
        if length>405+1e-7:errors.append(f'actual placed routed reach {length:.6f}>405: {an}->{bn}')
        if e.get('placed_pin_routed_bound_um') is None or abs(length-e['placed_pin_routed_bound_um'])>1e-6:
            errors.append('placed pin receipt missing/changed: '+an+' -> '+bn)
        if e['load'][0]=='pin':delivered.append(bn)
    expected=[m['root_buffer'][m['trees'][n]['root']]+'/A' for n in sp.get('members',[])]
    missing=sorted(set(expected)-set(delivered));extra=sorted(set(delivered)-set(expected))
    duplicates=sorted(n for n,c in Counter(delivered).items() if c!=1)
    if missing or extra or duplicates:errors.append('regional endpoint coverage missing/extra/duplicate')
    if max(fanouts.values(),default=0)>2:errors.append('actual spine fanout exceeds two')
    if not regional_only:
        gen=block.findITerm(source);entry=block.findITerm(sbn+'/A')
        if gen is None or entry is None or gen.getNet()!=entry.getNet():errors.append('generator entry disconnected')
        else:
            nload=sum(p.getIoType()=='INPUT' for p in gen.getNet().getITerms())
            if nload!=1:errors.append('generator must drive exactly one spine entry')
    if regional_only and regional_long:errors.append('regional actual direct wires exceed405: '+str(len(regional_long)))
    if row_plan:
        rp=propose_rows(block,{c[0] for c in m['cells']},u)
        rp.update(odb_sha256=sha(odb_path),manifest_sha256=sha(manifest_path))
        Path(row_plan).write_text(json.dumps(rp,indent=1)+'\n')
    return dict(schema='opentallas.qwen.regional_checkpoint_geometry.v1' if regional_only else 'opentallas.qwen.full_spine_geometry_proof.v1',tool_source=tool_source,
                auditor_sha256=sha(__file__),
                odb_sha256=sha(odb_path),manifest_sha256=sha(manifest_path),
                source_generator=source,all_clock_cells=len(m['cells']),spine_cells=len(boxes),
                regional_clock_cells=len(m['cells'])-len(boxes),regional_trees=len(m['trees']),
                required_spine_endpoints=len(expected),delivered_endpoints=len(delivered),
                endpoint_missing=missing,endpoint_extra=extra,endpoint_duplicates=duplicates,
                fixed_obstacles=len(fixed),overlap_count=len(hits),overlap_examples=sorted(hits)[:100],
                all_clock_overlap_count=len(all_clock_hits),all_clock_overlap_examples=sorted(all_clock_hits)[:100],
                physical_rows=len(block.getRows()),off_row_count=len(off_rows),off_row_examples=off_rows[:100],
                all_new_clock_cells_off_row=len(all_clock_off_rows),all_new_clock_off_row_examples=all_clock_off_rows[:100],
                regional_direct_distance_gt405_count=len(regional_long),
                max_regional_actual_direct_um=max_regional_direct,max_regional_actual_fanout=max_regional_fanout,
                regional_direct_distance_gt405_examples=sorted(regional_long,key=lambda r:-r['direct_distance_um'])[:100],
                native_regional_geometry_qualified=False,
                routed_stage_count=edge_count,max_actual_placed_routed_bound_um=max(reaches,default=0),
                generator_entry_routed_bound_um=sp.get('source_input_routed_bound_um'),
                max_actual_spine_fanout=max(fanouts.values(),default=0),errors=errors,
                geometry_pass=not errors,full_spine_proven=not regional_only and not errors,
                timing_qualified=False,production_admitted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('odb','manifest','tool-source','out'):p.add_argument('--'+arg,required=True)
    p.add_argument('--row-plan-out')
    p.add_argument('--regional-only',action='store_true',help='audit actual checkpoint only; never assert full-spine coverage')
    a=p.parse_args();r=audit(a.odb,a.manifest,a.tool_source,a.row_plan_out,a.regional_only)
    Path(a.out).write_text(json.dumps(r,indent=1)+'\n')
    print(json.dumps(r,indent=1),flush=True)
    raise SystemExit(0 if r['geometry_pass'] else 1)
