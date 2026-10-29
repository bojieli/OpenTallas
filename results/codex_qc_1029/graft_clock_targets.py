#!/usr/bin/env python3
"""Replace standalone clock tap ports with actual partition clock ITerms.

Run in OpenROAD Python BEFORE constructing physical clock wires. The returned
endpoint table drives the physical emitter; it must build real pin stacks to
these M7 pins. This script grants no route, timing or freeze qualification.
"""
import argparse
import json
from pathlib import Path


def load(path):
    import odb
    database = odb.dbDatabase.create()
    odb.read_db(database, str(path))
    return database, database.getChip().getBlock()


def rect(box):
    return tuple(getattr(box, key)() for key in ("xMin", "yMin", "xMax", "yMax"))


def placement(inst):
    return (inst.getMaster().getName(), tuple(inst.getLocation()), str(inst.getOrient()))


def graft(source, target, tree_path, output, report):
    import odb
    database, block = load(source)
    target_db, target_block = load(target)
    if block.getDbUnitsPerMicron() != target_block.getDbUnitsPerMicron():
        raise ValueError("source/target DBU mismatch")
    if rect(block.getDieArea()) != rect(target_block.getDieArea()):
        raise ValueError("source/target die area mismatch")
    # A terminal change after construction would invalidate a frozen physical
    # clock. Refuse it rather than silently rewriting its preservation receipt.
    wired = [net.getName() for net in block.getNets()
             if net.getWire() or list(net.getSWires())]
    if wired:
        raise ValueError(f"graft must precede wire construction ({len(wired)} routed nets)")
    taps = json.loads(Path(tree_path).read_text())["taps"]
    ports = [tap["port"] for tap in taps]
    endpoints = [(tap["part"], tap["tap"]) for tap in taps]
    if len(set(ports)) != len(ports) or len(set(endpoints)) != len(endpoints):
        raise ValueError("duplicate clock tap port or endpoint")
    extra = {term.getName() for term in block.getBTerms()
             if term.getName().startswith("t_")} - set(ports)
    if extra:
        raise ValueError(f"unmapped source clock tap ports: {sorted(extra)[:8]}")
    created = []
    for original in target_block.getInsts():
        inst = block.findInst(original.getName())
        if inst:
            if placement(inst) != placement(original):
                raise ValueError(f"different target instance placement: {original.getName()}")
            continue
        master = database.findMaster(original.getMaster().getName())
        if not master:
            raise ValueError(f"source lacks target master {original.getMaster().getName()}")
        inst = odb.dbInst.create(block, master, original.getName())
        inst.setOrient(str(original.getOrient()))
        inst.setLocation(*original.getLocation())
        inst.setPlacementStatus(str(original.getPlacementStatus()))
        created.append(inst.getName())
    rows = {}
    dbu = block.getDbUnitsPerMicron()
    for tap in taps:
        port = block.findBTerm(tap["port"])
        inst = block.findInst(tap["part"])
        term = inst.findITerm(tap["tap"]) if inst else None
        if not port or not port.getNet() or not term:
            raise ValueError(f"missing clock source or target: {tap}")
        if term.getNet():
            raise ValueError(f"target clock already connected: {tap['part']}/{tap['tap']}")
        layers = {shape.getTechLayer().getName()
                  for pin in term.getMTerm().getMPins() for shape in pin.getGeometry()
                  if shape.getTechLayer() and shape.getTechLayer().getRoutingLevel() > 0}
        if layers != {"M7"}:
            raise ValueError(f"target clock is not an M7 entry: {tap['part']}/{tap['tap']} {layers}")
        signs = {"R0": (1, 1), "MX": (1, -1), "MY": (-1, 1), "R180": (-1, -1)}
        orient = str(inst.getOrient())
        if orient not in signs:
            raise ValueError(f"unsupported partition orientation: {orient}")
        sx, sy = signs[orient]
        ox, oy = inst.getOrigin()
        pin_rects = []
        for pin in term.getMTerm().getMPins():
            for shape in pin.getGeometry():
                if shape.getTechLayer().getName() != "M7":
                    continue
                xs = sorted((ox + sx*shape.xMin(), ox + sx*shape.xMax()))
                ys = sorted((oy + sy*shape.yMin(), oy + sy*shape.yMax()))
                pin_rects.append([xs[0]/dbu, ys[0]/dbu, xs[1]/dbu, ys[1]/dbu])
        if len(pin_rects) != 1:
            raise ValueError(f"ambiguous target M7 pin metal: {tap['port']} {pin_rects}")
        ok, centre_x, centre_y = term.getAvgXY()
        if not ok:
            raise ValueError(f"target clock has no physical point: {tap}")
        planned = tuple(round(value * dbu) for value in tap["xy"])
        x0, y0, x1, y1 = (round(value*dbu) for value in pin_rects[0])
        # The abstract compiler snaps/clips the actual M7 pin independently
        # of the standalone M9 tap. Use the native pin's metal centroid as
        # the physical endpoint, and expose the displacement to the route
        # planner. No fictitious M7 conductor is added at the nominal point.
        x, y = centre_x, centre_y
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            raise ValueError(f"clock centroid outside actual pin metal: {tap['port']}")
        boxes = [shape for pin in port.getBPins() for shape in pin.getBoxes()]
        if len(boxes) != 1:
            raise ValueError(f"ambiguous source tap pin: {tap['port']} {len(boxes)} boxes")
        box = boxes[0]
        source_xy = ((box.xMin()+box.xMax())/2, (box.yMin()+box.yMax())/2)
        if max(abs(source_xy[0] - planned[0]), abs(source_xy[1] - planned[1])) > 1:
            raise ValueError(f"standalone tap differs from its tree: {tap['port']} {source_xy} != {planned}")
        net = port.getNet()
        term.connect(net)
        rows[tap["port"]] = dict(net=net.getName(), inst=inst.getName(), pin=term.getMTerm().getName(),
                                 layer="M7", xy_um=[x/dbu,y/dbu],
                                 rect_um=pin_rects[0],
                                 pin_centroid_um=[centre_x/dbu,centre_y/dbu],
                                 planned_xy_um=[value/dbu for value in planned],
                                 displacement_um=(abs(x-planned[0])+abs(y-planned[1]))/dbu,
                                 original_layer=box.getTechLayer().getName(),
                                 original_xy_um=[source_xy[0]/dbu,source_xy[1]/dbu])
        odb.dbBTerm.destroy(port)
    for name, row in rows.items():
        term = block.findInst(row["inst"]).findITerm(row["pin"])
        if block.findBTerm(name) or not term.getNet() or term.getNet().getName() != row["net"]:
            raise ValueError(f"clock terminal graft did not persist: {name}")
    odb.write_db(database, str(output))
    result = dict(schema="opentallas.qc.clock_targets.v1", verdict="CONNECTED_UNROUTED",
                  freeze_qualified=False, source=str(source), target=str(target), tree=str(tree_path),
                  output=str(output), instances_added=len(created), taps=len(rows), endpoints=rows,
                  endpoint_basis="actual native M7 pin metal; nominal M9 tap displacement reported",
                  max_displacement_um=max((row["displacement_um"] for row in rows.values()), default=0),
                  next="construct actual clock wires/vias and M8/M9-to-M7 terminal stacks before infra_replay")
    Path(report).write_text(json.dumps(result, indent=1)+"\n")
    print("QC_CLOCK_TARGETS CONNECTED_UNROUTED", len(rows), "taps; no physical route qualification")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("source", "target", "tree", "out", "report"):
        parser.add_argument("--"+option, required=True, type=Path)
    args = parser.parse_args()
    graft(args.source, args.target, args.tree, args.out, args.report)
