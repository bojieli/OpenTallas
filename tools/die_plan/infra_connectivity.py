#!/usr/bin/env python3
"""Actual OpenDB metal/via/terminal connectivity census; run with openroad -python.

Native via routing-layer enclosures form one 3D node.  ITerm.getGeometries()
provides the actual transformed pin shapes, including mirrored/rotated cells.
No guide, obstruction, timing or physical-freeze interpretation is involved.
"""
import argparse
import bisect
import heapq
from collections import defaultdict
import json
from pathlib import Path
import odb


def box(rect):
    return tuple(getattr(rect, name)() for name in ('xMin','yMin','xMax','yMax'))


def via_shapes(via, xy):
    x,y=xy
    return [(v.getTechLayer().getName(),(v.xMin()+x,v.yMin()+y,v.xMax()+x,v.yMax()+y))
            for v in via.getBoxes() if v.getTechLayer().getRoutingLevel()>0]


def net_nodes(net):
    nodes=[]
    for wire in net.getSWires():
        for shape in wire.getWires():
            if shape.isVia():
                via=shape.getTechVia() or shape.getBlockVia()
                nodes.append(('via:'+via.getName(),via_shapes(via,shape.getViaXY())))
            elif shape.getTechLayer().getRoutingLevel()>0:
                nodes.append(('segment',[(shape.getTechLayer().getName(),box(shape))]))
    if net.getWire():
        iterator=odb.dbWirePathItr();iterator.begin(net.getWire())
        path,entry=odb.dbWirePath(),odb.dbWirePathShape()
        while iterator.getNextPath(path):
            while iterator.getNextShape(entry):
                shape=entry.shape
                if shape.isVia():
                    via=shape.getTechVia() or shape.getVia()
                    nodes.append(('via:'+via.getName(),via_shapes(via,shape.getViaXY())))
                elif shape.getTechLayer() and shape.getTechLayer().getRoutingLevel()>0:
                    nodes.append(('segment',[(shape.getTechLayer().getName(),box(shape.getBox()))]))
    route_count=len(nodes)
    for term in net.getITerms():
        shapes=[(layer.getName(),box(rect)) for layer,rect in term.getGeometries()
                if layer.getRoutingLevel()>0]
        nodes.append(('terminal:'+term.getInst().getName()+'.'+term.getMTerm().getName(),shapes))
    for term in net.getBTerms():
        shapes=[(r.getTechLayer().getName(),box(r)) for pin in term.getBPins()
                for r in pin.getBoxes() if r.getTechLayer().getRoutingLevel()>0]
        nodes.append(('terminal:PORT/'+term.getName(),shapes))
    return nodes,route_count


def overlaps(rectangles):
    """Exact x sweep with a dynamic y-interval index, O(n log n + contacts).

    Full-die PG stripes can all span the same x coordinate. Scanning every
    active stripe per via is quadratic; the segment tree prunes y-disjoint
    shapes without rasterizing, expanding, or dropping physical contacts.
    """
    by_layer=defaultdict(list)
    for layer,rect,index in rectangles:
        by_layer[layer].append((rect,index))
    for layer,rows in by_layer.items():
        order=sorted(range(len(rows)),key=lambda i:rows[i][0][1])
        ys=[rows[i][0][1] for i in order]
        positions={i:j for j,i in enumerate(order)}
        size=1
        while size<len(rows):size*=2
        tree=[-(1<<63)]*(2*size)
        def update(position,value):
            position+=size;tree[position]=value
            while position>1:
                position//=2;tree[position]=max(tree[2*position],tree[2*position+1])
        expiry=[]
        for i in sorted(range(len(rows)),key=lambda i:rows[i][0][0]):
            rect,index=rows[i]
            while expiry and expiry[0][0]<rect[0]:
                _end,old=heapq.heappop(expiry);update(positions[old],-(1<<63))
            limit=bisect.bisect_right(ys,rect[3])
            stack=[(1,0,size)]
            while stack:
                node,lo,hi=stack.pop()
                if lo>=limit or tree[node]<rect[1]:continue
                if hi-lo==1:
                    other,j=rows[order[lo]]
                    if j!=index:yield layer,index,j
                else:
                    mid=(lo+hi)//2
                    stack.extend(((2*node,lo,mid),(2*node+1,mid,hi)))
            update(positions[i],rect[3]);heapq.heappush(expiry,(rect[2],i))


def check_database(path,names):
    if not names or len(set(names))!=len(names):
        raise ValueError('explicit unique infrastructure net names required')
    db=odb.dbDatabase.create();odb.read_db(db,str(path));block=db.getChip().getBlock()
    results,failures,all_rects,owner={},{},[],{}
    for name in names:
        net=block.findNet(name)
        if not net:
            failures[name]=['net missing'];continue
        nodes,routes=net_nodes(net);parent=list(range(len(nodes)))
        def find(i):
            while parent[i]!=i:
                parent[i]=parent[parent[i]];i=parent[i]
            return i
        rects=[(layer,rect,i) for i,(_label,shapes) in enumerate(nodes) for layer,rect in shapes]
        for _layer,i,j in overlaps(rects):parent[find(i)]=find(j)
        groups=defaultdict(list)
        for i,(label,_shapes) in enumerate(nodes):groups[find(i)].append(label)
        bad=[]
        if routes==0:bad.append('no actual wire/via geometry')
        if len(nodes)-routes<2:bad.append('fewer than two physical terminals')
        if any(not shapes for _label,shapes in nodes):bad.append('terminal or route lacks routing-layer geometry')
        if len(groups)!=1:bad.append(f'{len(groups)} disconnected physical components')
        result=dict(verdict='FAIL' if bad else 'CONNECTED',route_objects=routes,terminals=len(nodes)-routes,
                    physical_3d_components=len(groups),errors=bad)
        if bad:result['components']=[labels for labels in groups.values()]
        results[name]=result
        if bad:failures[name]=bad
        offset=len(owner)
        for i in range(len(nodes)):owner[offset+i]=name
        all_rects.extend((layer,rect,offset+i) for layer,rect,i in rects)
    shorts=[]
    for layer,i,j in overlaps(all_rects):
        if owner[i]!=owner[j]:
            entry=(owner[i],owner[j],layer)
            if entry not in shorts:shorts.append(entry)
    return dict(schema='opentallas.infra_connectivity.v1',database=str(path),
                verdict='FAIL' if failures or shorts else 'CONNECTED',nets=results,
                failures=failures,cross_net_overlaps=shorts,
                freeze_qualified=False,note='Actual routing-layer metal/via and transformed terminal geometry only; no DRC/timing/IR qualification')


def check_basic_clearance(path,names,clock_mesh_names=(),mesh_spacing_um=.08):
    """Check actual fixed metal against nominal tech/NDR spacing, including
    native via enclosures. This supplements DRT, which can skip fixed-vs-fixed
    checks. It is conservative rectangle spacing, not a full foundry DRC deck.
    """
    db=odb.dbDatabase.create();odb.read_db(db,str(path));block=db.getChip().getBlock();dbu=block.getDbUnitsPerMicron()
    shapes=[];rows=[];mesh=set(clock_mesh_names)
    for name in names:
        net=block.findNet(name)
        if not net:raise ValueError('clearance net missing: '+name)
        rule=net.getNonDefaultRule()
        nodes,_=net_nodes(net)
        for _label,parts in nodes:
            for layer_name,rect in parts:
                layer=db.getTech().findLayer(layer_name);spacing=layer.getSpacing()
                lr=rule.getLayerRule(layer) if rule else None
                if lr:spacing=max(spacing,lr.getSpacing())
                if name in mesh and layer_name in ('M8','M9'):spacing=max(spacing,round(mesh_spacing_um*dbu))
                index=len(shapes);shapes.append((name,layer_name,rect,spacing))
                rows.append((layer_name,rect,2*index))
                # Coordinates are integer DBU. Exactly-at-minimum spacing is
                # legal; expanding by spacing-1 detects strictly smaller gaps.
                d=max(0,spacing-1);a,b,c,e=rect
                rows.append((layer_name,(a-d,b-d,c+d,e+d),2*index+1))
    violations=[];seen=set()
    for layer,i,j in overlaps(rows):
        if (i%2)==(j%2):continue
        a,b=shapes[i//2],shapes[j//2]
        if a[0]==b[0]:continue
        key=tuple(sorted((i//2,j//2)))
        if key in seen:continue
        seen.add(key)
        required=max(a[3],b[3]);r,t=a[2],b[2]
        dx=max(r[0]-t[2],t[0]-r[2],0);dy=max(r[1]-t[3],t[1]-r[3],0)
        if dx<required and dy<required:
            violations.append(dict(nets=[a[0],b[0]],layer=layer,rectangles_dbu=[r,t],
                                   required_spacing_dbu=required,actual_gap_dbu=[dx,dy]))
    return dict(schema='opentallas.infra_basic_clearance.v1',verdict='FAIL' if violations else 'PASS',
                violations=violations,actual_rectangles=len(shapes),mesh_spacing_um=mesh_spacing_um,
                note='Actual metal/via nominal technology/NDR rectangular clearance; full DRC/timing/IR remain separate')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',required=True);p.add_argument('--nets',nargs='+',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();result=check_database(a.db,a.nets)
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
    print('INFRA_CONNECTIVITY',result['verdict'],result['failures'],result['cross_net_overlaps'])
    raise SystemExit(0 if result['verdict']=='CONNECTED' else 1)


if __name__=='__main__':main()
