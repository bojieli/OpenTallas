#!/usr/bin/env python3
"""Split abstract macro PG terminals into independent current injection sites.

Run with OpenROAD -python. This is a PDNSim model experiment, not a physical
netlist ECO: all PG rectangles and fixed die wires/vias are preserved. PDNSim
normally shorts every rectangle of a macro terminal to one 1-milliohm virtual
node. Independent terminals remove that ideal cross-strap short and share the
instance's declared power evenly across equal-area rectangles. Unequal-area
rectangles are rejected because PDNSim weights terminal nodes equally.
"""
import argparse
import json
from pathlib import Path


def split_rectangles(rectangles):
    """Validate equal area before PDNSim's equal-current terminal split."""
    if not rectangles:
        raise ValueError('supply terminal has no rectangles')
    areas = [(r[3] - r[1]) * (r[4] - r[2]) for r in rectangles]
    if min(areas) <= 0 or max(areas) != min(areas):
        raise ValueError('PG rectangles must have equal positive area for equal-current splitting')
    return rectangles


def distribute(db, odb):
    block = db.getChip().getBlock()
    cache, census = {}, []
    for inst in list(block.getInsts()):
        old = inst.getMaster()
        if not old.isBlock():
            continue
        if old.getName() not in cache:
            master = odb.dbMaster_create(old.getLib(), old.getName() + '__psm_distributed')
            master.setType('BLOCK')
            master.setWidth(old.getWidth())
            master.setHeight(old.getHeight())
            mapping = []
            for term in old.getMTerms():
                if term.getSigType() not in ('POWER', 'GROUND'):
                    continue
                rects = []
                for mpin in term.getMPins():
                    for box in mpin.getGeometry():
                        if box.isVia():
                            raise ValueError('via supply geometry requires explicit handling')
                        rects.append((box.getTechLayer(), box.xMin(), box.yMin(), box.xMax(), box.yMax()))
                split_rectangles(rects)
                for k, (layer, x0, y0, x1, y1) in enumerate(rects):
                    name = term.getName() + '__psm_' + str(k)
                    nt = odb.dbMTerm_create(master, name, 'INOUT', term.getSigType())
                    pin = odb.dbMPin_create(nt)
                    odb.dbBox_create(pin, layer, x0, y0, x1, y1)
                    mapping.append((name, term.getName()))
            master.setFrozen()
            cache[old.getName()] = master, mapping
            master.setFrozen()
        master, mapping = cache[old.getName()]
        nets = {it.getMTerm().getName(): it.getNet() for it in inst.getITerms()}
        name, orient, loc, status = inst.getName(), inst.getOrient(), inst.getLocation(), inst.getPlacementStatus()
        odb.dbInst_destroy(inst)
        ni = odb.dbInst_create(block, master, name)
        ni.setOrient(orient)
        ni.setLocation(*loc)
        ni.setPlacementStatus(status)
        connected = 0
        for termname, original in mapping:
            net = nets.get(original)
            if net is not None:
                ni.findITerm(termname).connect(net)
                connected += 1
        census.append(dict(instance=name, old_master=old.getName(), terminals=connected))
    return census


def main():
    import odb
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input_odb')
    p.add_argument('output_odb')
    p.add_argument('--census', required=True)
    args = p.parse_args()
    db = odb.dbDatabase.create()
    odb.read_db(db, args.input_odb)
    census = distribute(db, odb)
    if not census:
        raise ValueError('no block macro instances found')
    odb.write_db(db, args.output_odb)
    Path(args.census).write_text(json.dumps(dict(instances=len(census), terminals=sum(x['terminals'] for x in census), parts=census), indent=2) + '\n')
    print('OT_DISTRIBUTED_LOAD', len(census), sum(x['terminals'] for x in census))


if __name__ == '__main__':
    main()
