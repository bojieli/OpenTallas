#!/usr/bin/env python3
"""Read actual clock-cell supply metal before planning physical PG access.

Run with OpenROAD Python. This writes no ODB and qualifies no route or IR gate.
Coordinates come from each instantiated master and orientation, never a nominal
clock site or a signal-pin proxy.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path


def transformed_rect(inst, shape):
    signs = {"R0": (1, 1), "MX": (1, -1), "MY": (-1, 1), "R180": (-1, -1)}
    orientation = str(inst.getOrient())
    if orientation not in signs:
        raise ValueError(f"unsupported orientation: {orientation}")
    sx, sy = signs[orientation]
    ox, oy = inst.getOrigin()
    xs = sorted((ox + sx * shape.xMin(), ox + sx * shape.xMax()))
    ys = sorted((oy + sy * shape.yMin(), oy + sy * shape.yMax()))
    return [xs[0], ys[0], xs[1], ys[1]]


def census(source, output, expected_cells=None):
    import odb
    database = odb.dbDatabase.create()
    odb.read_db(database, str(source))
    block = database.getChip().getBlock()
    dbu = block.getDbUnitsPerMicron()
    rows, masters, orientations = [], Counter(), Counter()
    for inst in block.getInsts():
        master = inst.getMaster().getName()
        if not master.startswith("CKINVDCx16_"):
            continue
        masters[master] += 1
        orientations[str(inst.getOrient())] += 1
        for name, kind in (("VDD", "POWER"), ("VSS", "GROUND")):
            term = inst.findITerm(name)
            if not term or str(term.getMTerm().getSigType()) != kind:
                raise ValueError(f"missing declared supply {inst.getName()}/{name}")
            shapes = []
            for pin in term.getMTerm().getMPins():
                for shape in pin.getGeometry():
                    layer = shape.getTechLayer()
                    if layer and layer.getRoutingLevel() > 0:
                        shapes.append([layer.getName(), *transformed_rect(inst, shape)])
            if not shapes:
                raise ValueError(f"supply has no physical metal: {inst.getName()}/{name}")
            rows.append(dict(inst=inst.getName(), pin=name, master=master,
                             orient=str(inst.getOrient()), shapes_dbu=shapes,
                             connected_net=term.getNet().getName() if term.getNet() else None))
    if expected_cells is not None and sum(masters.values()) != expected_cells:
        raise ValueError(f"clock-cell count {sum(masters.values())} != {expected_cells}")

    # Detect actual existing opposing supply contacts before adding any stack.
    # A contact along a nonzero edge also conducts; mere corner contact is not
    # classified here. Original source geometry is retained unchanged.
    bins, rectangles, contacts = defaultdict(list), [], []
    bucket = max(1, round(2.16 * dbu))
    for row in rows:
        for layer, x0, y0, x1, y1 in row["shapes_dbu"]:
            cells = [(layer, x, y) for x in range(x0 // bucket, x1 // bucket + 1)
                     for y in range(y0 // bucket, y1 // bucket + 1)]
            seen = set()
            for cell in cells:
                for index in bins[cell]:
                    if index in seen:
                        continue
                    seen.add(index)
                    other = rectangles[index]
                    if other[0] == row["pin"]:
                        continue
                    dx = min(x1, other[4]) - max(x0, other[2])
                    dy = min(y1, other[5]) - max(y0, other[3])
                    if dx >= 0 and dy >= 0 and (dx > 0 or dy > 0):
                        contacts.append([row["inst"], row["pin"], other[1], other[0], layer,
                                         dx / dbu, dy / dbu])
            number = len(rectangles)
            rectangles.append((row["pin"], row["inst"], x0, y0, x1, y1))
            for cell in cells:
                bins[cell].append(number)
    vias = {}
    for via in database.getTech().getVias():
        if via.getName() in {f"VIA{i}{i+1}" for i in range(1, 9)}:
            vias[via.getName()] = [
                [box.getTechLayer().getName(), box.xMin(), box.yMin(), box.xMax(), box.yMax()]
                for box in via.getBoxes() if box.getTechLayer()]
    output.mkdir(parents=True, exist_ok=True)
    (output / "power_terms.json").write_text(json.dumps(dict(dbu=dbu, terms=rows), separators=(",", ":")))
    result = dict(source=str(source), physical_route=False, odb_mutated=False,
                  dbu=dbu, cells=sum(masters.values()), terms=len(rows),
                  masters=dict(masters), orientations=dict(orientations),
                  supply_rectangles=len(rectangles), opposing_supply_contacts=len(contacts),
                  contact_examples=contacts[:40], tech_vias_dbu=vias,
                  verdict="FAIL_EXISTING_SUPPLY_CONTACTS" if contacts else "READY_FOR_PG_ACCESS_PLAN")
    (output / "census.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--odb", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expect-cells", type=int)
    args = parser.parse_args()
    census(args.odb, args.out, args.expect_cells)
