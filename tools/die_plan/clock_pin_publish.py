#!/usr/bin/env python3
"""Expose existing, physically connected root-clock metal as an additional pin.

OpenROAD Python only. No wires, vias, cells or original pin shapes are changed.
The requested layer must already contain routed clock metal connected through
native via enclosures to the original input pin AND every actual clock load.
Publication stays within the original pin's XY footprint. Parent pin access,
abstract export, clock timing and normal qualification remain required.
"""
import argparse
import hashlib
import json
from pathlib import Path


def rect(box):
    return (box.xMin(), box.yMin(), box.xMax(), box.yMax())


def intersection(a, b):
    result = (max(a[0], b[0]), max(a[1], b[1]),
              min(a[2], b[2]), min(a[3], b[3]))
    return result if result[0] < result[2] and result[1] < result[3] else None


def overlaps(a, b):
    return a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


def components(nodes, bonds):
    parent = list(range(len(nodes)))

    def root(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    def join(a, b):
        parent[root(a)] = root(b)

    for a, b in bonds:
        join(a, b)
    by_layer = {}
    for i, (layer, box) in enumerate(nodes):
        for j in by_layer.setdefault(layer, []):
            if overlaps(box, nodes[j][1]):
                join(i, j)
        by_layer[layer].append(i)
    return [root(i) for i in range(len(nodes))]


def wire_geometry(net):
    import odb
    wire = net.getWire()
    if wire is None:
        raise ValueError("clock has no existing regular routed wire")
    nodes, bonds, records, segments = [], [], [], []
    iterator = odb.dbWirePathItr()
    iterator.begin(wire)
    path, piece = odb.dbWirePath(), odb.dbWirePathShape()
    while iterator.getNextPath(path):
        while iterator.getNextShape(piece):
            shape = piece.shape
            if not shape.isVia():
                layer, box = shape.getTechLayer().getName(), rect(shape)
                segments.append(len(nodes))
                nodes.append((layer, box))
                records.append(("metal", layer, *box))
                continue
            via = shape.getTechVia() or shape.getVia()
            if via is None:
                raise ValueError("clock contains an unknown native via")
            x, y = shape.getViaXY()
            pieces = []
            for box in via.getBoxes():
                layer = box.getTechLayer()
                if str(layer.getType()) != "ROUTING":
                    continue
                a, b, c, d = rect(box)
                pieces.append(len(nodes))
                nodes.append((layer.getName(), (a+x, b+y, c+x, d+y)))
            if len(pieces) != 2:
                raise ValueError("clock via needs exactly two routing enclosures")
            bonds.append(tuple(pieces))
            records.append(("via", via.getName(), x, y))
    return nodes, bonds, records, segments


def candidates(nodes, bonds, segments, original, loads, layer, min_width):
    """Only real wire inside the original pin footprint, not a bounding-box guess."""
    nodes = list(nodes)
    source_ids = []
    for shape in original:
        source_ids.append(len(nodes))
        nodes.append(shape)
    load_ids = []
    for shapes in loads:
        if not shapes:
            raise ValueError("clock load has no physical pin geometry")
        ids = list(range(len(nodes), len(nodes) + len(shapes)))
        nodes.extend(shapes)
        load_ids.append(ids)
    roots = components(nodes, bonds)
    sources = {roots[i] for i in source_ids}
    connected = {r for r in sources if all(any(roots[i] == r for i in ids) for ids in load_ids)}
    if not connected:
        raise ValueError("original clock pin is not physically connected to every clock load")
    output = set()
    for i in segments:
        lay, box = nodes[i]
        if lay != layer or roots[i] not in connected:
            continue
        for _, port in original:
            cut = intersection(box, port)
            if cut and min(cut[2]-cut[0], cut[3]-cut[1]) >= min_width:
                output.add(cut)
    if not output:
        raise ValueError("no connected target-layer clock metal of legal width inside original pin footprint")
    return sorted(output)


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()


def publish(input_db, output_db, pin_name, layer_name, report=None):
    import odb
    source, output = Path(input_db), Path(output_db)
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError("output must be a fresh private database")
    if report and Path(report).exists():
        raise ValueError("report must be fresh")
    db = odb.dbDatabase.create()
    try:
        odb.read_db(db, str(source))
        block = db.getChip().getBlock()
        pin = block.findBTerm(pin_name)
        layer = db.getTech().findLayer(layer_name)
        if pin is None or pin.getNet() is None or str(pin.getIoType()) != "INPUT":
            raise ValueError("requires one existing input BTerm")
        net = pin.getNet()
        if str(net.getSigType()) != "CLOCK" or list(net.getBTerms()) != [pin]:
            raise ValueError("requires a CLOCK net with exactly its one input BTerm")
        if layer is None or str(layer.getType()) != "ROUTING":
            raise ValueError("target must be an actual routing layer")
        terms = list(net.getITerms())
        if not terms or any(str(term.getIoType()) != "INPUT" for term in terms):
            raise ValueError("root clock must have real input loads and no internal driver")
        original = [(box.getTechLayer().getName(), rect(box))
                    for p in pin.getBPins() for box in p.getBoxes()]
        if not original:
            raise ValueError("clock input has no original pin metal")
        nodes, bonds, records, segments = wire_geometry(net)
        loads = [[(l.getName(), rect(box)) for l, box in t.getGeometries()] for t in terms]
        chosen = candidates(nodes, bonds, segments, original, loads, layer_name, layer.getWidth())
        existing = {box for lay, box in original if lay == layer_name}
        missing = [box for box in chosen if not any(
            old[0] <= box[0] and old[1] <= box[1] and old[2] >= box[2] and old[3] >= box[3]
            for old in existing)]
        counts = (len(list(block.getInsts())), len(list(block.getNets())))
        if missing:
            published = odb.dbBPin_create(pin)
            published.setPlacementStatus("FIRM")
            for box in missing:
                odb.dbBox_create(published, layer, *box)
        after = wire_geometry(net)[2]
        if records != after or counts != (len(list(block.getInsts())), len(list(block.getNets()))):
            raise ValueError("pin publication changed existing clock wire or design inventory")
        final_shapes = {(box.getTechLayer().getName(), rect(box))
                        for p in pin.getBPins() for box in p.getBoxes()}
        if not set(original) <= final_shapes:
            raise ValueError("pin publication changed original pin geometry")
        result = dict(schema="opentallas.clock_pin_publish.v1", input_db=str(source),
                      output_db=str(output), pin=pin_name, net=net.getName(),
                      layer=layer_name, original_pin_shapes=original,
                      added_pin_rectangles=missing, connected_loads=len(terms),
                      actual_clock_geometry_sha256=digest(records), existing_wires_unchanged=True,
                      added_signal_cycles=0, parent_access_qualified=False,
                      qualification="requires actual abstract export, parent PA/DRC and clock timing")
        odb.write_db(db, str(output))
        if report:
            Path(report).write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        odb.dbDatabase.destroy(db)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_db")
    parser.add_argument("output_db")
    parser.add_argument("--pin", required=True)
    parser.add_argument("--layer", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()
    print(json.dumps(publish(args.input_db, args.output_db, args.pin, args.layer, args.report)))


if __name__ == "__main__":
    main()
