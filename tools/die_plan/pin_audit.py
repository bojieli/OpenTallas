"""Pin audit (OpenROAD python): every placed pin of a partition / die ODB against the plan's exact pins.

    openroad -python -exit tools/die_plan/pin_audit.py   with env ODB=<db> PINS=<kit pins.json> OUT=<json>
    (pins.json from gen.py phys: bus, bit, layer, x, y, face in the type frame)

A pin passes when its BTerm has one box on the plan layer whose centre lies on the plan coordinate along the face
(+/- 0.001 um) and which touches the plan face.  Output: {pins, ok, missing, wrong_layer, wrong_place, extra}.
"""
import json
import re
import os

import odb  # noqa: E402  (OpenROAD python)

TOL = 0.001


def main():
    db = odb.dbDatabase.create()
    db = odb.read_db(db, os.environ["ODB"])
    block = db.getChip().getBlock()
    dbu = block.getDefUnits()
    die = block.getDieArea()
    W, H = die.xMax() / dbu, die.yMax() / dbu
    want = {f"{p['bus']}[{p['bit']}]": p for p in json.load(open(os.environ["PINS"]))}
    res = dict(pins=len(want), ok=0, missing=[], wrong_layer=[], wrong_place=[], extra=[])
    seen = set()
    for bt in block.getBTerms():
        n = bt.getName()
        if n not in want:
            # clock taps (R4: clk, clk_t<i>), the reset tap and reset wavefront outs are interior die pins, not face pins
            if not re.match(r"^(clk(_t[0-9]+|_c[0-9]+)?|arst_n|rst_o_[0-9]+|start_i|start_o_[0-9]+)$", n) and not bt.getSigType() in ("POWER", "GROUND"):
                res["extra"].append(n)
            continue
        seen.add(n)
        p = want[n]
        boxes = [(b.getTechLayer().getName(), b.xMin() / dbu, b.yMin() / dbu, b.xMax() / dbu, b.yMax() / dbu)
                 for bp in bt.getBPins() for b in bp.getBoxes()]
        lay = [b for b in boxes if b[0] == p["layer"]]
        if not lay:
            res["wrong_layer"].append([n, p["layer"], sorted({b[0] for b in boxes})])
            continue
        good = False
        for _, x0, y0, x1, y1 in lay:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            f = p["face"]
            along = abs(cy - p["y"]) <= TOL if f in "EW" else abs(cx - p["x"]) <= TOL
            edge = {"E": abs(x1 - W) <= TOL, "W": abs(x0) <= TOL, "N": abs(y1 - H) <= TOL, "S": abs(y0) <= TOL}[f]
            good |= along and edge
        if good:
            res["ok"] += 1
        else:
            res["wrong_place"].append([n, p, lay[0]])
    res["missing"] = sorted(set(want) - seen)
    for k in ("missing", "wrong_layer", "wrong_place", "extra"):
        res[k + "_n"] = len(res[k])
        res[k] = res[k][:20]
    res["verdict"] = "PASS" if res["ok"] == res["pins"] and not res["extra_n"] else "FAIL"
    json.dump(res, open(os.environ["OUT"], "w"), indent=1)
    print(f"PIN_AUDIT {res['verdict']} {res['ok']}/{res['pins']} missing {res['missing_n']} wrong_layer "
          f"{res['wrong_layer_n']} wrong_place {res['wrong_place_n']} extra {res['extra_n']}")


main()
