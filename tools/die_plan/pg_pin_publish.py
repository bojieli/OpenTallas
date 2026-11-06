#!/usr/bin/env python3
"""Publish actual existing power-wire rectangles as macro PG pin geometry.

Run in an OpenROAD Python environment. This copies connected VDD/VSS special
wire metal into the SAME net's existing BTerm. It does not add/move wires,
vias, cells, clocks or signal pins, and does not invent a routing aperture.
An actual abstract export and parent PG-mode check must follow.
"""
import argparse
import hashlib
import json
from pathlib import Path


def _rect(box):
    return (box.xMin(),box.yMin(),box.xMax(),box.yMax())


def _special_geometry(net):
    rows=[]
    for wire in net.getSWires():
        for box in wire.getWires():
            if box.isVia():
                via=box.getTechVia() or box.getBlockVia()
                rows.append(("via",via.getName(),*_rect(box)))
            else:
                rows.append(("metal",box.getTechLayer().getName(),*_rect(box)))
    return sorted(rows)


def publish(input_db,output_db,layer,report=None):
    import odb
    source=Path(input_db);target=Path(output_db)
    if source.resolve()==target.resolve():
        raise ValueError("output must be a fresh private database")
    if target.exists():
        raise FileExistsError(target)
    db=odb.dbDatabase.create();odb.read_db(db,str(source));block=db.getChip().getBlock()
    tech_layer=db.getTech().findLayer(layer)
    if tech_layer is None:
        raise ValueError(f"technology has no layer {layer}")
    before={};staged={}
    for name in ("VDD","VSS"):
        net=block.findNet(name)
        if net is None:
            raise ValueError(f"missing existing supply net {name}")
        terms=[t for t in net.getBTerms() if t.getName()==name]
        if len(terms)!=1:
            raise ValueError(f"{name}: requires its one existing supply BTerm")
        shapes=_special_geometry(net);before[name]=shapes
        rects={tuple(row[2:]) for row in shapes if row[:2]==("metal",layer)}
        if not rects:
            raise ValueError(f"{name}: no actual {layer} power-wire metal to publish")
        term=terms[0];existing=[]
        for pin in term.getBPins():
            existing += [_rect(q) for q in pin.getBoxes() if q.getTechLayer()==tech_layer]
        # A previously published larger shape can already cover a wire fragment.
        missing=[r for r in sorted(rects) if not any(q[0]<=r[0] and q[1]<=r[1] and q[2]>=r[2] and q[3]>=r[3] for q in existing)]
        staged[name]=(net,term,missing)
    out={"schema":"opentallas.pg_pin_publish.v1","input_db":str(source),"output_db":str(target),
         "layer":layer,"supply":{},"interface_only":True,"added_signal_cycles":0}
    for name,(net,term,missing) in staged.items():
        if missing:
            prior=list(term.getBPins());pin=odb.dbBPin_create(term)
            pin.setPlacementStatus(prior[0].getPlacementStatus() if prior else "FIRM")
            for r in missing:
                odb.dbBox_create(pin,tech_layer,*r)
        after=_special_geometry(net)
        assert before[name]==after,"publishing a pin must not change existing PG geometry"
        out["supply"][name]={"added_pin_rectangles":len(missing),"existing_pg_geometry_sha256":
                            hashlib.sha256(json.dumps(before[name],separators=(",",":")).encode()).hexdigest()}
    odb.write_db(db,str(target))
    odb.dbDatabase.destroy(db)
    if report:
        Path(report).write_text(json.dumps(out,indent=2)+"\n")
    return out


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("input_db");p.add_argument("output_db");p.add_argument("--layer",required=True);p.add_argument("--report")
    a=p.parse_args(argv);print(json.dumps(publish(a.input_db,a.output_db,a.layer,a.report)))


if __name__=="__main__":main()
