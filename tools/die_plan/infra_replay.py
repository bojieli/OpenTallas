#!/usr/bin/env python3
"""Replay actual routed infrastructure into a combined signal OpenDB design.

Run inside OpenROAD's Python interpreter, after the infrastructure has real wires
and vias (GRT guides are insufficient):
  openroad -python infra_replay.py --source infra.odb --target signals.odb \
    --nets infra_nets.txt --out combined.odb [--report replay.json]

The infrastructure ODB remains the physical base; target signal connectivity is
appended to it while actual wire/via geometry and terminals remain byte-identical.
Existing ROUTED path status is changed to FIXED in the new database only. This is a
physical import mechanism, not a clock-skew, connectivity, IR or freeze gate.
The net inventory must include every required reset/START net even if its signal
type is SIGNAL; all CLOCK/POWER/GROUND/RESET nets are required automatically.
The infrastructure DB supplies placement rows/tracks; signal pin placement must
agree, and target signal obstructions are merged into that physical base.
"""
import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path


def section(text, name):
    m = re.search(rf"(?ms)^{name}\s+\d+\s*;\s*\n(.*?)^END\s+{name}\s*$", text)
    if not m:
        return {}
    entries = re.findall(r"(?ms)^[ \t]*-\s+(.*?);\s*(?=^[ \t]*-|\Z)", m.group(1))
    result = {}
    for entry in entries:
        key = re.sub(r"\\(.)", r"\1", entry.split()[0])
        result[key] = "- " + entry.strip() + " ;\n"
    return result


def route_signature(record):
    """Canonical actual DEF path records; includes via names and wire coordinates."""
    paths = re.findall(r"(?s)\+\s+(?:ROUTED|FIXED|COVER)\s+(.*?)(?=\s+\+\s+\w+|\s*;\s*$)", record)
    return sorted(" ".join(p.split()) for p in paths)


def terminals(net):
    return sorted([("ITERM", t.getInst().getName(), t.getMTerm().getName()) for t in net.getITerms()] +
                  [("BTERM", t.getName()) for t in net.getBTerms()])


def inst_position(inst):
    return (inst.getMaster().getName(), tuple(inst.getLocation()), str(inst.getOrient()))


def load_db(path):
    import odb
    db = odb.dbDatabase.create()
    odb.read_db(db, str(path))
    if not db.getChip() or not db.getChip().getBlock():
        raise ValueError(f"no block in {path}")
    return db, db.getChip().getBlock()


def physical_snapshot(net):
    wire = net.getWire()
    regular = [(wire.getOpcode(i), wire.getData(i)) for i in range(wire.length())] if wire else []
    special = []
    for swire in net.getSWires():
        shapes = []
        for box in swire.getWires():
            via = box.getTechVia() or box.getBlockVia() if box.isVia() else None
            shapes.append((str(box.getWireShapeType()), box.getTechLayer().getName() if box.getTechLayer() else None,
                           box.xMin(), box.yMin(), box.xMax(), box.yMax(), via.getName() if via else None))
        special.append((str(swire.getWireType()), shapes))
    return dict(regular=regular, special=special, terminals=terminals(net),
                cell_geometry=sorted((t.getInst().getName(), inst_position(t.getInst()), str(t.getInst().getPlacementStatus()),
                                      t.getInst().isDoNotTouch()) for t in net.getITerms()),
                pin_geometry=sorted((t.getName(), pin_shapes(t)) for t in net.getBTerms()))


def pin_shapes(term):
    return sorted((b.getTechLayer().getName(), b.xMin(), b.yMin(), b.xMax(), b.yMax())
                  for p in term.getBPins() for b in p.getBoxes())


def route_shapes(net):
    """Actual metal rectangles, including every routing-layer via enclosure."""
    import odb

    def via_boxes(via, x, y):
        for box in via.getBoxes():
            layer = box.getTechLayer()
            if layer and layer.getRoutingLevel() > 0:
                yield layer, (box.xMin()+x, box.yMin()+y, box.xMax()+x, box.yMax()+y), "via_enclosure"

    wire = net.getWire()
    if wire:
        iterator = odb.dbWirePathItr()
        iterator.begin(wire)
        path, item = odb.dbWirePath(), odb.dbWirePathShape()
        while iterator.getNextPath(path):
            while iterator.getNextShape(item):
                shape = item.shape
                if shape.isVia():
                    via = shape.getTechVia() or shape.getVia()
                    yield from via_boxes(via, *shape.getViaXY())
                else:
                    layer = shape.getTechLayer()
                    if layer and layer.getRoutingLevel() > 0:
                        yield layer, (shape.xMin(), shape.yMin(), shape.xMax(), shape.yMax()), "wire"
    for swire in net.getSWires():
        for box in swire.getWires():
            if box.isVia():
                via = box.getTechVia() or box.getBlockVia()
                yield from via_boxes(via, *box.getViaXY())
            else:
                layer = box.getTechLayer()
                if layer and layer.getRoutingLevel() > 0:
                    yield layer, (box.xMin(), box.yMin(), box.xMax(), box.yMax()), "special_wire"


def reserve_actual_routes(block, names, tcl_path, extra_clearance_um=0.0):
    """Materialize real wire/via footprints as GRT obstacles (special wires alone
    are not subtracted from GRT capacity). Clearance is max(tech, NDR, caller).
    This is a conservative physical reservation, not a post-route DRC claim.
    """
    import odb
    dbu = block.getDbUnitsPerMicron()
    area = block.getDieArea()
    existing = {(o.getTechLayer().getName(), o.getBBox().xMin(), o.getBBox().yMin(),
                 o.getBBox().xMax(), o.getBBox().yMax()) for o in block.getObstructions()}
    result = dict(actual_shapes=0, new_obstructions=0, layers={}, kinds={},
                  clearance="max(technology spacing, net NDR spacing, explicit extra clearance)",
                  extra_clearance_um=extra_clearance_um)
    with Path(tcl_path).open("w") as f:
        f.write("# Actual OpenDB infrastructure wire/via footprints plus required spacing; no guides.\n")
        for name in sorted(names):
            net = block.findNet(name)
            rule = net.getNonDefaultRule()
            for layer, rect, kind in route_shapes(net):
                spacing = max(layer.getSpacing(), round(extra_clearance_um * dbu))
                lr = rule.getLayerRule(layer) if rule else None
                if lr:
                    spacing = max(spacing, lr.getSpacing())
                x0, y0, x1, y1 = rect
                rect = (max(area.xMin(), x0-spacing), max(area.yMin(), y0-spacing),
                        min(area.xMax(), x1+spacing), min(area.yMax(), y1+spacing))
                if rect[0] >= rect[2] or rect[1] >= rect[3]:
                    raise ValueError(f"infrastructure shape outside die: {name} {layer.getName()}")
                result["actual_shapes"] += 1
                result["layers"][layer.getName()] = result["layers"].get(layer.getName(), 0) + 1
                result["kinds"][kind] = result["kinds"].get(kind, 0) + 1
                key = (layer.getName(), *rect)
                if key in existing:
                    continue
                odb.dbObstruction.create(block, layer, *rect)
                existing.add(key)
                result["new_obstructions"] += 1
                coords = " ".join(f"{v/dbu:.6f}" for v in rect)
                f.write(f"create_obstruction -region {{{coords}}} -layer {layer.getName()}\n")
    return result


def replay(source, target, names, output, report=None, extra_clearance_um=0.0, provisional=()):
    import odb
    # The infrastructure database is the physical base. OpenROAD's incremental
    # DEF reader updates placement/pins but silently ignores routed NETS and
    # SPECIALNETS; transferring connectivity onto the already routed DB avoids
    # that trap and retains wire opcodes, via IDs, and BPin geometry unchanged.
    source_db, block = load_db(source)
    target_db, target_block = load_db(target)
    names, provisional = set(names), set(provisional)
    if not names:
        raise ValueError("explicit nonempty infrastructure net selection required")
    if block.getDbUnitsPerMicron() != target_block.getDbUnitsPerMicron():
        raise ValueError("source/target DBU mismatch")
    coords = lambda r: tuple(getattr(r, f)() for f in ("xMin", "yMin", "xMax", "yMax"))
    if coords(block.getDieArea()) != coords(target_block.getDieArea()):
        raise ValueError("source/target die area mismatch")
    typed_missing = [n.getName() for n in block.getNets()
                     if str(n.getSigType()) in ("CLOCK", "POWER", "GROUND", "RESET")
                     and n.getName() not in names]
    if typed_missing:
        raise ValueError("unselected typed infrastructure nets: " + ", ".join(typed_missing))
    selected, protected, fixed_status_changes, locked_cells = {}, set(), [], set()
    with tempfile.TemporaryDirectory(prefix="infra-replay-") as temporary:
        path = Path(temporary) / "source.def"
        odb.write_def(block, str(path))
        records = section(path.read_text(), "NETS") | section(path.read_text(), "SPECIALNETS")
        for name in names:
            net = block.findNet(name)
            if not net or not route_signature(records.get(name, "")):
                raise ValueError(f"infrastructure {name} lacks actual wires/vias; guides are not routes")
            if str(net.getWireType()) != "FIXED" or any(str(w.getWireType()) != "FIXED" for w in net.getSWires()):
                fixed_status_changes.append(name)
            # This updates route status, not dbWire geometry/opcodes. The input
            # ODB file is immutable; only the new combined database is marked.
            net.setWireType("FIXED")
            for wire in net.getSWires():
                wire.setWireType("FIXED")
            ts = terminals(net)
            if str(net.getSigType()) not in ("POWER", "GROUND") and len(ts) < 2:
                raise ValueError(f"infrastructure {name} has fewer than two terminals")
            protected.update(ts)
            for term in net.getITerms():
                cell = term.getInst()
                cell.setDoNotTouch(False)  # append legitimate signal pins on this physical cell first
                cell.setPlacementStatus("LOCKED")
                locked_cells.add(cell.getName())
            selected[name] = physical_snapshot(net)
        # A missed physical net must not be overwritten as a signal merely
        # because the caller supplied an incomplete protection inventory.
        omitted = [n.getName() for n in block.getNets()
                   if (n.getWire() or list(n.getSWires())) and n.getName() not in names]
        if omitted:
            raise ValueError("unselected physical infrastructure nets: " + ", ".join(omitted))
        for inst in target_block.getInsts():
            present = block.findInst(inst.getName())
            if present:
                if inst_position(inst) != inst_position(present):
                    raise ValueError(f"source/target instance placement or master differs: {inst.getName()}")
                continue
            master = source_db.findMaster(inst.getMaster().getName())
            if not master:
                raise ValueError(f"infrastructure DB lacks target cell master {inst.getMaster().getName()}")
            new = odb.dbInst.create(block, master, inst.getName())
            new.setOrient(str(inst.getOrient()))
            new.setLocation(*inst.getLocation())
            new.setPlacementStatus(str(inst.getPlacementStatus()))
        signals = {}
        for target_net in target_block.getNets():
            name = target_net.getName()
            if name in names:
                continue  # target's provisional clock/reset connections are replaced by the routed source
            if target_net.getWire() or list(target_net.getSWires()):
                raise ValueError(f"target signal {name} already has routes; supply its placed pre-signal DB")
            net = block.findNet(name) or odb.dbNet.create(block, name)
            net.setSigType(str(target_net.getSigType()))
            wanted = []
            for term in target_net.getITerms():
                key = ("ITERM", term.getInst().getName(), term.getMTerm().getName())
                if key in protected:
                    if name not in provisional:
                        raise ValueError(f"target data net {name} attaches protected infrastructure terminal {key}; "
                                         "name an explicitly provisional infrastructure net to reconnect it")
                    continue
                dest = block.findInst(key[1]).findITerm(key[2])
                dest.connect(net)
                wanted.append(key)
            for term in target_net.getBTerms():
                key = ("BTERM", term.getName())
                if key in protected:
                    if name not in provisional:
                        raise ValueError(f"target data net {name} attaches protected infrastructure terminal {key}; "
                                         "name an explicitly provisional infrastructure net to reconnect it")
                    continue
                dest = block.findBTerm(term.getName())
                if dest:
                    if pin_shapes(dest) != pin_shapes(term):
                        raise ValueError(f"source/target pin geometry differs: {term.getName()}")
                    dest.connect(net)
                else:
                    dest = odb.dbBTerm.create(net, term.getName())
                    dest.setIoType(str(term.getIoType()))
                    dest.setSigType(str(term.getSigType()))
                    for target_pin in term.getBPins():
                        pin = odb.dbBPin.create(dest)
                        pin.setPlacementStatus(str(target_pin.getPlacementStatus()))
                        for box in target_pin.getBoxes():
                            layer = source_db.getTech().findLayer(box.getTechLayer().getName())
                            if not layer:
                                raise ValueError(f"target pin uses unknown layer {box.getTechLayer().getName()}")
                            odb.dbBox.create(pin, layer, box.xMin(), box.yMin(), box.xMax(), box.yMax())
                wanted.append(key)
            if terminals(net) != sorted(wanted):
                raise ValueError(f"signal connectivity differs after transfer: {name}")
            signals[name] = sorted(wanted)
        # Retain source infra reservations and also import the target's signal
        # routing blockages. Exact duplicate obstructions are not multiplied.
        def obstruction_key(o):
            b = o.getBBox()
            return (o.getTechLayer().getName(), b.xMin(), b.yMin(), b.xMax(), b.yMax())
        existing = {obstruction_key(o) for o in block.getObstructions()}
        for obstruction in target_block.getObstructions():
            key = obstruction_key(obstruction)
            if key not in existing:
                layer = source_db.getTech().findLayer(key[0])
                if not layer:
                    raise ValueError(f"target obstruction uses unknown layer {key[0]}")
                odb.dbObstruction.create(block, layer, *key[1:])
                existing.add(key)
        for name, expected in selected.items():
            net = block.findNet(name)
            if physical_snapshot(net) != expected:
                raise ValueError(f"signal transfer altered infrastructure wire/via/terminal data: {name}")
            net.setDoNotTouch(True)
        for cell in locked_cells:
            block.findInst(cell).setDoNotTouch(True)
        selected = {name: physical_snapshot(block.findNet(name)) for name in selected}
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        reservations = reserve_actual_routes(block, names, output.with_suffix(".infra_obs.tcl"), extra_clearance_um)
        odb.write_db(source_db, str(output))
        odb.write_def(block, str(output.with_suffix(".infra.def")))
    result = dict(schema="opentallas.infra_replay.v1", source=str(source), target=str(target), output=str(output),
                  verdict="IMPORTED", freeze_qualified=False, nets=selected, signals=signals,
                  fixed_status_changes=sorted(fixed_status_changes), reservations=reservations,
                  locked_cells=sorted(locked_cells), provisional_infrastructure_nets=sorted(provisional),
                  wire_geometry_sha256=hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest(),
                  note="Infrastructure ODB retained; target signal connectivity appended; physical freeze gates remain separate")
    Path(report or output.with_suffix(".replay.json")).write_text(json.dumps(result, indent=2) + "\n")
    return result


def verify(database, receipt):
    _db, block = load_db(database)
    reference = json.loads(Path(receipt).read_text())
    for name, expected in reference["nets"].items():
        net = block.findNet(name)
        if not net or json.dumps(physical_snapshot(net), sort_keys=True) != json.dumps(expected, sort_keys=True):
            raise ValueError(f"routing altered preserved infrastructure wire/via/terminal data: {name}")
    for name, expected in reference.get("signals", {}).items():
        net = block.findNet(name)
        if not net or json.dumps(terminals(net)) != json.dumps(expected):
            raise ValueError(f"routing altered transferred signal connectivity: {name}")
    return dict(verdict="PRESERVED", freeze_qualified=False, nets=len(reference["nets"]),
                signals=len(reference.get("signals", {})))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source")
    p.add_argument("--target")
    p.add_argument("--nets", help="One exact infrastructure net name per line")
    p.add_argument("--out")
    p.add_argument("--report")
    p.add_argument("--provisional-nets", help="File naming explicit target provisional infrastructure nets allowed to reconnect")
    p.add_argument("--extra-clearance-um", type=float, default=0.0,
                   help="Nonnegative extra metal clearance; maxed with technology/NDR spacing")
    p.add_argument("--verify", metavar="ROUTED_ODB", help="Verify preservation after signal routing")
    p.add_argument("--against", metavar="REPLAY_JSON", help="Original import receipt for --verify")
    a = p.parse_args(argv)
    if a.verify:
        if not a.against:
            p.error("--verify requires --against")
        result = verify(a.verify, a.against)
        print("INFRA_REPLAY PRESERVED", result["nets"], "nets; no freeze qualification")
        return
    if not all((a.source, a.target, a.nets, a.out)):
        p.error("import requires --source, --target, --nets and --out")
    names = [line.strip() for line in Path(a.nets).read_text().splitlines() if line.strip() and not line.startswith("#")]
    if a.extra_clearance_um < 0:
        p.error("--extra-clearance-um must be nonnegative")
    provisional = Path(a.provisional_nets).read_text().split() if a.provisional_nets else ()
    result = replay(a.source, a.target, names, a.out, a.report, a.extra_clearance_um, provisional)
    print("INFRA_REPLAY IMPORTED", len(result["nets"]), "nets; actual fixed routes, no freeze qualification")


if __name__ == "__main__":
    main()
