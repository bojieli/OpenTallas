"""opentools shared plan schema 'opentools.plan/1' (owner of the schema: OSS-CLKPLAN-1).

One JSON file describes a die (or a block) at planning time; every opentools tool reads it and may add its own
output section.  All lengths are micrometres, all delays picoseconds, origin at the die lower-left corner.
See opentools/common/README.md for the field list.  This module only loads, checks and saves; it has no
technology knowledge.

    P = load(path)          # dict, validated, defaults filled
    errs = validate(P)      # list of strings (empty = OK)
    save(P, path)
"""
import copy
import json
import math
from pathlib import Path

SCHEMA = "opentools.plan/1"
MACRO_KINDS = ("hard_core", "phy", "blockage")
SHIELD_MODES = ("none", "drawn", "pg_flank")
CORNERS = ("TT", "FF")
FEED_KINDS = ("forward", "spine")

DEFAULT_CLOCK = dict(name="clk", period_ps=None, entry=None, layers={"H": None, "V": None},
                     ndr=dict(width_um=None, space_um=None, shield="none", shield_width_um=None),
                     target_latency_ps=None, skew_target_ps=80.0, min_crossing_margin_ps=100.0,
                     crossing_mode="phase", count_aligned=None, ring_phase=None)


def rect_ok(r):
    return (isinstance(r, (list, tuple)) and len(r) == 4 and all(isinstance(v, (int, float)) for v in r)
            and r[2] > r[0] and r[3] > r[1])


def validate(P):
    e = []
    if P.get("schema") != SCHEMA:
        e.append(f"schema must be {SCHEMA!r}")
    d = P.get("die") or {}
    if not (d.get("w", 0) > 0 and d.get("h", 0) > 0):
        e.append("die.w and die.h (um) must be > 0")
    names = set()
    for m in P.get("macros", []):
        n = m.get("name")
        if not n or n in names:
            e.append(f"macro name missing or duplicate: {n!r}")
        names.add(n)
        if not rect_ok(m.get("rect")):
            e.append(f"macro {n}: rect [x0,y0,x1,y1] with x1>x0, y1>y0 required")
        if m.get("kind", "hard_core") not in MACRO_KINDS:
            e.append(f"macro {n}: kind must be one of {MACRO_KINDS}")
        for cp in m.get("clock_pins", []):
            if not (isinstance(cp.get("xy"), (list, tuple)) and len(cp["xy"]) == 2):
                e.append(f"macro {n}: clock pin {cp.get('name')} needs xy")
            for c, v in (cp.get("insertion_ps") or {}).items():
                if not (isinstance(v, (int, float)) and v >= 0):
                    e.append(f"macro {n}: insertion_ps[{c}] must be >= 0")
    snames = {s.get("name") for s in P.get("sinks", [])}
    for s in P.get("sinks", []):
        if not (isinstance(s.get("xy"), (list, tuple)) and len(s["xy"]) == 2):
            e.append(f"sink {s.get('name')}: xy required")
    regs = {r.get("name") for r in P.get("regions", [])}
    for r in P.get("regions", []):
        if not rect_ok(r.get("rect")):
            e.append(f"region {r.get('name')}: rect required")
    allpins = snames | {f"{m['name']}/{cp.get('name', 'clk')}" for m in P.get("macros", []) for cp in m.get("clock_pins", [])}
    for c in P.get("crossings", []):
        for k in ("a", "b"):
            if c.get(k) not in allpins:
                e.append(f"crossing {c.get('name')}: {k}={c.get(k)!r} is not a sink or macro clock pin")
    for g in P.get("pg", []):
        if g.get("dir") not in ("H", "V") or not g.get("pitch_um", 0) > 0:
            e.append(f"pg {g.get('layer')}: dir H|V and pitch_um > 0 required")
        for s in g.get("stripes", []):
            if not (s.get("width_um", 0) > 0 and 0 <= s.get("offset_um", -1) < g.get("pitch_um", 0) + 1e-9):
                e.append(f"pg {g.get('layer')}: stripe width_um > 0 and 0 <= offset_um < pitch_um")
    for w in P.get("pin_windows", []):
        if not w.get("layer") or not (("rows" in w) or ("positions_um" in w)):
            e.append("pin_windows: layer + rows{pitch_um,offset_um,half_um} or positions_um[] + half_um required")
    ck = P.get("clock", {})
    if ck.get("ndr", {}).get("shield", "none") not in SHIELD_MODES:
        e.append(f"clock.ndr.shield must be one of {SHIELD_MODES}")
    if ck.get("entry") is not None and not (isinstance(ck["entry"], (list, tuple)) and len(ck["entry"]) == 2):
        e.append("clock.entry must be [x, y] or null (planner chooses)")
    for r in P.get("regions", []):
        if r.get("partition") is not None and not isinstance(r["partition"], str):
            e.append(f"region {r.get('name')}: partition must be a name")
    for f in P.get("feeds", []):
        if f.get("dst") not in regs or not (f.get("src") == "root" or f.get("src") in regs):
            e.append(f"feed {f.get('name')}: src must be 'root' or a region, dst a region")
        if not (isinstance(f.get("len_um"), (int, float)) and f["len_um"] >= 0):
            e.append(f"feed {f.get('name')}: len_um >= 0 required")
        if f.get("tap", "root") not in ("root", "leaf"):
            e.append(f"feed {f.get('name')}: tap must be 'root' or 'leaf'")
        if f.get("kind", "forward") not in FEED_KINDS:
            e.append(f"feed {f.get('name')}: kind must be one of {FEED_KINDS}")
    dsts = [f.get("dst") for f in P.get("feeds", [])]
    for d in {d for d in dsts if dsts.count(d) > 1}:
        e.append(f"region {d}: more than one incoming feed (feeds must form a tree)")
    return e


def fill_defaults(P):
    P = copy.deepcopy(P)
    P.setdefault("macros", [])
    P.setdefault("sinks", [])
    P.setdefault("regions", [])
    P.setdefault("crossings", [])
    P.setdefault("pg", [])
    P.setdefault("layers", [])
    P.setdefault("pin_windows", [])
    P.setdefault("channels", [])
    P.setdefault("feeds", [])
    ck = copy.deepcopy(DEFAULT_CLOCK)
    user = P.get("clock", {})
    for k, v in user.items():
        if isinstance(v, dict) and isinstance(ck.get(k), dict):
            ck[k].update(v)
        else:
            ck[k] = v
    P["clock"] = ck
    for m in P["macros"]:
        m.setdefault("kind", "hard_core")
        m.setdefault("clock_pins", [])
        m.setdefault("islands", False)
    return P


def load(path):
    P = json.loads(Path(path).read_text())
    P = fill_defaults(P)
    e = validate(P)
    if e:
        raise ValueError(f"{path}: invalid {SCHEMA} plan:\n  " + "\n  ".join(e))
    return P


def save(P, path):
    Path(path).write_text(json.dumps(P, indent=1, default=_json_default) + "\n")


def _json_default(o):
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if hasattr(o, "tolist"):
        return o.tolist()
    raise TypeError(type(o))


def keepouts(P, kinds=MACRO_KINDS):
    """[(x0, y0, x1, y1, name, kind)] of the macros (clock cells may not sit inside them)."""
    return [tuple(m["rect"]) + (m["name"], m["kind"]) for m in P["macros"] if m["kind"] in kinds]


def clock_sinks(P):
    """every clock tap the die tree must reach: explicit sinks + every macro clock pin.
    -> [dict(name, xy, insertion_ps{TT,FF}, region, macro, weight)]"""
    out = []
    reg_of = _region_lookup(P)
    for s in P["sinks"]:
        out.append(dict(name=s["name"], xy=tuple(map(float, s["xy"])), insertion_ps=dict(s.get("insertion_ps") or {}),
                        region=s.get("region") or reg_of(s["xy"]), macro=None, weight=float(s.get("weight", 1.0))))
    for m in P["macros"]:
        for cp in m["clock_pins"]:
            xy = tuple(map(float, cp["xy"]))
            out.append(dict(name=f"{m['name']}/{cp.get('name', 'clk')}", xy=xy, insertion_ps=dict(cp.get("insertion_ps") or {}),
                            region=cp.get("region") or m.get("region") or reg_of(xy), macro=m["name"],
                            weight=float(cp.get("sinks", 1))))
    return out


def _region_lookup(P):
    regs = [(r["rect"], r["name"]) for r in P["regions"]]

    def f(xy):
        for r, n in regs:
            if r[0] <= xy[0] <= r[2] and r[1] <= xy[1] <= r[3]:
                return n
        return None
    return f
