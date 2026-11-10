"""Pin audit (OpenROAD python): every placed pin of a partition / die ODB against the plan's exact pins.

    openroad -python -exit tools/die_plan/pin_audit.py   with env ODB=<db> PINS=<kit pins.json> OUT=<json>
    (pins.json from gen.py phys: bus, bit, layer, x, y, face in the type frame)

A pin passes when its BTerm has one box on the plan layer whose centre lies on the plan coordinate along the face
(+/- 0.001 um) and which touches the plan face.  Output: {pins, ok, missing, wrong_layer, wrong_place, extra}.
Interior pins (face "island" or any non-N/E/S/W face, e.g. the 12.2a1 pushdown centre clock entry): the box centre must
lie on the plan (x, y) in BOTH coordinates (+/- 0.001 um) and the box must lie inside the die; no face contact.
Scalar ports (bit None) are keyed by the bare port name.
"""
import json
import math
import re
import os

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_pin_contract import native_rects_match

TOL = 0.001
FACES = "NESW"
INTERIOR = re.compile(r"^(clk(_t[0-9]+|_c[0-9]+)?|arst_n|rst_o_[0-9]+|start_i|start_o_[0-9]+|ft_(ck|rst)_[io](_[0-9]+)?|mp_isl\w*)$")
# Planned interior ports that the physical pin audit does NOT carry as strict rows (clock taps, the reset tap, the
# pushdown feed-throughs: checked by the clock / ft_ports gates).  Planned reset/START wavefront outs (rst_o_<k>,
# start_i, start_o_<k>) ARE audited at their exact island centre, so a native ABI that packs them as 1-bit vectors
# (rst_o_0[0]) resolves through scalar_aliases instead of counting as extra (DIE-QC-84 11-06, SU2 pin readback).
AUDIT_EXCLUDED = re.compile(r"^(clk(_t[0-9]+|_c[0-9]+)?|arst_n|ft_(ck|rst)_[io](_[0-9]+)?|mp_isl\w*)$")


def pin_key(p):
    """plan pin -> BTerm name: bus[bit], or the bare bus name for a scalar port (bit None)."""
    return p["bus"] if p.get("bit") is None else f"{p['bus']}[{p['bit']}]"


def scalar_aliases(want, actual_names):
    """Unique boundary-bit identity only: bare scalar <-> vector[0].

    Both the complete plan and actual BTerm inventory must contain exactly
    one bit of this bus. Ambiguous dual spellings and any wider bus stay exact.
    """
    planned = {}
    for name, pin in want.items():
        planned.setdefault(pin["bus"], []).append(name)
    actual = {}
    for name in actual_names:
        m = re.fullmatch(r"(.*)\[([0-9]+)\]", name)
        base = m[1] if m else name
        actual.setdefault(base, []).append(name)
    aliases = {}
    for bus, names in planned.items():
        if len(names) != 1 or len(actual.get(bus, [])) != 1:
            continue
        pn, an = names[0], actual[bus][0]
        if pn == an or want[pn].get("bit") not in (None, 0):
            continue
        if {pn, an} == {bus, bus + "[0]"}:
            aliases[an] = pn
    return aliases


def within_tolerance(delta):
    """Include the declared 1 nm boundary despite binary subtraction roundoff."""
    return delta <= TOL or math.isclose(delta, TOL, rel_tol=0.0, abs_tol=1e-12)


def box_ok(p, box, W, H):
    """one BTerm box (x0, y0, x1, y1 in um) against plan pin p on a W x H die."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    f = p["face"]
    if f not in FACES:                      # interior pin (island clock entry): exact (x, y), inside the die
        return within_tolerance(abs(cx - p["x"])) and within_tolerance(abs(cy - p["y"])) and x0 >= -TOL and y0 >= -TOL and x1 <= W + TOL and y1 <= H + TOL
    along = within_tolerance(abs(cy - p["y"])) if f in "EW" else within_tolerance(abs(cx - p["x"]))
    edge = {"E": within_tolerance(abs(x1 - W)), "W": within_tolerance(abs(x0)), "N": within_tolerance(abs(y1 - H)), "S": within_tolerance(abs(y0))}[f]
    return along and edge


def declared_clock_ports(pins_path):
    """Only explicit core clock roles exempt otherwise unplanned interior ports."""
    try:
        with open(os.path.join(os.path.dirname(pins_path), "core.json")) as stream:
            roles = json.load(stream).get("boundary_role", {})
    except (OSError, ValueError, AttributeError):
        return set()
    if not isinstance(roles, dict):
        return set()
    return {name for name, role in roles.items() if role == "clk"}


def accepted_count_strap_bits(evidence):
    """{bit names} of parent-tied count straps, from the kit's count_strap_evidence.json (count_strap_evidence.py).

    A strap counts only if the plan declares it in count_straps, it is a bound-only input of that width, and every
    instance of the type ties it to a literal of that width.  Anything else stays an extra pin.
    """
    if not isinstance(evidence, dict) or not evidence.get("instances"):
        return set()
    bound = {r.get("port"): (r.get("dir"), r.get("width")) for r in evidence.get("bound_only_pins") or []}
    bits = set()
    for strap in evidence.get("plan_count_straps") or []:
        name, width = strap.get("name"), strap.get("width")
        ties = (evidence.get("parent_ties") or {}).get(name) or {}
        if bound.get(name) != ("input", width):
            continue
        if not all(re.fullmatch(rf"{width}'[bBdDhH][0-9a-fA-F_]+", ties.get(i) or "") for i in evidence["instances"]):
            continue
        bits |= {f"{name}[{b}]" for b in range(width)}
        if width == 1:
            bits.add(name)
    return bits


def load_count_strap_evidence(pins_path):
    try:
        with open(os.path.join(os.path.dirname(pins_path), "count_strap_evidence.json")) as stream:
            return json.load(stream)
    except (OSError, ValueError):
        return None


def main():
    import odb  # noqa: E402  (OpenROAD python)
    db = odb.dbDatabase.create()
    db = odb.read_db(db, os.environ["ODB"])
    block = db.getChip().getBlock()
    dbu = block.getDefUnits()
    die = block.getDieArea()
    W, H = die.xMax() / dbu, die.yMax() / dbu
    want = {pin_key(p): p for p in json.load(open(os.environ["PINS"]))}
    clock_ports = declared_clock_ports(os.environ["PINS"])
    tied_straps = accepted_count_strap_bits(load_count_strap_evidence(os.environ["PINS"]))
    res = dict(pins=len(want), ok=0, missing=[], wrong_layer=[], wrong_place=[], extra=[], count_straps_accepted=[])
    seen = set()
    aliases = scalar_aliases(want, [bt.getName() for bt in block.getBTerms()])
    res["scalar_aliases"] = aliases
    for bt in block.getBTerms():
        n = aliases.get(bt.getName(), bt.getName())
        if n not in want:
            # clock taps (R4: clk, clk_t<i>), the reset tap and reset wavefront outs are interior die pins, not face pins;
            # so are the 12.2a1 pushdown island feed-through ports (ft_ck_i/o, ft_rst_i/o, mp_isl*: die-owned, checked by
            # the ft_ports / pushdown gates, not by the face-pin table)
            if n not in clock_ports and not INTERIOR.match(n) and not bt.getSigType() in ("POWER", "GROUND"):
                res["count_straps_accepted" if n in tied_straps else "extra"].append(n)
            continue
        seen.add(n)
        p = want[n]
        boxes = [(b.getTechLayer().getName(), b.xMin() / dbu, b.yMin() / dbu, b.xMax() / dbu, b.yMax() / dbu)
                 for bp in bt.getBPins() for b in bp.getBoxes()]
        lay = [b for b in boxes if b[0] == p["layer"]]
        if not lay:
            res["wrong_layer"].append([n, p["layer"], sorted({b[0] for b in boxes})])
            continue
        if "native_rects" in p:
            if native_rects_match(p, boxes, dbu):
                res["ok"] += 1
            else:
                res["wrong_place"].append([n, p, boxes])
            continue
        if any(box_ok(p, b[1:], W, H) for b in lay):
            res["ok"] += 1
        else:
            res["wrong_place"].append([n, p, lay[0]])
    res["missing"] = sorted(set(want) - seen)
    for k in ("missing", "wrong_layer", "wrong_place", "extra"):
        res[k + "_n"] = len(res[k])
        res[k] = res[k][:20]
    res["count_straps_accepted_n"] = len(res["count_straps_accepted"])
    res["verdict"] = "PASS" if res["ok"] == res["pins"] and not res["extra_n"] else "FAIL"
    json.dump(res, open(os.environ["OUT"], "w"), indent=1)
    print(f"PIN_AUDIT {res['verdict']} {res['ok']}/{res['pins']} missing {res['missing_n']} wrong_layer "
          f"{res['wrong_layer_n']} wrong_place {res['wrong_place_n']} extra {res['extra_n']}")
    return 0 if res["verdict"] == "PASS" else 1


if os.environ.get("ODB"):   # run under openroad -python with ODB/PINS/OUT; importable for tests
    raise SystemExit(main())
