"""Abutment audit of a routed die ODB (OpenROAD python): opens and shorts on the shared partition faces.

    openroad -python -exit tools/die_plan/abut_audit.py   with env ODB=<die_routed.odb> OUT=<json>

For every die net, the pin shapes of its partition (macro) terminals are taken in die coordinates.
- OPEN: two macro terminals of one net on a shared face whose shapes neither touch nor overlap and that are not joined
  by routed wire (the net has no wire).
- SHORT: two shapes of different nets on the same layer that touch or overlap, or that lie closer than the layer's
  min spacing.
It also counts the routed die nets (clock / reset spine) and reads the DRC marker count of the die route.
"""
import json
import os
from collections import defaultdict

import odb  # noqa: E402


def boxes_of(iterm):
    inst = iterm.getInst()
    tr = inst.getTransform()
    out = []
    for mp in iterm.getMTerm().getMPins():
        for g in mp.getGeometry():
            L = g.getTechLayer()
            if L is None:
                continue
            r = odb.Rect(g.xMin(), g.yMin(), g.xMax(), g.yMax())
            tr.apply(r)
            out.append((L.getName(), r.xMin(), r.yMin(), r.xMax(), r.yMax()))
    return out


def touch(a, b, gap=0):
    return a[0] == b[0] and a[1] <= b[3] + gap and b[1] <= a[3] + gap and a[2] <= b[4] + gap and b[2] <= a[4] + gap


def main():
    db = odb.dbDatabase.create()
    db = odb.read_db(db, os.environ["ODB"])
    block = db.getChip().getBlock()
    tech = db.getTech()
    dbu = block.getDefUnits()
    spacing = {L.getName(): L.getSpacing() for L in tech.getLayers()}
    res = dict(nets=0, abut_nets=0, abut_ok=0, opens=[], shorts=[], wired_nets=0, macro_pins=0)
    shapes = defaultdict(list)            # layer -> [(box, net)]
    for net in block.getNets():
        st = net.getSigType()
        if st in ("POWER", "GROUND"):
            continue
        res["nets"] += 1
        its = [it for it in net.getITerms() if it.getInst().getMaster().isBlock()]
        wired = net.getWire() is not None
        res["wired_nets"] += wired
        bxs = []
        for it in its:
            b = boxes_of(it)
            res["macro_pins"] += 1
            bxs.append((it.getInst().getName() + "/" + it.getMTerm().getName(), b))
            for x in b:
                shapes[x[0]].append((x, net.getName()))
        insts = {n.split("/")[0] for n, _ in bxs}
        if len(bxs) == 2 and len(insts) == 2 and not net.getBTerms() and net.getName() not in ("clk", "rst_n"):
            res["abut_nets"] += 1
            if any(touch(a, b) for a in bxs[0][1] for b in bxs[1][1]):
                res["abut_ok"] += 1
            elif not wired:
                res["opens"].append(net.getName())
            else:
                res["abut_ok"] += 1          # joined by routed wire (not abutted, but connected)
    nshort = 0
    for L, lst in shapes.items():
        gap = spacing.get(L, 0) - 1
        lst.sort(key=lambda s: s[0][1])
        for i, (a, na) in enumerate(lst):
            j = i + 1
            while j < len(lst) and lst[j][0][1] <= a[3] + gap:
                b, nb = lst[j]
                if nb != na and touch(a, b, gap):
                    nshort += 1
                    if len(res["shorts"]) < 20:
                        res["shorts"].append([L, na, nb])
                j += 1
    res["short_n"] = nshort
    res["open_n"] = len(res["opens"])
    res["opens"] = res["opens"][:20]
    try:
        txt = open(os.environ.get("DRC", "/work/die_drc.rpt")).read()
        res["drc_markers"] = txt.count("violation type")
    except OSError:
        res["drc_markers"] = None
    res["verdict"] = "PASS" if res["open_n"] == 0 and nshort == 0 and res["abut_nets"] == res["abut_ok"] else "FAIL"
    json.dump(res, open(os.environ["OUT"], "w"), indent=1)
    print(f"ABUT_AUDIT {res['verdict']} abut nets {res['abut_ok']}/{res['abut_nets']} opens {res['open_n']} "
          f"shorts {nshort} die nets {res['nets']} wired {res['wired_nets']} drc_markers {res['drc_markers']}")


main()
