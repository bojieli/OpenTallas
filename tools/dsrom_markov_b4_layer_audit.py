#!/usr/bin/env python3
"""Read-only OpenDB J7 audit. Run with OpenROAD -python, args after --.

Count routed PATH layers and all routing-metal via enclosures, separating power
and ground from signal/clock routes. Any M7+ signal/clock geometry blocks the
same-M2-M6 claim, including a via landing without a nonzero M7 segment.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


def main():
    import odb
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--odb', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    database = odb.dbDatabase.create()
    odb.read_db(database, a.odb)
    block = database.getChip().getBlock()
    paths, via_metals, special_metals = Counter(), Counter(), Counter()
    upper_nets = []
    routed_nets = 0
    for net in block.getNets():
        if str(net.getSigType()) in ('POWER', 'GROUND'):
            for sw in net.getSWires():
                for box in sw.getWires():
                    if box.isVia():
                        via = box.getTechVia() or box.getBlockVia()
                        layers = [g.getTechLayer() for g in via.getBoxes()] if via else []
                    else:
                        layers = [box.getTechLayer()]
                    for layer in layers:
                        if layer and layer.getRoutingLevel() > 0:
                            special_metals[layer.getName()] += 1
            continue
        wire = net.getWire()
        if not wire:
            continue
        routed_nets += 1
        upper = set()
        decoder = odb.dbWireDecoder()
        decoder.begin(wire)
        while True:
            op = decoder.next()
            if op == odb.dbWireDecoder.END_DECODE:
                break
            if op == odb.dbWireDecoder.PATH:
                layer = decoder.getLayer()
                paths[layer.getName()] += 1
                if layer.getRoutingLevel() > 6:
                    upper.add(layer.getName())
            elif op in (odb.dbWireDecoder.TECH_VIA, odb.dbWireDecoder.VIA):
                via = decoder.getTechVia() if op == odb.dbWireDecoder.TECH_VIA else decoder.getVia()
                for geom in via.getBoxes():
                    layer = geom.getTechLayer()
                    if layer.getRoutingLevel() > 0:
                        via_metals[layer.getName()] += 1
                        if layer.getRoutingLevel() > 6:
                            upper.add(layer.getName())
        if upper:
            upper_nets.append(dict(net=net.getName(), type=str(net.getSigType()), layers=sorted(upper)))
    masters = Counter(inst.getMaster().getName() for inst in block.getInsts())
    units = block.getDbUnitsPerMicron()
    area = sum(inst.getMaster().getWidth() * inst.getMaster().getHeight() for inst in block.getInsts()) / units**2
    result = dict(schema='opentallas.markov.b4.used-layer-audit.v1',
        odb_sha256=hashlib.sha256(Path(a.odb).read_bytes()).hexdigest(),
        source=a.odb, signal_and_clock_routed_nets=routed_nets,
        signal_and_clock_PATH_layers=dict(paths), signal_and_clock_via_metal_layers=dict(via_metals),
        power_ground_special_layers=dict(special_metals), above_M6_signal_and_clock_nets=upper_nets,
        same_M2_M6_upper_layer_qualification=not upper_nets,
        total_instances=sum(masters.values()), master_counts=dict(masters),
        sequential_instances=sum(v for k, v in masters.items() if 'DFF' in k),
        all_master_area_um2=area,
        scope='Physical read-only layer/inventory audit; timing, DRC and electrical checks remain separate.')
    Path(a.out).write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(dict(upper_nets=len(upper_nets), PATH_layers=dict(paths), sequential=result['sequential_instances'])))


if __name__ == '__main__':
    main()
