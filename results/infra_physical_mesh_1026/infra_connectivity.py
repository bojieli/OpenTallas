#!/usr/bin/env python3
"""Actual OpenDB metal/via/terminal connectivity census; run with openroad -python.

Native via routing-layer enclosures form one 3D node.  ITerm.getGeometries()
provides the actual transformed pin shapes, including mirrored/rotated cells.
No guide, obstruction, timing or physical-freeze interpretation is involved.
"""
import argparse
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
    """Sweep routing-layer rectangles; output touching node pairs without voxel rounding."""
    by_layer=defaultdict(list)
    for layer,rect,index in rectangles:
        by_layer[layer].append((rect,index))
    for layer,rows in by_layer.items():
        active=[]
        for rect,index in sorted(rows,key=lambda row:row[0][0]):
            active=[(other,j) for other,j in active if other[2]>=rect[0]]
            for other,j in active:
                if j!=index and other[1]<=rect[3] and rect[1]<=other[3]:
                    yield layer,index,j
            active.append((rect,index))


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


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',required=True);p.add_argument('--nets',nargs='+',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();result=check_database(a.db,a.nets)
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
    print('INFRA_CONNECTIVITY',result['verdict'],result['failures'],result['cross_net_overlaps'])
    raise SystemExit(0 if result['verdict']=='CONNECTED' else 1)


if __name__=='__main__':main()
