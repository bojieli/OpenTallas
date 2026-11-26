#!/usr/bin/env python3
"""Extract exact signal-pin stacks from a signed OpenDB file.

Run with OpenROAD's Python frontend:
    openroad -exit -no_init -python pinstack_odb.py core.odb stack.json
The resulting mapping is accepted by abstract_exact.py form --pin-stack.
"""
import argparse
import json
import re
import tempfile
from collections import defaultdict
from pathlib import Path

ROUTING_LAYERS = {"M4", "M5", "M6", "M7"}
NET_NAME = re.compile(r"\s*-\s+(\S+)")
RECT_PATCH = re.compile(
    r"\b(?:ROUTED|NEW) (M[4-7]) \( (-?\d+) (-?\d+) \) "
    r"RECT \( (-?\d+) (-?\d+) (-?\d+) (-?\d+) \)"
)


def def_patches(lines, signal_nets):
    """Return RECT patches owned by each requested signal net in the DEF NETS section."""
    patches = defaultdict(list)
    in_nets = False
    net = None
    for line in lines:
        if not in_nets:
            in_nets = line.startswith("NETS ")
            continue
        if line.startswith("END NETS"):
            break
        name = NET_NAME.match(line)
        if name:
            net = re.sub(r"\\(.)", r"\1", name[1])
        if net not in signal_nets:
            continue
        match = RECT_PATCH.search(line)
        if not match:
            continue
        layer, *values = match.groups()
        x, y, dx0, dy0, dx1, dy1 = map(int, values)
        patches[net].append((layer, x + dx0, y + dy0, x + dx1, y + dy1))
    return patches


def layer_rect(layer, box, x=0, y=0):
    return (layer, x + box.xMin(), y + box.yMin(), x + box.xMax(), y + box.yMax())


def wire_rects(odb, wire):
    """Yield real routed segments and technology via enclosures, in the block's own coordinates."""
    routes = odb.dbWirePathItr()
    routes.begin(wire)
    path = odb.dbWirePath()
    shape = odb.dbWirePathShape()
    while routes.getNextPath(path):
        while routes.getNextShape(shape):
            part = shape.shape
            if part.isSegment():
                layer = part.getTechLayer().getName()
                if layer in ROUTING_LAYERS:
                    yield layer_rect(layer, part)
            elif part.isVia():
                via = part.getTechVia() or part.getVia()
                if via is None:
                    continue
                for box in via.getBoxes():
                    layer = box.getTechLayer().getName()
                    if layer in ROUTING_LAYERS:
                        yield layer_rect(layer, box, shape.point.getX(), shape.point.getY())


def near_pin(rect, pin_boxes, pad):
    """Whether the shape intersects a window around any box of the same signal port."""
    _, x0, y0, x1, y1 = rect
    return any(x0 < px1 + pad and x1 > px0 - pad and y0 < py1 + pad and y1 > py0 - pad
               for _, px0, py0, px1, py1 in pin_boxes)


def extract(odb, block, def_lines, window, selected_pins=()):
    if block.getDbUnitsPerMicron() != 1000:
        raise ValueError("pin stack export requires 1,000 database units per micron")
    pins = []
    for bterm in block.getBTerms():
        name = bterm.getName()
        if selected_pins and name not in selected_pins:
            continue
        net = bterm.getNet()
        if net is None or net.getWire() is None or net.getSigType() in ("POWER", "GROUND"):
            continue
        boxes = [layer_rect(box.getTechLayer().getName(), box)
                 for bpin in bterm.getBPins() for box in bpin.getBoxes()]
        if boxes:
            pins.append((name, net, boxes))
    missing = set(selected_pins) - {name for name, _, _ in pins}
    if missing:
        raise ValueError("requested pins have no routed signal geometry: " + ", ".join(sorted(missing)))
    patches = def_patches(def_lines, {net.getName() for _, net, _ in pins})
    nets = {}
    out = {}
    for name, net, boxes in pins:
        if net.getName() not in nets:
            rects = list(wire_rects(odb, net.getWire())) + patches.get(net.getName(), [])
            nets[net.getName()] = sorted(set(rects))
        stack = nets[net.getName()]
        if window is not None:
            stack = [rect for rect in stack if near_pin(rect, boxes, window)]
        out[name] = {"pin": boxes, "stack": stack}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("odb", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pin", action="append", default=[], help="expose the stack only for this pin; repeat as needed")
    window = parser.add_mutually_exclusive_group()
    window.add_argument("--window-nm", type=int, default=300)
    window.add_argument("--full", action="store_true", help="export the entire pin net for ownership diagnostics")
    args = parser.parse_args()
    if args.window_nm < 0:
        parser.error("--window-nm must be nonnegative")

    import odb

    db = odb.dbDatabase.create()
    odb.read_db(db, str(args.odb))
    block = db.getChip().getBlock()
    # OpenDB's path iterator omits the route RECT patches. Write a DEF from the
    # same database so those shapes retain the exact same net ownership.
    with tempfile.TemporaryDirectory(dir=args.output.parent) as scratch:
        path = Path(scratch) / "signed.def"
        odb.write_def(block, str(path))
        with path.open() as def_file:
            result = extract(odb, block, def_file, None if args.full else args.window_nm, set(args.pin))
    args.output.write_text(json.dumps(result, sort_keys=True) + "\n")
    print(f"OT_PINSTACK bterms {len(result)} shapes {sum(len(v['stack']) for v in result.values())}")


if __name__ == "__main__":
    main()
