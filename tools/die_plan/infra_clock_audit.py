#!/usr/bin/env python3
"""Audit decoded clock metal against spine layers and explicit endpoint islands.

Access regions come from the reviewed placement contract, never from routed
wire extents. JSON fields cells/terminals/ports map exact names to rect_um (or a
four-number rectangle), in microns. A cells entry is for a standard clock cell;
macro pins require terminal entries, so a whole tile is not an access waiver.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))


def contains(outer,inner):
    return outer[0]<=inner[0] and outer[1]<=inner[1] and outer[2]>=inner[2] and outer[3]>=inner[3]


def region_value(value,dbu):
    value=value.get('rect_um') if isinstance(value,dict) else value
    if not isinstance(value,list) or len(value)!=4:
        raise ValueError('access region must be an explicit four-number rect_um')
    result=tuple(round(float(x)*dbu) for x in value)
    if result[0]>=result[2] or result[1]>=result[3]:raise ValueError('empty access region')
    return result


def audit_block(block,clock_names,clock_layers,regions):
    import odb
    from infra_replay import route_shapes
    if not clock_names or len(set(clock_names))!=len(clock_names):
        raise ValueError('explicit unique clock-net inventory required')
    dbu=block.getDbUnitsPerMicron();tech=block.getDb().getTech()
    endpoints=[tech.findLayer(n) for n in clock_layers.split('-')]
    if len(endpoints)!=2 or any(not x for x in endpoints):raise ValueError('invalid clock layer range')
    lo,hi=sorted(x.getRoutingLevel() for x in endpoints)
    cells=regions.get('cells',{});terms=regions.get('terminals',{});ports=regions.get('ports',{})
    results={};failures=[]
    for name in clock_names:
        net=block.findNet(name)
        if not net:raise ValueError('clock net missing: '+name)
        if str(net.getSigType()) in ('POWER','GROUND'):raise ValueError('power net in clock inventory: '+name)
        allowed=[];endpoint_labels=[]
        for term in net.getITerms():
            inst=term.getInst();label=inst.getName()+'/'+term.getMTerm().getName()
            value=terms.get(label)
            if value is None and inst.getName() in cells:
                if not str(inst.getMaster().getType()).startswith('CORE'):
                    raise ValueError('macro requires pin-specific access region: '+label)
                value=cells[inst.getName()]
            pin_shapes=[(r.xMin(),r.yMin(),r.xMax(),r.yMax()) for layer,r in term.getGeometries()
                        if layer.getRoutingLevel()>0]
            if value is not None:
                region=region_value(value,dbu)
                if not all(contains(region,r) for r in pin_shapes):
                    raise ValueError('declared access region does not contain actual transformed pin: '+label)
                allowed.append(region);endpoint_labels.append(label)
            else:
                # An undeclared endpoint has only its real metal shapes, not a
                # guessed halo, tile-sized box, or generic low-metal corridor.
                allowed.extend(pin_shapes);endpoint_labels.append(label+' (native pin only)')
        for term in net.getBTerms():
            label='PORT/'+term.getName();value=terms.get(label,ports.get(term.getName()))
            pin_shapes=[(r.xMin(),r.yMin(),r.xMax(),r.yMax()) for p in term.getBPins() for r in p.getBoxes()]
            if value is not None:
                region=region_value(value,dbu)
                if not all(contains(region,r) for r in pin_shapes):
                    raise ValueError('port access region misses actual pin: '+label)
                allowed.append(region)
            else:allowed.extend(pin_shapes)
            endpoint_labels.append(label)
        lengths=defaultdict(int);segments=0
        if net.getWire():
            iterator=odb.dbWirePathItr();iterator.begin(net.getWire());path,item=odb.dbWirePath(),odb.dbWirePathShape()
            while iterator.getNextPath(path):
                previous=(path.point.x(),path.point.y())
                while iterator.getNextShape(item):
                    shape=item.shape
                    if shape.isVia():
                        previous=tuple(shape.getViaXY())
                    else:
                        endpoint=(item.point.x(),item.point.y())
                        # getLength() measures the metal rectangle and can lose
                        # explicit zero-endcap distance at BTerms. Native path
                        # points retain the exact decoded centerline endpoints.
                        lengths[shape.getTechLayer().getName()]+=abs(endpoint[0]-previous[0])+abs(endpoint[1]-previous[1])
                        previous=endpoint;segments+=1
        below=0
        for layer,rect,kind in route_shapes(net):
            level=layer.getRoutingLevel()
            if level>hi:
                failures.append(dict(net=name,layer=layer.getName(),kind=kind,rect_dbu=list(rect),reason='above clock spine range'))
            elif level<lo:
                below+=1
                if not any(contains(region,rect) for region in allowed):
                    failures.append(dict(net=name,layer=layer.getName(),kind=kind,rect_dbu=list(rect),
                                         reason='outside explicit own-endpoint access islands/pins'))
        results[name]=dict(regular_segments=segments,decoded_centerline_length_um={k:v/dbu for k,v in lengths.items()},
                           lower_layer_shapes=below,access_endpoints=endpoint_labels)
    return dict(schema='opentallas.infra_clock_audit.v1',verdict='FAIL' if failures else 'PASS',
                clock_layers=clock_layers,nets=results,violations=failures,freeze_qualified=False,
                note='Decoded actual clock metal; lower layers only in explicit own-endpoint placement islands/native pins')


def main():
    from infra_replay import load_db
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',required=True);p.add_argument('--clock-nets',required=True)
    p.add_argument('--access-regions',required=True);p.add_argument('--clock-layers',default='M8-M9');p.add_argument('--out',required=True)
    a=p.parse_args();_db,block=load_db(a.db)
    result=audit_block(block,Path(a.clock_nets).read_text().split(),a.clock_layers,json.loads(Path(a.access_regions).read_text()))
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
    print('INFRA_CLOCK_AUDIT',result['verdict'],len(result['violations']),'violations')
    raise SystemExit(0 if result['verdict']=='PASS' else 1)


if __name__=='__main__':main()
