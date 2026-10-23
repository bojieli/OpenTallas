"""Seam audit of a routed die ODB (OpenROAD python; CP1 checks, COORD 10-23).

    openroad -python -exit tools/die_plan/abut_audit.py   env ODB=<die_routed.odb> SEAMS=<seams.json> OUT=<json>
                                                          [DRC=<die_drc.rpt>]

SEAMS is the plan's list of seam nets, written by gen.py assembly. Each entry is
{net, port, kind: abutted|channel, src, dst}.

Every seam net must satisfy all of these:
- it exists;
- it has exactly 2 ITerms, one on src and one on dst, both macros;
- it has no BTerm (no top-port tap) and no other ITerm (no fan-out).

An abutted seam must also have:
- pin shapes on the SAME layer that overlap or touch. This catches OR#11810 on images without #11814: different-layer
  overlaps are treated as abutted and left unrouted;
- dbNet.isConnectedByAbutment() true.

A channel seam must also have routed wire, and the two pins must not touch.

Die-wide checks:
- every non-seam signal net with 2 or more terminals has wire;
- the seam count equals the plan's;
- the DRC marker count of the die route.
"""
import json
import os

import odb  # noqa: E402


SIGN = {"R0": (1, 1), "MX": (1, -1), "MY": (-1, 1), "R180": (-1, -1)}


def boxes_of(iterm):
    """pin shapes in die coordinates (orient R0 / MX / MY / R180 about the instance origin)."""
    inst = iterm.getInst()
    ox, oy = inst.getOrigin()
    sx, sy = SIGN[inst.getOrient()]
    out = []
    for mp in iterm.getMTerm().getMPins():
        for g in mp.getGeometry():
            L = g.getTechLayer()
            if L is None or L.getType() != "ROUTING":
                continue
            xs = sorted((ox + sx * g.xMin(), ox + sx * g.xMax()))
            ys = sorted((oy + sy * g.yMin(), oy + sy * g.yMax()))
            out.append((L.getName(), xs[0], ys[0], xs[1], ys[1]))
    return out


def bterm_on_pin(bt, it):
    """die IO BTerm shape on the same layer overlapping the partition pin (die-edge IO with no wire)."""
    a = boxes_of(it)
    for bp in bt.getBPins():
        for bx in bp.getBoxes():
            L = bx.getTechLayer()
            b = (L.getName() if L else "", bx.xMin(), bx.yMin(), bx.xMax(), bx.yMax())
            if any(touch(x, b) for x in a):
                return True
    return False


def touch(a, b):
    return a[0] == b[0] and a[1] <= b[3] and b[1] <= a[3] and a[2] <= b[4] and b[2] <= a[4]


def xy_touch(a, b):
    return a[1] <= b[3] and b[1] <= a[3] and a[2] <= b[4] and b[2] <= a[4]


def main():
    db = odb.dbDatabase.create()
    db = odb.read_db(db, os.environ["ODB"])
    block = db.getChip().getBlock()
    plan = json.load(open(os.environ["SEAMS"]))["seams"]
    want = {s["net"]: s for s in plan}
    res = dict(plan_seams=len(plan), plan_abutted=sum(s["kind"] == "abutted" for s in plan),
               plan_channel=sum(s["kind"] == "channel" for s in plan), found=0, ok=0, fails={}, examples={},
               nonseam_nets=0, nonseam_unrouted=[], layer_mismatch_xy_overlap=0)

    def fail(kind, net, msg):
        res["fails"][kind] = res["fails"].get(kind, 0) + 1
        res["examples"].setdefault(kind, [])
        if len(res["examples"][kind]) < 5:
            res["examples"][kind].append(f"{net}: {msg}")

    seen = set()
    for net in block.getNets():
        if net.getSigType() in ("POWER", "GROUND"):
            continue
        nm = net.getName()
        its = list(net.getITerms())
        bts = list(net.getBTerms())
        wired = net.getWire() is not None
        s = want.get(nm)
        if s is None:
            if len(its) + len(bts) >= 2:
                res["nonseam_nets"] += 1
                if len(its) == 1 and len(bts) == 1 and not wired and bterm_on_pin(bts[0], its[0]):
                    res["io_pin_on_pin"] = res.get("io_pin_on_pin", 0) + 1   # die IO pin drawn on the partition pin
                    continue
                if not wired and not net.isConnectedByAbutment():
                    if len(res["nonseam_unrouted"]) < 20:
                        res["nonseam_unrouted"].append(nm)
                    res["nonseam_unrouted_n"] = res.get("nonseam_unrouted_n", 0) + 1
            continue
        seen.add(nm)
        res["found"] += 1
        good = True
        if bts:
            fail("top_port_tap", nm, f"{len(bts)} BTerm(s)")
            good = False
        insts = sorted(it.getInst().getName() for it in its)
        if len(its) != 2 or insts != sorted([s["src"], s["dst"]]):
            fail("not_2pin_src_dst", nm, f"ITerms on {insts}")
            good = False
        if any(not it.getInst().getMaster().isBlock() for it in its):
            fail("not_macro_pins", nm, "a terminal is not a partition macro pin")
            good = False
        if len(its) == 2:
            a, b = boxes_of(its[0]), boxes_of(its[1])
            same = any(touch(x, y) for x in a for y in b)
            diff = any(xy_touch(x, y) and x[0] != y[0] for x in a for y in b)
            if diff and not same:
                res["layer_mismatch_xy_overlap"] += 1
            if s["kind"] == "abutted":
                if not same:
                    fail("abut_no_same_layer_overlap", nm, f"layers {sorted({x[0] for x in a})} / "
                         f"{sorted({y[0] for y in b})}")
                    good = False
                if not net.isConnectedByAbutment():
                    fail("abut_not_recognised", nm, "isConnectedByAbutment false")
                    good = False
            else:
                if not wired:
                    fail("channel_unrouted", nm, "no wire")
                    good = False
                if same:
                    fail("channel_pins_touch", nm, "pins touch across a planned channel")
                    good = False
        res["ok"] += good
    missing = [n for n in want if n not in seen]
    if missing:
        res["fails"]["missing_seam_net"] = len(missing)
        res["examples"]["missing_seam_net"] = missing[:5]
    try:
        txt = open(os.environ.get("DRC", "/work/die_drc.rpt")).read()
        res["drc_markers"] = txt.count("violation type")
    except OSError:
        res["drc_markers"] = None
    res["verdict"] = "PASS" if (res["ok"] == res["plan_seams"] == res["found"] and not res["fails"]
                                and not res.get("nonseam_unrouted_n") and not res["drc_markers"]) else "FAIL"
    json.dump(res, open(os.environ["OUT"], "w"), indent=1)
    print(f"SEAM_AUDIT {res['verdict']} seams ok {res['ok']}/{res['plan_seams']} (abutted {res['plan_abutted']}, "
          f"channel {res['plan_channel']}) fails {res['fails']} nonseam unrouted {res.get('nonseam_unrouted_n', 0)} "
          f"drc {res['drc_markers']} layer-mismatch-overlaps {res['layer_mismatch_xy_overlap']}")


main()
