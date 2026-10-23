"""die_plan.json schema, loader and validator (TOPDOWN-PLAN, owner-approved 2026-10-23).

One die_plan.json per die (physical/die_plan/<die>/die_plan.json) is the single source the G0 checker and every
generator (partition wrapper RTL, partition physical spec, latency table, die assembly) read.  The full field reference
is tools/die_plan/README.md; the machine-readable JSON schema is tools/die_plan/die_plan.schema.json (written from
SCHEMA below by `python3 tools/die_plan/schema.py dump-schema`).

    python3 tools/die_plan/schema.py validate PLAN.json        # structure + references; exit 1 on error
    python3 tools/die_plan/schema.py dump-schema [OUT.json]

Conventions (binding for every tool):
- Units are um and ps.  The die frame has its origin at the die's lower-left corner.
- A partition instance is placed with `origin_um` = the lower-left corner of its placed bounding box and `orient`
  (R0, MX, MY, R180; as DEF/ODB).  Coordinates inside `partition_types` are in the TYPE frame (R0, origin lower-left).
- A port is one inter-partition signal bundle on ONE shared face.  `face` is the face of the SOURCE partition in the
  DIE frame; the destination uses the opposite face.  `window_um` = [lo, hi] along that face in DIE coordinates
  (y for E/W faces, x for N/S faces).  For a port whose src is "@die", `face` is the dst partition's face on the
  die edge.  Both partitions get pins at exactly the same die coordinates (pin_positions()).
- Every port is registered on both sides (a boundary flop at the source pin and at the destination pin).
- A feedthrough slot `S` of a partition type defines two buses `S_i` (in, on `in_face`) and `S_o` (out, on `out_face`),
  with `stations` reset-less data registers (+ one reset epoch bit) between them.
- A lane is an ordered list of ports; consecutive ports meet inside a partition at the `_i`/`_o` buses of one ft slot.
  Latency (cycles from the source's out flop to the destination's in flop) = sum(stations of crossed slots) + 1
  + fixed_cycles (lane_latency()).
- Part name "@die" in a port endpoint is the die boundary (bumps / die IO); its bus is the die-level port name.
"""
import json
import math
import sys
from pathlib import Path

SCHEMA_ID = "opentallas.die_plan.v1"
DIE_PART = "@die"
FACES = ("N", "S", "E", "W")
OPP = dict(N="S", S="N", E="W", W="E")
ORIENTS = ("R0", "MX", "MY", "R180")
KINDS = ("data", "ctl", "clock", "reset")
STATUS = ("reuse", "rework", "new")

# ASAP7 ORFS tracks (platform openRoad/make_tracks.tcl): H layers use y tracks, V layers x tracks.
ASAP7_LAYERS = [
    dict(name="M2", dir="H", pitch_um=0.036, offset_um=0.045),
    dict(name="M3", dir="V", pitch_um=0.036, offset_um=0.009),
    dict(name="M4", dir="H", pitch_um=0.048, offset_um=0.012),
    dict(name="M5", dir="V", pitch_um=0.048, offset_um=0.012),
    dict(name="M6", dir="H", pitch_um=0.064, offset_um=0.016),
    dict(name="M7", dir="V", pitch_um=0.064, offset_um=0.016),
    dict(name="M8", dir="H", pitch_um=0.080, offset_um=0.116),
    dict(name="M9", dir="V", pitch_um=0.080, offset_um=0.116),
]
# 8.64 um = lcm(row 0.27, site 0.054, M4..M9 pitches): partition origins/outlines on this grid keep rows, sites and
# tracks identical in the die and partition frames (also the PG stripe pitch of the closed S81 kits).
GRID_UM = 8.64

DEFAULT_BUDGETS = dict(face_pins_per_um=6.0, face_pin_layers=2, face_window_um=10.0, pin_track_max=0.6,
                       cut_ratio_max=0.6, cut_step_um=250.0, pin_reg_p90_um=30.0)
DEFAULT_CLOCK = dict(insertion_ps=250.0, insertion_tol_ps=40.0, neighbour_skew_ps=80.0, face_xing="budgeted")
DEFAULT_RESET = dict(sync_stages=2, data_reset=False, epoch_bit=True, release="counted")
DEFAULT_LAYER_BUDGET = dict(partition_signal_max="M7", die_layers=["M8", "M9"],
                            die_use=["clock_spine", "pg", "ft_reserved"],
                            cut_avail={"M8": 0.6, "M9": 0.6})

# ---------------------------------------------------------------------------------------------------------- schema
_num = {"type": "number"}
_nonneg = {"type": "number", "minimum": 0}
_pos = {"type": "number", "exclusiveMinimum": 0}
_xy = {"type": "array", "items": _num, "minItems": 2, "maxItems": 2}
_wh = {"type": "array", "items": _pos, "minItems": 2, "maxItems": 2}
_rect = {"type": "array", "items": _num, "minItems": 4, "maxItems": 4}
_name = {"type": "string", "minLength": 1}
_layer = {"type": "string", "pattern": "^M[1-9]$"}
_end = {"type": "object", "required": ["part", "bus"], "additionalProperties": False,
        "properties": {"part": _name, "bus": _name}}

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": SCHEMA_ID,
    "title": "OpenTallas die plan (TOPDOWN-PLAN)",
    "type": "object",
    "required": ["schema", "die", "partition_types", "partitions", "ports", "lanes"],
    "additionalProperties": False,
    "properties": {
        "schema": {"const": SCHEMA_ID},
        "note": {"type": "string"},
        "die": {
            "type": "object", "required": ["name", "outline_um", "period_ps", "reach_um"],
            "additionalProperties": False,
            "properties": {
                "name": _name, "label": {"type": "string"}, "tech": {"enum": ["asap7"]},
                "outline_um": _wh, "period_ps": _pos,
                "reach_um": _pos,                    # measured one-cycle hop (REACH-M89): S81 1500, KV 1200, QC 1000, HBM 1000
                "rep_um": _pos,                      # repeater spacing (450)
                "grid_um": _pos,                     # partition origin / outline grid (8.64)
                "rows": {"type": "object", "additionalProperties": False,
                         "properties": {"site": _name, "height_um": _pos, "site_w_um": _pos}},
                "layers": {"type": "array", "items": {
                    "type": "object", "required": ["name", "dir", "pitch_um", "offset_um"],
                    "additionalProperties": False,
                    "properties": {"name": _layer, "dir": {"enum": ["H", "V"]}, "pitch_um": _pos,
                                   "offset_um": _nonneg}}},
                "layer_budget": {"type": "object", "additionalProperties": False, "properties": {
                    "partition_signal_max": _layer,
                    "die_layers": {"type": "array", "items": _layer},
                    "die_use": {"type": "array", "items": {"enum": ["clock_spine", "pg", "ft_reserved", "reset"]}},
                    "cut_avail": {"type": "object", "additionalProperties": {"type": "number", "minimum": 0,
                                                                            "maximum": 1}}}},
                "channels": {"type": "array", "items": {   # die-level gaps between partitions, each with its reason
                    "type": "object", "required": ["rect_um", "reason"], "additionalProperties": False,
                    "properties": {"rect_um": _rect, "reason": {"type": "string", "minLength": 3}}}},
                "pg": {"type": "object", "additionalProperties": False, "properties": {
                    "partition_pg_max": _layer,
                    "grid": {"type": "array", "items": {
                        "type": "object", "required": ["layer", "width_um", "pitch_um", "offset_um"],
                        "additionalProperties": False,
                        "properties": {"layer": _layer, "width_um": _pos, "pitch_um": _pos, "offset_um": _nonneg,
                                       "nets": {"type": "array", "items": _name}}}}}},
            }},
        "partition_types": {
            "type": "object", "minProperties": 1,
            "additionalProperties": {
                "type": "object", "required": ["module", "outline_um"], "additionalProperties": False,
                "properties": {
                    "module": _name,                 # generated wrapper module name
                    "outline_um": _wh,
                    "hard": {"type": "boolean"},     # hard IP (PHY, closed macro used as-is): no generated wrapper
                    "kit": {"type": "string"},
                    "note": {"type": "string"},
                    "buses": {"type": "array", "items": {
                        "type": "object", "required": ["name", "dir", "width"], "additionalProperties": False,
                        "properties": {"name": _name, "dir": {"enum": ["in", "out"]},
                                       "width": {"type": "integer", "minimum": 1}, "kind": {"enum": list(KINDS)},
                                       "leaf": {"type": "string"},      # "<inst>.<port>" the bus binds to inside
                                       "note": {"type": "string"}}}},
                    "ft_slots": {"type": "array", "items": {
                        "type": "object", "required": ["name", "in_face", "out_face", "width"],
                        "additionalProperties": False,
                        "properties": {"name": _name, "in_face": {"enum": list(FACES)},
                                       "out_face": {"enum": list(FACES)},
                                       "width": {"type": "integer", "minimum": 1},
                                       "stations": {"type": "integer", "minimum": 1},
                                       "regs_um": {"type": "array", "items": _xy},   # station sites, type frame
                                       "layer": _layer}}},                          # in-partition ft layer (<= M7)
                    "clock": {"type": "object", "additionalProperties": False, "properties": {
                        "tap_um": _xy, "layer": _layer, "insertion_ps": _pos, "insertion_tol_ps": _nonneg}},
                    "reset": {"type": "object", "additionalProperties": False, "properties": {
                        "tap_um": _xy, "sync_stages": {"type": "integer", "minimum": 2}}},
                    "contents": {"type": "array", "items": {
                        "type": "object", "required": ["inst", "module", "status"], "additionalProperties": False,
                        "properties": {"inst": _name, "module": _name, "status": {"enum": list(STATUS)},
                                       "kit": {"type": "string"}, "geom_pass": {"type": "string"},
                                       "origin_um": _xy, "outline_um": _wh, "note": {"type": "string"}}}},
                    "channels": {"type": "array", "items": {
                        "type": "object", "required": ["rect_um", "reason"], "additionalProperties": False,
                        "properties": {"rect_um": _rect, "reason": {"type": "string", "minLength": 3}}}},
                    "ft_track_frac": {"type": "number", "minimum": 0, "maximum": 1},
                }}},
        "partitions": {"type": "array", "minItems": 1, "items": {
            "type": "object", "required": ["name", "type", "origin_um"], "additionalProperties": False,
            "properties": {"name": _name, "type": _name, "origin_um": _xy, "orient": {"enum": list(ORIENTS)},
                           "note": {"type": "string"}}}},
        "ports": {"type": "array", "items": {
            "type": "object", "required": ["id", "src", "dst", "width", "face", "layers", "window_um"],
            "additionalProperties": False,
            "properties": {"id": _name, "src": _end, "dst": _end, "width": {"type": "integer", "minimum": 1},
                           "kind": {"enum": list(KINDS)}, "face": {"enum": list(FACES)},
                           "layers": {"type": "array", "items": _layer, "minItems": 1, "maxItems": 2},
                           "window_um": {"type": "array", "items": _num, "minItems": 2, "maxItems": 2},
                           "order": {"enum": ["lsb_low", "lsb_high"]}, "note": {"type": "string"}}}},
        "lanes": {"type": "array", "items": {
            "type": "object", "required": ["id", "ports"], "additionalProperties": False,
            "properties": {"id": _name, "ports": {"type": "array", "items": _name, "minItems": 1},
                           "fixed_cycles": {"type": "integer", "minimum": 0},
                           "reach_um": _pos, "param": {"type": "string", "pattern": "^[A-Z][A-Z0-9_]*$"},
                           "note": {"type": "string"}}}},
        "clock": {"type": "object", "additionalProperties": False, "properties": {
            "source": _end, "insertion_ps": _pos, "insertion_tol_ps": _nonneg, "neighbour_skew_ps": _pos,
            "face_xing": {"enum": ["budgeted", "forwarded_landing"]},
            "spine": {"type": "object", "additionalProperties": False, "properties": {
                "layers": {"type": "array", "items": _layer}, "root_um": _xy,
                "topology": {"enum": ["htree", "fishbone", "mesh"]}}}}},
        "reset": {"type": "object", "additionalProperties": False, "properties": {
            "source": _end, "sync_stages": {"type": "integer", "minimum": 2},
            "data_reset": {"const": False}, "epoch_bit": {"const": True}, "release": {"enum": ["counted"]}}},
        "latency": {"type": "object", "additionalProperties": False, "properties": {
            "lanes": {"type": "object", "additionalProperties": {
                "type": "object", "required": ["cycles"], "additionalProperties": False,
                "properties": {"cycles": {"type": "integer", "minimum": 1}, "stations": {"type": "integer"},
                               "faces": {"type": "integer"}, "fixed": {"type": "integer"},
                               "param": {"type": "string"}}}}}},
        "budgets": {"type": "object", "additionalProperties": False, "properties": {
            k: ({"type": "integer", "minimum": 1} if k == "face_pin_layers" else _pos) for k in DEFAULT_BUDGETS}},
    },
}


# ------------------------------------------------------------------------------- structural validator (subset)
def _check(v, s, path, errs):
    """Minimal draft-2020-12 subset (type, const, enum, required, properties, additionalProperties, items, min/max*,
    pattern, minLength, minProperties).  No external dependency, so it runs on every fleet host."""
    import re
    if "const" in s and v != s["const"]:
        errs.append(f"{path}: must be {s['const']!r}")
        return
    if "enum" in s and v not in s["enum"]:
        errs.append(f"{path}: {v!r} not in {s['enum']}")
        return
    t = s.get("type")
    ok = {"object": lambda x: isinstance(x, dict), "array": lambda x: isinstance(x, list),
          "string": lambda x: isinstance(x, str), "boolean": lambda x: isinstance(x, bool),
          "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
          "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)}
    if t and not ok[t](v):
        errs.append(f"{path}: expected {t}, got {type(v).__name__}")
        return
    if t == "object":
        for r in s.get("required", ()):
            if r not in v:
                errs.append(f"{path}: missing '{r}'")
        if len(v) < s.get("minProperties", 0):
            errs.append(f"{path}: needs >= {s['minProperties']} entries")
        props = s.get("properties", {})
        addl = s.get("additionalProperties", True)
        for k, x in v.items():
            if k in props:
                _check(x, props[k], f"{path}.{k}", errs)
            elif addl is False:
                errs.append(f"{path}: unknown key '{k}'")
            elif isinstance(addl, dict):
                _check(x, addl, f"{path}.{k}", errs)
    elif t == "array":
        if len(v) < s.get("minItems", 0):
            errs.append(f"{path}: needs >= {s['minItems']} items")
        if "maxItems" in s and len(v) > s["maxItems"]:
            errs.append(f"{path}: needs <= {s['maxItems']} items")
        if "items" in s:
            for i, x in enumerate(v):
                _check(x, s["items"], f"{path}[{i}]", errs)
    elif t == "string":
        if len(v) < s.get("minLength", 0):
            errs.append(f"{path}: empty")
        if "pattern" in s and not re.search(s["pattern"], v):
            errs.append(f"{path}: {v!r} does not match {s['pattern']}")
    elif t in ("number", "integer"):
        if "minimum" in s and v < s["minimum"]:
            errs.append(f"{path}: {v} < {s['minimum']}")
        if "maximum" in s and v > s["maximum"]:
            errs.append(f"{path}: {v} > {s['maximum']}")
        if "exclusiveMinimum" in s and v <= s["exclusiveMinimum"]:
            errs.append(f"{path}: {v} <= {s['exclusiveMinimum']}")


def validate_structure(obj):
    errs = []
    _check(obj, SCHEMA, "$", errs)
    return errs


# ------------------------------------------------------------------------------------------------------- loader
class Plan:
    """Loaded plan with defaults filled and lookup helpers.  `raw` is the JSON exactly as read."""

    def __init__(self, raw, path=None):
        self.raw = raw
        self.path = path
        d = raw["die"]
        self.die = d
        self.name = d["name"]
        self.W, self.H = d["outline_um"]
        self.reach = float(d["reach_um"])
        self.rep_um = float(d.get("rep_um", 450.0))
        self.grid = float(d.get("grid_um", GRID_UM))
        self.layers = {L["name"]: L for L in d.get("layers", ASAP7_LAYERS)}
        self.layer_budget = dict(DEFAULT_LAYER_BUDGET, **d.get("layer_budget", {}))
        self.types = raw["partition_types"]
        self.parts = {p["name"]: p for p in raw["partitions"]}
        self.ports = {p["id"]: p for p in raw["ports"]}
        self.lanes = {l["id"]: l for l in raw["lanes"]}
        self.clock = dict(DEFAULT_CLOCK, **raw.get("clock", {}))
        self.reset = dict(DEFAULT_RESET, **raw.get("reset", {}))
        self.budgets = dict(DEFAULT_BUDGETS, **raw.get("budgets", {}))

    # -- partitions
    def ptype(self, part):
        return self.types[self.parts[part]["type"]]

    def orient(self, part):
        return self.parts[part].get("orient", "R0")

    def rect(self, part):
        """placed bbox in the die frame: (x0, y0, x1, y1)."""
        if part == DIE_PART:
            return (0.0, 0.0, float(self.W), float(self.H))
        p = self.parts[part]
        w, h = self.ptype(part)["outline_um"]
        x0, y0 = p["origin_um"]
        return (x0, y0, x0 + w, y0 + h)

    def to_die(self, part, pt):
        """type-frame point -> die frame."""
        p = self.parts[part]
        w, h = self.ptype(part)["outline_um"]
        x, y = pt
        o = self.orient(part)
        X, Y = {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]
        return (p["origin_um"][0] + X, p["origin_um"][1] + Y)

    def to_type(self, part, pt):
        """die-frame point -> type frame (the four orients are involutions)."""
        p = self.parts[part]
        w, h = self.ptype(part)["outline_um"]
        x, y = pt[0] - p["origin_um"][0], pt[1] - p["origin_um"][1]
        o = self.orient(part)
        return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]

    def type_face(self, part, die_face):
        """die-frame face of a placed partition -> face in its type frame."""
        o = self.orient(part)
        if o in ("MX", "R180") and die_face in "NS":
            return OPP[die_face]
        if o in ("MY", "R180") and die_face in "EW":
            return OPP[die_face]
        return die_face

    def die_face(self, part, type_face):
        return self.type_face(part, type_face)   # involution

    def buses(self, part):
        """{bus name: dict(dir, width, kind, slot?)} incl. the _i/_o buses of every ft slot."""
        if part == DIE_PART:
            return None
        tn = self.parts[part]["type"]
        if not hasattr(self, "_bus_cache"):
            self._bus_cache = {}
        if tn not in self._bus_cache:
            self._bus_cache[tn] = self._type_buses(tn)
        return self._bus_cache[tn]

    def _type_buses(self, tn):
        t = self.types[tn]
        out = {b["name"]: dict(b) for b in t.get("buses", [])}
        for s in t.get("ft_slots", []):
            out[s["name"] + "_i"] = dict(name=s["name"] + "_i", dir="in", width=s["width"], kind="data",
                                         slot=s["name"], face=s["in_face"])
            out[s["name"] + "_o"] = dict(name=s["name"] + "_o", dir="out", width=s["width"], kind="data",
                                         slot=s["name"], face=s["out_face"])
        return out

    def slot(self, part, name):
        for s in self.ptype(part).get("ft_slots", []):
            if s["name"] == name:
                return s
        return None

    # -- ports
    def port_pins(self, pid):
        return pin_positions(self.ports[pid], self.layers)

    def port_point(self, pid):
        """centre of the port window on its face, die frame."""
        pr = self.ports[pid]
        x0, y0, x1, y1 = self.rect(self.face_part(pid))
        f = pr["face"]
        c = (pr["window_um"][0] + pr["window_um"][1]) / 2.0
        return {"E": (x1, c), "W": (x0, c), "N": (c, y1), "S": (c, y0)}[f]

    def face_part(self, pid):
        """the partition whose face `face` names: src, or dst when src is the die boundary."""
        pr = self.ports[pid]
        return pr["src"]["part"] if pr["src"]["part"] != DIE_PART else pr["dst"]["part"]

    # -- lanes
    def lane_crossings(self, lid):
        """[(part, slot, in_port, out_port)] for every partition the lane crosses (between consecutive ports)."""
        ln = self.lanes[lid]
        out = []
        for a, b in zip(ln["ports"], ln["ports"][1:]):
            pa, pb = self.ports[a], self.ports[b]
            part = pa["dst"]["part"]
            slot = pa["dst"]["bus"][:-2] if pa["dst"]["bus"].endswith("_i") else None
            out.append((part, slot, a, b))
        return out

    def lane_latency(self, lid):
        """dict(cycles, stations, faces, fixed): cycles from the source out flop to the destination in flop."""
        ln = self.lanes[lid]
        st = 0
        for part, slot, _, _ in self.lane_crossings(lid):
            s = self.slot(part, slot) if slot else None
            st += int(s.get("stations", 1)) if s else 1
        fixed = int(ln.get("fixed_cycles", 0))
        return dict(cycles=st + 1 + fixed, stations=st, faces=len(ln["ports"]), fixed=fixed)


def pin_positions(port, layers):
    """Deterministic pin assignment of one port, die frame: [(bit, layer, coord_um)] with coord along the face.

    Bits alternate over the port's layers (bit i -> layers[i % n]); on each layer the bits are spread evenly over
    [lo, hi] at an integer multiple of that layer's track pitch, snapped to offset + k * pitch.  Both partitions of a
    face use this same function, so their pins coincide by construction.  Raises ValueError if the window cannot hold
    the bits on whole tracks."""
    lo, hi = sorted(port["window_um"])
    names = port["layers"]
    w = int(port["width"])
    nl = len(names)
    rev = port.get("order", "lsb_low") == "lsb_high"
    out = []
    for li, ln in enumerate(names):
        L = layers[ln]
        p, off = L["pitch_um"], L["offset_um"]
        bits = list(range(li, w, nl))
        n = len(bits)
        if n == 0:
            continue
        k0 = math.ceil((lo - off) / p - 1e-9)
        k1 = math.floor((hi - off) / p + 1e-9)
        ntr = k1 - k0 + 1
        if ntr < n:
            raise ValueError(f"port {port['id']}: {n} bits on {ln} need {n} tracks, window has {max(ntr, 0)}")
        step = max(1, ntr // n)
        first = k0 + (ntr - step * (n - 1) - 1) // 2      # centre the used span in the window
        for j, b in enumerate(bits):
            slot = (n - 1 - j) if rev else j
            out.append((b, ln, round(off + (first + slot * step) * p, 6)))
    out.sort()
    return out


def load(path):
    raw = json.loads(Path(path).read_text())
    return raw


def validate(raw):
    """Structure + references + local consistency.  Returns a list of error strings (empty = valid).
    Geometric / budget checks (abutment, cuts, faces, hops) are the G0 checker's job (check.py)."""
    errs = validate_structure(raw)
    if errs:
        return errs
    P = Plan(raw)
    # names unique
    for what, lst, key in (("partition", raw["partitions"], "name"), ("port", raw["ports"], "id"),
                           ("lane", raw["lanes"], "id")):
        seen = set()
        for x in lst:
            if x[key] in seen:
                errs.append(f"{what} '{x[key]}' defined twice")
            seen.add(x[key])
    for tn, t in raw["partition_types"].items():
        names = [b["name"] for b in t.get("buses", [])] + \
            [s["name"] + sfx for s in t.get("ft_slots", []) for sfx in ("_i", "_o")]
        dup = {n for n in names if names.count(n) > 1}
        if dup:
            errs.append(f"type {tn}: bus names defined twice: {sorted(dup)}")
        for s in t.get("ft_slots", []):
            if s["in_face"] == s["out_face"]:
                errs.append(f"type {tn} slot {s['name']}: in_face == out_face")
            if "regs_um" in s and len(s["regs_um"]) != s.get("stations", 1):
                errs.append(f"type {tn} slot {s['name']}: {len(s['regs_um'])} regs_um for {s.get('stations', 1)} "
                            "stations")
        insts = [c["inst"] for c in t.get("contents", [])]
        if len(set(insts)) != len(insts):
            errs.append(f"type {tn}: duplicate content instance names")
    for p in raw["partitions"]:
        if p["type"] not in raw["partition_types"]:
            errs.append(f"partition {p['name']}: unknown type '{p['type']}'")
        if p["name"] == DIE_PART:
            errs.append(f"partition name '{DIE_PART}' is reserved")
    if errs:
        return errs
    # ports: endpoints, buses, widths, directions
    for pr in raw["ports"]:
        pid = pr["id"]
        for side, want in (("src", "out"), ("dst", "in")):
            e = pr[side]
            if e["part"] == DIE_PART:
                continue
            if e["part"] not in P.parts:
                errs.append(f"port {pid}: {side} partition '{e['part']}' unknown")
                continue
            b = P.buses(e["part"]).get(e["bus"])
            if b is None:
                errs.append(f"port {pid}: {side} bus '{e['bus']}' not on type '{P.parts[e['part']]['type']}'")
                continue
            if b["dir"] != want:
                errs.append(f"port {pid}: {side} bus '{e['bus']}' is dir {b['dir']}, needs {want}")
            if b["width"] != pr["width"]:
                errs.append(f"port {pid}: width {pr['width']} != {side} bus '{e['bus']}' width {b['width']}")
        if pr["src"]["part"] == DIE_PART and pr["dst"]["part"] == DIE_PART:
            errs.append(f"port {pid}: both ends on {DIE_PART}")
        if pr["src"]["part"] == pr["dst"]["part"]:
            errs.append(f"port {pid}: src and dst are the same partition")
        if pr["window_um"][0] >= pr["window_um"][1]:
            errs.append(f"port {pid}: window lo >= hi")
        for ln in pr["layers"]:
            if ln not in P.layers:
                errs.append(f"port {pid}: layer {ln} not in die.layers")
                continue
            want_dir = "H" if pr["face"] in "EW" else "V"
            if P.layers[ln]["dir"] != want_dir:
                errs.append(f"port {pid}: layer {ln} is {P.layers[ln]['dir']}, a {pr['face']} face needs {want_dir}")
    # every bus endpoint used exactly once (no open / unbound / multiply-driven bus)
    use = {}
    for pr in raw["ports"]:
        for side in ("src", "dst"):
            e = pr[side]
            if e["part"] != DIE_PART:
                use.setdefault((e["part"], e["bus"]), []).append(pr["id"])
    for part in P.parts:
        for bn in P.buses(part):
            u = use.get((part, bn), [])
            if not u:
                errs.append(f"partition {part}: bus '{bn}' is unbound (no port; tie-offs are not allowed)")
            elif len(u) > 1:
                errs.append(f"partition {part}: bus '{bn}' bound by {len(u)} ports {u}")
    # lanes: continuity through ft slots, each port in exactly one lane
    inlane = {}
    for ln in raw["lanes"]:
        lid = ln["id"]
        for x in ln["ports"]:
            if x not in P.ports:
                errs.append(f"lane {lid}: unknown port '{x}'")
            inlane.setdefault(x, []).append(lid)
        if any(x not in P.ports for x in ln["ports"]):
            continue
        for a, b in zip(ln["ports"], ln["ports"][1:]):
            pa, pb = P.ports[a], P.ports[b]
            if pa["dst"]["part"] != pb["src"]["part"]:
                errs.append(f"lane {lid}: port {a} ends in {pa['dst']['part']} but {b} starts in {pb['src']['part']}")
                continue
            ib, ob = pa["dst"]["bus"], pb["src"]["bus"]
            if not (ib.endswith("_i") and ob.endswith("_o") and ib[:-2] == ob[:-2]
                    and P.slot(pa["dst"]["part"], ib[:-2])):
                errs.append(f"lane {lid}: {a}->{b} inside {pa['dst']['part']} must pass one ft slot "
                            f"(<slot>_i -> <slot>_o), got {ib} -> {ob}")
        first, last = P.ports[ln["ports"][0]], P.ports[ln["ports"][-1]]
        if first["src"]["bus"].endswith("_o") and first["src"]["part"] != DIE_PART and \
                P.buses(first["src"]["part"])[first["src"]["bus"]].get("slot"):
            errs.append(f"lane {lid}: starts at an ft slot output (lane must start at a functional bus)")
        if last["dst"]["part"] != DIE_PART and P.buses(last["dst"]["part"])[last["dst"]["bus"]].get("slot"):
            errs.append(f"lane {lid}: ends at an ft slot input (lane must end at a functional bus)")
    for pid in P.ports:
        n = len(inlane.get(pid, []))
        if n != 1:
            errs.append(f"port {pid}: in {n} lanes (each port belongs to exactly one lane)")
    # reset / clock references
    for k in ("clock", "reset"):
        src = raw.get(k, {}).get("source")
        if src and src["part"] != DIE_PART and src["part"] not in P.parts:
            errs.append(f"{k}.source: unknown partition {src['part']}")
    # latency table keys
    lat = raw.get("latency", {}).get("lanes", {})
    for lid in lat:
        if lid not in P.lanes:
            errs.append(f"latency: entry for unknown lane '{lid}'")
    return errs


def main(argv):
    if len(argv) >= 2 and argv[1] == "validate":
        bad = 0
        for f in argv[2:]:
            errs = validate(load(f))
            for e in errs:
                print(f"{f}: ERROR {e}")
            print(f"{f}: {'FAIL' if errs else 'PASS'} ({len(errs)} errors)")
            bad |= bool(errs)
        return 1 if bad else 0
    if len(argv) >= 2 and argv[1] == "dump-schema":
        out = argv[2] if len(argv) > 2 else str(Path(__file__).with_name("die_plan.schema.json"))
        Path(out).write_text(json.dumps(SCHEMA, indent=1) + "\n")
        print(out)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
