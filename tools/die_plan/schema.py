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
  Latency (register stages the lane adds between source leaf and destination leaf) = source out boundary flop +
  sum(stations of crossed slots) + destination in boundary flop + fixed_cycles (lane_latency()).
- Part name "@die" in a port endpoint is the die boundary (bumps / die IO); its bus is the die-level port name.
"""
import bisect
from fractions import Fraction
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
    dict(name="M4", dir="H", pitch_um=0.048, offset_um=0.024),
    dict(name="M5", dir="V", pitch_um=0.048, offset_um=0.024),
    dict(name="M6", dir="H", pitch_um=0.064, offset_um=0.032),
    dict(name="M7", dir="V", pitch_um=0.064, offset_um=0.032),
    dict(name="M8", dir="H", pitch_um=0.080, offset_um=0.040),
    dict(name="M9", dir="V", pitch_um=0.080, offset_um=0.040),
]
# M4-M9 (the pin layers) use SYMMETRIC tracks, offset = pitch / 2 (platform make_tracks: 0.012 / 0.016 / 0.116).  With
# partition origins and outlines on the die lattice (GRID_UM, a multiple of every pitch), a track at offset + k*p in the
# type frame lands on a die track for R0, MX, MY and R180 instances alike (h - (p/2 + k p) = p/2 + (h/p - k - 1) p),
# so mirrored / shifted copies of one partition type share one pin table and one hardened view.  The generated
# partition and die kits write these tracks (gen_phys.make_tracks_tcl); M1-M3 keep the platform cell-access tracks.
# 8.64 um = lcm(row 0.27, site 0.054, M2..M9 pitches, PG 4.32/8.64): the DIE LATTICE.  Partition origins and outlines
# on it keep rows, sites, tracks and PG identical in the die and every partition frame, for every orient.
# ORFS base unit (COORD 10-23, mock-array): 2.16 um = 45 x 0.048 = 40 x 0.054 = 8 x 0.27.  grid_um must be a multiple of
# it AND of every pin-layer pitch: 2.16 alone is NOT a multiple of the M6/M7 pitch 0.064 (33.75 tracks), so pins on
# M6/M7 need the 8.64 lattice (4 base units).  Channel widths are multiples of grid_um (8.64 = 4 units, 17.28 = 8).
BASE_LATTICE_UM = 2.16
GRID_UM = 8.64

DEFAULT_BUDGETS = dict(face_pins_per_um=6.0, face_pin_layers=2, face_window_um=10.0, pin_track_max=0.6,
                       cut_ratio_max=0.6, cut_step_um=250.0, pin_reg_p90_um=30.0,
                       # COORD 10-23 R3: ft stations at most 750 um apart on every die; R4 (CP1 r8 RULING 21:26):
                       # partition clock tap GRID at <= 400 um pitch covering all sinks (CP1 r6: 16 taps @400 =
                       # face-flop spread 68/57 ps TT, seam skew <= 52)
                       ft_station_max_um=750.0, tap_pitch_um=400.0,
                       # PLAN-TOOL5 (COORD 10-23 die review): G0C reach = hop <= reach_margin x the per-layer measured
                       # reach (reach.py); die IO bump fields within io_edge_max_um of a die edge (die_io.py)
                       reach_margin=0.9, io_edge_max_um=200.0)
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
_win = {"type": "array", "items": _num, "minItems": 2, "maxItems": 2}
_lays = {"type": "array", "items": _layer, "minItems": 1, "maxItems": 3}   # 3 only on a face_layers face (G0 faces)
_order = {"enum": ["lsb_low", "lsb_high"]}
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
                "grid_um": _pos,                     # the die lattice: partition origins + outlines (8.64)
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
                                                                            "maximum": 1}},
                    # layers a lane hop routes on (reach.py): default die_layers when die_use has ft_reserved
                    "ft_route_layers": {"type": "array", "items": _layer, "minItems": 1}}},
                # die IO (COORD 10-23, S81-P5): pad / bump windows of every off-die signal (SerDes PMA pads, HBM PHY
                # memory side, host).  Each window sits over its host partition (the PHY / IO partition), offers
                # `sites` signal bumps/pads, and lists the @die ports it carries (bits <= sites).
                "io": {"type": "array", "items": {
                    # PLAN-TOOL5 (die_io.py): a PHY-macro window may instead declare its interface class + off-die
                    # signal count (`iface`, `signals`; the modelled PHY has no RTL pad ports), and `host` when it
                    # also carries the die's host link (true), or, on a die without a host link, its host traffic
                    # in-band ("in_band", with the on-die `host_route`; S81-XDIE 10-24)
                    "type": "object", "required": ["name", "kind", "rect_um", "sites", "part"],
                    "additionalProperties": False,
                    "properties": {"name": _name, "kind": {"enum": ["bump", "pad", "phy_macro"]}, "rect_um": _rect,
                                   "sites": {"type": "integer", "minimum": 1}, "pitch_um": _pos, "layer": _layer,
                                   "part": _name, "ports": {"type": "array", "items": _name, "minItems": 1},
                                   "iface": {"enum": ["serdes", "ucie", "hbm_phy", "host", "refclk", "other"]},
                                   "signals": {"type": "integer", "minimum": 1}, "host": {"enum": [True, False, "in_band"]},
                                   "host_route": {"type": "string"},
                                   "basis": {"type": "string"}, "note": {"type": "string"},
                                   # rack table macro name (lk_<name>) of this window when its partition is not
                                   # named after it (xdie_io.py; HBM B2l, HBM-ARCH 10-24)
                                   "rack_macro": {"type": "string"}}}},
                "channels": {"type": "array", "items": {   # die-level gaps between partitions, each with its reason
                    # either a plain reserved gap (rect_um), or a PLANNED CHANNEL between two partitions (between +
                    # width_um + layers + ports): those ports are routed at die level across the gap, boundary flops
                    # on both sides; their pins keep the same along-face windows; rect_um is derived
                    "type": "object", "required": ["reason"], "additionalProperties": False,
                    "properties": {"rect_um": _rect, "reason": {"type": "string", "minLength": 3},
                                   "name": _name,
                                   "between": {"type": "array", "items": _name, "minItems": 2, "maxItems": 2},
                                   "width_um": _pos,
                                   "layers": {"type": "array", "items": _layer, "minItems": 1},
                                   "ports": {"type": "array", "items": _name}}}},
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
                    # estimated std cells of one instance (synth / census); COORD 10-23 CORE-KS: a type over
                    # CORE_CELLS_MAX (400k) must list hard_cores[] (G0 ERROR).  Else the sum of contents[].cells.
                    "cells": {"type": "integer", "minimum": 0},
                    "hard": {"type": "boolean"},     # hard IP (PHY, closed macro used as-is): no generated wrapper
                    "kit": {"type": "string"},
                    "note": {"type": "string"},
                    "buses": {"type": "array", "items": {
                        "type": "object", "required": ["name", "dir", "width"], "additionalProperties": False,
                        "properties": {"name": _name, "dir": {"enum": ["in", "out"]},
                                       "width": {"type": "integer", "minimum": 1}, "kind": {"enum": list(KINDS)},
                                       "leaf": {"type": "string"},      # "<inst>.<port>" the bus binds to inside
                                       # pin geometry in the TYPE frame (then ports need no window: every instance
                                       # of the type, in any orient, derives its die window from it)
                                       "face": {"enum": list(FACES)}, "window_um": _win, "layers": _lays,
                                       "order": _order,
                                       "note": {"type": "string"}}}},
                    "ft_slots": {"type": "array", "items": {
                        "type": "object", "required": ["name", "in_face", "out_face", "width"],
                        "additionalProperties": False,
                        "properties": {"name": _name, "in_face": {"enum": list(FACES)},
                                       "out_face": {"enum": list(FACES)},
                                       "width": {"type": "integer", "minimum": 1},
                                       "stations": {"type": "integer", "minimum": 1},
                                       "regs_um": {"type": "array", "items": _xy},   # station sites, type frame
                                       "bit_sites_um": {"type": "array", "items": {"type": "array", "items": _xy}},
                                       "bit_site_cell_um": _xy,  # allocated cell footprint; explicit sites are lower-left
                                       "layer": _layer,                             # in-partition ft layer (<= M7)
                                       "in_window_um": _win, "out_window_um": _win,  # type frame pin windows
                                       "layers": _lays, "order": _order}}},
                    "clock": {"type": "object", "additionalProperties": False, "properties": {
                        "tap_um": _xy, "layer": _layer, "insertion_ps": _pos, "insertion_tol_ps": _nonneg,
                        # R4 revised (COORD 10-23): tap grid pitch for this type, sized from the measured tree
                        # (OT_TAP_CHECK WARN suggests it); default budgets.tap_pitch_um
                        "tap_pitch_um": _pos,
                        # default "grid" (R4, CP1 r8 RULING 21:26).  "grid+sinks" (alias "sinks", KV-P6) = the
                        # grid PLUS sink-anchored taps (taps.py k-medians of face registers + ft stations) ADDED
                        # for face-register clusters; sink taps never replace the grid (CP1 r8: interior logic
                        # 4.5-5.7k sinks piled on one tap, spread 133 ps)
                        "tap_mode": {"enum": ["grid", "grid+sinks", "sinks"]}, "tap_radius_um": _pos,
                        "tap_max_sinks": {"type": "integer", "minimum": 1},
                        # CP2: "early" turns the kind 'core' taps[] into kit clock ports clk_c<k> (core_taps()): the
                        # core's clock pins hang on their own tap, which the spine delivers (insertion_ps - common
                        # latency) early, so the core's internal flops see the common latency.  Absent: taps[] are
                        # plan records only (unchanged kits).
                        "core_taps": {"enum": ["early"]},
                        # matched M8/M9 branch leaves below the partition root tap_um: one per planned core or
                        # landed glue region (COORD 10-23 07:24; QC-FIX)
                        "taps": {"type": "array", "items": {
                            "type": "object", "required": ["name", "xy"], "additionalProperties": False,
                            "properties": {"name": _name, "xy": _xy, "kind": {"enum": ["core", "glue", "leaf"]},
                                           "orient": {"enum": list(ORIENTS)}, "insertion_ps": _pos,
                                           "insertion_tol_ps": _nonneg, "budget_owner": {"type": "string"},
                                           "from_root_um": _nonneg, "note": {"type": "string"}}}}}},
                    # hard cores built on PLATFORM tracks (macros inside): a per-core placement offset puts their
                    # boundary pins on the plan tracks (COORD 10-23 08:36; A0: y +0.012)
                    "hard_cores": {"type": "array", "items": {
                        "type": "object", "required": ["inst", "origin_um", "outline_um"],
                        "additionalProperties": False,
                        "properties": {"inst": _name, "module": _name, "origin_um": _xy, "outline_um": _xy,
                                       "orient": {"enum": list(ORIENTS)},
                                       "track_offset_um": _xy,      # added to origin_um (lattice) at placement
                                       "pins": {"type": "array", "items": {   # core frame (R0, origin 0)
                                           "type": "object", "required": ["name", "layer", "xy"],
                                           "additionalProperties": False,
                                           "properties": {"name": _name, "layer": _layer, "xy": _xy}}},
                                       "pins_file": {"type": "string"},   # JSON [{name|bus+bit, layer, x, y}]
                                       # hardened views (repo-relative): the partition kit places the core as a
                                       # macro at origin_um + track_offset_um (COORD 10-23: kits place content macros)
                                       "lef": {"type": "string"}, "lib": {"type": "string"},
                                       "note": {"type": "string"}}}},
                    "reset": {"type": "object", "additionalProperties": False, "properties": {
                        "tap_um": _xy, "sync_stages": {"type": "integer", "minimum": 2}}},
                    "contents": {"type": "array", "items": {
                        "type": "object", "required": ["inst", "module", "status"], "additionalProperties": False,
                        "properties": {"inst": _name, "module": _name, "status": {"enum": list(STATUS)},
                                       "kit": {"type": "string"}, "geom_pass": {"type": "string"},
                                       "origin_um": _xy, "outline_um": _wh, "note": {"type": "string"},
                                       # a macro leaf (SRAM / ROM / hard block): repo-relative views; the kit places it
                                       # at origin_um (type frame) with orient (mandatory when lef is given)
                                       "lef": {"type": "string"}, "lib": {"type": "string"},
                                       "orient": {"enum": list(ORIENTS)},
                                       "obs_max": _layer,   # leaf blockage top layer (G2 probe; default M5)
                                       "cells": {"type": "integer", "minimum": 0},   # est. std cells of this leaf
                                       # leaf port -> "clk" | "rst_n" (partition synchronised reset, active low)
                                       #   | "rst" (active high) | "net:<type net>" | "bus:<bus>" | "epoch:<bus>"
                                       "bind": {"type": "object", "additionalProperties": {"type": "string"}},
                                       "params": {"type": "object",
                                                  "additionalProperties": {"type": ["integer", "string"]}}}}},
                    "sources": {"type": "array", "items": {"type": "string"}},   # leaf RTL files (repo paths)
                    "nets": {"type": "array", "items": {                         # internal leaf-to-leaf nets
                        "type": "object", "required": ["name", "width"], "additionalProperties": False,
                        "properties": {"name": _name, "width": {"type": "integer", "minimum": 1}}}},
                    # R3-INTERNAL (COORD 10-23 18:15): FIRM stations of an internal reg-reg connection > 750 um
                    # (face window -> internal block, block -> block); type frame; every hop <= ft_station_max_um
                    "internal_stations": {"type": "array", "items": {
                        "type": "object", "required": ["from_um", "to_um", "regs_um"], "additionalProperties": False,
                        "properties": {"conn": {"type": "string"},    # "bus:<bus>" | "<leaf inst>.<port>" | "<a>|<b>"
                                       "from_um": _xy, "to_um": _xy, "regs_um": {"type": "array", "items": _xy},
                                       "bits": {"type": "integer", "minimum": 1}, "launch": {"type": "string"},
                                       "capture": {"type": "string"}, "note": {"type": "string"}}}},
                    "channels": {"type": "array", "items": {
                        "type": "object", "required": ["rect_um", "reason"], "additionalProperties": False,
                        "properties": {"rect_um": _rect, "reason": {"type": "string", "minLength": 3}}}},
                    "ft_track_frac": {"type": "number", "minimum": 0, "maximum": 1},
                    # PLAN-TOOL5 (e): share of the M8 / M9 tracks over this type reserved for over-the-top die ft
                    # (default die.layer_budget.cut_avail)
                    "ft_budget": {"type": "object", "additionalProperties": {"type": "number", "minimum": 0,
                                                                             "maximum": 1}},
                    # per-face pin layer sets (type frame faces); a layer above partition_signal_max (e.g. M8 on an
                    # S81 svc fold / rail face) is allowed only when listed here for that face (COORD 10-23)
                    "face_layers": {"type": "object", "additionalProperties": False, "properties": {
                        f: {"type": "array", "items": _layer, "minItems": 1} for f in FACES}},
                    # spare slots: reserved face windows WITHOUT ports, so partitions of one slot class keep one
                    # face layout (no tie-offs: a spare is not a port; COORD 10-23)
                    "spare_slots": {"type": "array", "items": {
                        "type": "object", "required": ["name", "face", "window_um", "layers"],
                        "additionalProperties": False,
                        "properties": {"name": _name, "face": {"enum": list(FACES)}, "window_um": _win,
                                       "layers": {"type": "array", "items": _layer, "minItems": 1},
                                       "reason": {"type": "string"}}}},
                }}},
        "partitions": {"type": "array", "minItems": 1, "items": {
            "type": "object", "required": ["name", "type", "origin_um"], "additionalProperties": False,
            "properties": {"name": _name, "type": _name, "origin_um": _xy, "orient": {"enum": list(ORIENTS)},
                           "note": {"type": "string"}}}},
        "ports": {"type": "array", "items": {
            "type": "object", "required": ["id", "src", "dst", "width"],   # face/layers/window: or from the type
            "additionalProperties": False,
            "properties": {"id": _name, "src": _end, "dst": _end, "width": {"type": "integer", "minimum": 1},
                           "kind": {"enum": list(KINDS)}, "face": {"enum": list(FACES)},
                           "layers": {"type": "array", "items": _layer, "minItems": 1, "maxItems": 3},
                           "window_um": {"type": "array", "items": _num, "minItems": 2, "maxItems": 2},
                           "order": {"enum": ["lsb_low", "lsb_high"]}, "epoch": {"type": "boolean"},
                           "note": {"type": "string"}}}},
        "lanes": {"type": "array", "items": {
            "type": "object", "required": ["id", "ports"], "additionalProperties": False,
            "properties": {"id": _name, "ports": {"type": "array", "items": _name, "minItems": 1},
                           "fixed_cycles": {"type": "integer", "minimum": 0},
                           "reach_um": _pos, "param": {"type": "string", "pattern": "^[A-Z][A-Z0-9_]*$"},
                           "route_layers": {"type": "array", "items": _layer, "minItems": 1},
                           "note": {"type": "string"}}}},
        # R8 (COORD 10-23): lanes that must arrive in the SAME cycle: the bits of one as-built bus (valid + data +
        # forwarded bits, groups from BINDER2) split over several lanes.  lane_latency() pads every member to the
        # slowest; replicated consumers of one source (same source bus, same destination type + bus) are grouped
        # automatically (Plan.latency_groups()).
        "latency_groups": {"type": "array", "items": {
            "type": "object", "required": ["name", "lanes"], "additionalProperties": False,
            "properties": {"name": _name, "kind": {"enum": ["bus", "replica", "landed"]},
                           "window": {"type": "integer", "minimum": 2},
                           "lanes": {"type": "array", "items": _name, "minItems": 2},
                           "source": {"type": "string"}, "note": {"type": "string"}}}},
        "clock": {"type": "object", "additionalProperties": False, "properties": {
            "source": _end, "insertion_ps": _pos, "insertion_tol_ps": _nonneg, "neighbour_skew_ps": _pos,
            # R4 owner rule (COORD 10-23 19:55): ONE die-wide common latency target; every partition balances its
            # face-flop insertion to it (seam skew <= 80 ps TT+FF); the IO SDC proxy uses it as vclk latency.
            # Absolute insertion / sinks per tap are guidance (OT_TAP_CHECK WARN).  G0 completeness requires it.
            "common_latency_ps": _pos,
            "face_xing": {"enum": ["budgeted", "forwarded_landing"]},
            "spine": {"type": "object", "additionalProperties": False, "properties": {
                "layers": {"type": "array", "items": _layer}, "root_um": _xy,
                "topology": {"enum": ["htree", "fishbone", "mesh"]},
                # CP2 branch model (spine.py, pair plans): the FULL die's root / outline and each partition's origin
                # in that die; branch latency = H-tree path length x branch_ps_per_mm (default 60), recursion down to
                # regions <= branch_leaf_um (default budgets.tap_pitch_um)
                "die_root_um": _xy, "die_outline_um": _xy,
                "part_die_origin_um": {"type": "object", "additionalProperties": _xy},
                "branch_ps_per_mm": _pos, "branch_leaf_um": _pos}}}},
        "reset": {"type": "object", "additionalProperties": False, "properties": {
            "source": _end, "sync_stages": {"type": "integer", "minimum": 2},
            "data_reset": {"const": False}, "epoch_bit": {"const": True}, "release": {"enum": ["counted"]}}},
        "latency": {"type": "object", "additionalProperties": False, "properties": {
            "lanes": {"type": "object", "additionalProperties": {
                "type": "object", "required": ["cycles"], "additionalProperties": False,
                "properties": {"cycles": {"type": "integer", "minimum": 1}, "stations": {"type": "integer"},
                               "faces": {"type": "integer"}, "fixed": {"type": "integer"},
                               "boundary": {"type": "integer"},
                               "natural": {"type": "integer"}, "pad": {"type": "integer", "minimum": 0},
                               "param": {"type": "string"}}}}}},
        # mandatory G0 census coverage (census_cov.py): [{rows, map, note}] or {"none": reason}
        "census": {"type": ["array", "object"]},
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
    if t and not any(ok[x](v) for x in (t if isinstance(t, list) else [t])):
        errs.append(f"{path}: expected {t}, got {type(v).__name__}")
        return
    if isinstance(t, list):
        t = next(x for x in t if ok[x](v))
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
        self.ports = {p["id"]: self._resolve_port(p) for p in raw["ports"]}
        self.lanes = {l["id"]: l for l in raw["lanes"]}
        self.clock = dict(DEFAULT_CLOCK, **raw.get("clock", {}))
        if "common_latency_ps" in self.clock:       # R4 owner rule: the ONE die-wide target is the insertion every
            self.clock["insertion_ps"] = float(self.clock["common_latency_ps"])   # kit balances to + vclk latency
        self.reset = dict(DEFAULT_RESET, **raw.get("reset", {}))
        self.budgets = dict(DEFAULT_BUDGETS, **raw.get("budgets", {}))

    # -- port geometry from the type's bus declaration
    def _type_geom(self, part, bus):
        """(type face, window, layers, order) declared on the partition's type for `bus`, or None."""
        if part == DIE_PART or part not in self.parts or self.parts[part]["type"] not in self.types:
            return None
        t = self.types[self.parts[part]["type"]]
        for b in t.get("buses", []):
            if b["name"] == bus and "window_um" in b and "face" in b and "layers" in b:
                return b["face"], b["window_um"], b["layers"], b.get("order", "lsb_low")
        for s_ in t.get("ft_slots", []):
            for sfx, fk, wk in (("_i", "in_face", "in_window_um"), ("_o", "out_face", "out_window_um")):
                if bus == s_["name"] + sfx and wk in s_ and "layers" in s_:
                    return s_[fk], s_[wk], s_["layers"], s_.get("order", "lsb_low")
        return None

    def geom_to_die(self, part, g):
        """type-frame (face, window, layers, order) -> die-frame (face, window, layers, order) for one instance."""
        tf, (a, b), lays, order = g
        p = self.parts[part]
        w, h = self.types[p["type"]]["outline_um"]
        o = p.get("orient", "R0")
        df = self.die_face(part, tf)
        if tf in "EW":
            base, ext, flip = p["origin_um"][1], h, o in ("MX", "R180")
        else:
            base, ext, flip = p["origin_um"][0], w, o in ("MY", "R180")
        if flip:
            a, b = ext - b, ext - a
            order = "lsb_high" if order == "lsb_low" else "lsb_low"
        return df, [round(base + a, 6), round(base + b, 6)], list(lays), order

    def port_geom_from(self, pr, side):
        g = self._type_geom(pr[side]["part"], pr[side]["bus"])
        if g is None:
            return None
        df, win, lays, order = self.geom_to_die(pr[side]["part"], g)
        if side == "dst" and pr["src"]["part"] != DIE_PART:
            df = OPP[df]
        return df, win, lays, order

    def _resolve_port(self, pr):
        if all(k in pr for k in ("face", "layers", "window_um")):
            return pr
        for side in ("src", "dst"):
            try:
                g = self.port_geom_from(pr, side)
            except (KeyError, TypeError):
                g = None
            if g:
                q = dict(pr)
                q.setdefault("face", g[0])
                q.setdefault("window_um", g[1])
                q.setdefault("layers", g[2])
                q.setdefault("order", g[3])
                q["_geom_from"] = side
                return q
        return pr

    # -- partitions
    def ptype(self, part):
        return self.types[self.parts[part]["type"]]

    def orient(self, part):
        return self.parts[part].get("orient", "R0")

    def channel_of(self, pid):
        """the planned die.channels entry carrying port pid (or None = abutted)."""
        if not hasattr(self, "_chan_of"):
            self._chan_of = {}
            for c in self.die.get("channels", []):
                for q in c.get("ports", []):
                    self._chan_of[q] = c
        return self._chan_of.get(pid)

    def channel_rect(self, c):
        """rect of a channel: rect_um, or the gap between its two partitions' facing faces."""
        if "rect_um" in c:
            return tuple(c["rect_um"])
        a, b = (self.rect(n) for n in c["between"])
        if a[2] <= b[0] + 1e-6 or b[2] <= a[0] + 1e-6:          # side by side: vertical channel
            l, r = (a, b) if a[2] <= b[0] + 1e-6 else (b, a)
            return (l[2], max(l[1], r[1]), r[0], min(l[3], r[3]))
        lo, hi = (a, b) if a[3] <= b[1] + 1e-6 else (b, a)
        return (max(lo[0], hi[0]), lo[3], min(lo[2], hi[2]), hi[1])

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

    def type_top_layer(self, tn):
        """highest pin / route layer of a type: partition_signal_max, raised by its face_layers (M8 faces)."""
        top = self.layer_budget["partition_signal_max"]
        for ls in self.types[tn].get("face_layers", {}).values():
            for ln in ls:
                if int(ln[1:]) > int(top[1:]):
                    top = ln
        return top

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
        """[(bit, layer, die coordinate along the face)].  A port whose geometry comes from a TYPE declaration gets its
        pins computed in that type's frame and transformed to the die: the pin table is a property of the type, so
        every instance (any orient, any lattice origin) carries the identical hardened pins."""
        pr = self.ports[pid]
        side = pr.get("_geom_from")
        if not side:
            return pin_positions(pr, self.layers)
        part = pr[side]["part"]
        tf, win, lays, order = self._type_geom(part, pr[side]["bus"])
        tp = dict(pr, face=tf, window_um=win, layers=lays, order=order)
        p = self.parts[part]
        w, h = self.types[p["type"]]["outline_um"]
        o = p.get("orient", "R0")
        if tf in "EW":
            base, ext, flip = p["origin_um"][1], h, o in ("MX", "R180")
        else:
            base, ext, flip = p["origin_um"][0], w, o in ("MY", "R180")
        return sorted((b, ln, round(base + (ext - c if flip else c), 6)) for b, ln, c in pin_positions(tp, self.layers))

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

    def latency_groups(self):
        """R8: [(name, kind, [lanes])]: the plan's latency_groups (bus groups from BINDER2) + automatic replica groups
        (lanes from one source bus into the same destination type + bus on different partitions)."""
        out = [(g["name"], g.get("kind", "bus"), list(g["lanes"])) for g in self.raw.get("latency_groups", [])]
        rep = {}
        for lid, ln in self.lanes.items():
            a, b = self.ports[ln["ports"][0]], self.ports[ln["ports"][-1]]
            if b["dst"]["part"] == DIE_PART:
                continue
            key = (a["src"]["part"], a["src"]["bus"], self.parts[b["dst"]["part"]]["type"], b["dst"]["bus"])
            rep.setdefault(key, []).append(lid)
        for (sp, sb, dt, db), lids in sorted(rep.items()):
            if len(lids) > 1:
                out.append((f"replica:{sp}.{sb}->{dt}.{db}", "replica", sorted(lids)))
        return out

    def landed_skew(self):
        """LANDED BUNDLES (COORD rule 10-23, r8.py doc): a latency group of kind `landed` = the lanes of one bundle
        that lands in ONE forwarded-clock landing ring with one K strap (window = ring depth D cycles, default 4).  The
        bundle arrives at ONE group depth (lane_pads pads every lane to the slowest, as a bus group); its natural
        per-lane spread must stay under the landing window margin D - 1, else the bundle cannot land coherently and the
        stations must be re-planned.  Returns [message] for every landed group over the margin."""
        bad = []
        for g in self.raw.get("latency_groups", []):
            if g.get("kind") != "landed" or not all(l in self.lanes for l in g["lanes"]):
                continue
            nat = {l: self.lane_natural(l)["cycles"] for l in g["lanes"]}
            d = g.get("window", 4)
            if max(nat.values()) - min(nat.values()) > d - 1:
                bad.append(f"landed group {g['name']}: natural lane spread {max(nat.values()) - min(nat.values())} "
                           f"cycles {nat} > landing window margin {d - 1} (re-plan the stations so the bundle lands "
                           "in one window)")
        return bad

    def lane_pads(self):
        """R8: {lane: pad cycles} so every latency group arrives in one cycle (fixpoint over overlapping groups)."""
        if getattr(self, "_pads", None) is not None:
            return self._pads
        nat = {lid: self.lane_natural(lid)["cycles"] for lid in self.lanes}
        cyc = dict(nat)
        groups = [g for g in self.latency_groups() if all(l in self.lanes for l in g[2])]
        for _ in range(len(self.lanes) + 1):
            moved = False
            for _, _, lids in groups:
                m = max(cyc[l] for l in lids)
                for l in lids:
                    if cyc[l] < m:
                        cyc[l], moved = m, True
            if not moved:
                break
        self._pads = {lid: cyc[lid] - nat[lid] for lid in self.lanes}
        return self._pads

    def lane_pad_sites(self, lid):
        """candidate sites of a lane's pad stages, preferred first: the destination in bus, then the source out bus."""
        ln = self.lanes[lid]
        a, b = self.ports[ln["ports"][0]], self.ports[ln["ports"][-1]]
        out = []
        if b["dst"]["part"] != DIE_PART:
            out.append((self.parts[b["dst"]["part"]]["type"], b["dst"]["bus"]))
        if a["src"]["part"] != DIE_PART:
            out.append((self.parts[a["src"]["part"]]["type"], a["src"]["bus"]))
        return out

    def bus_pads(self):
        """R8: ({(type, bus): pad}, [conflicts]).  Pad stages are a TYPE property (hardened once): every lane through
        a (type, bus) site must want the same pad there.  Each padded lane takes its destination in bus, else its
        source out bus; a lane that fits neither is a conflict (split the type, or move the delay with fixed_cycles /
        ft stations)."""
        pads = self.lane_pads()
        want = {}                                  # site -> {lane: pad} for every lane touching the site
        for lid in self.lanes:
            for site in self.lane_pad_sites(lid):
                want.setdefault(site, {})[lid] = None
        chosen, bad, got = {}, [], {lid: 0 for lid in self.lanes}
        for lid in sorted(self.lanes, key=lambda l: (-pads[l], l)):
            need = pads[lid] - got[lid]
            if not need:
                continue
            for site in self.lane_pad_sites(lid):
                if site in chosen:
                    continue
                # a site pads EVERY lane through it: each must still need exactly this much
                if all(pads[o] - got[o] == need for o in want[site]):
                    chosen[site] = need
                    for o in want[site]:
                        got[o] += need
                    break
            else:
                bad.append(f"lane {lid}: pad {need} fits no site {self.lane_pad_sites(lid)} (other lanes of the same "
                           "type bus need a different pad: split the type or move the delay with fixed_cycles)")
        return chosen, bad

    def lane_latency(self, lid):
        """lane_natural() + the R8 group pad: dict(cycles, natural, pad, stations, boundary, faces, fixed)."""
        d = self.lane_natural(lid)
        pad = self.lane_pads()[lid]
        d["natural"], d["pad"] = d["cycles"], pad
        d["cycles"] += pad
        return d

    def lane_natural(self, lid):
        """dict(cycles, stations, boundary, faces, fixed).  cycles = the register stages a lane adds between the source
        leaf and the destination leaf: the source partition's out boundary flop + the stations of every crossed ft
        slot + the destination's in boundary flop (a die-IO end has no partition flop) + fixed_cycles."""
        ln = self.lanes[lid]
        st = 0
        for part, slot, _, _ in self.lane_crossings(lid):
            s = self.slot(part, slot) if slot else None
            st += int(s.get("stations", 1)) if s else 1
        fixed = int(ln.get("fixed_cycles", 0))
        a, b = self.ports[ln["ports"][0]], self.ports[ln["ports"][-1]]
        bnd = (a["src"]["part"] != DIE_PART) + (b["dst"]["part"] != DIE_PART)
        return dict(cycles=bnd + st + fixed, stations=st, boundary=bnd, faces=len(ln["ports"]), fixed=fixed)


def tap_pitch(P, tn):
    """R4 revised: the type's tap GRID pitch (clock.tap_pitch_um, sized from the measured trees) else
    budgets.tap_pitch_um (400).  Also with added sink-anchored taps: the grid stays (CP1 r8 RULING)."""
    return float(P.types[tn].get("clock", {}).get("tap_pitch_um", P.budgets.get("tap_pitch_um", 400.0)))


def sink_tap_mode(t):
    """True when the type adds sink-anchored taps to its grid (clock.tap_mode "grid+sinks", or the KV-P6 alias
    "sinks", which since the CP1 r8 RULING no longer replaces the grid)."""
    return t.get("clock", {}).get("tap_mode") in ("grid+sinks", "sinks")


def tap_grid(P, tn):
    """COORD 10-23 R4: the partition's clock taps, [(port, x, y)] in the type frame (unsnapped).  A grid of
    ceil(w/pitch) x ceil(h/pitch) taps at the cell centres (pitch = budgets.tap_pitch_um, 400), so every sink is
    within ~200 um of a tap.  A type that fits one cell keeps its clock.tap_um.  Tap 0 is the port 'clk', the others
    'clk_t<i>' (row-major from the type's SW corner); the kit connects each flop to its nearest tap (clock_taps.tcl).
    CP1 r8 RULING (COORD 10-23 21:26): the grid is THE method on every die; clock.tap_mode "grid+sinks" (or "sinks")
    only ADDS sink-anchored taps (taps.py) for face-register clusters after the grid taps, numbered on from the grid;
    a sink tap within taps.SEP_UM of a grid tap is dropped (same spine drop)."""
    t = P.types[tn]
    out = _grid_taps(P, tn)
    if sink_tap_mode(t):
        import taps
        for _, x, y, _, _ in taps.sink_taps(P, tn):
            if any(abs(x - a) + abs(y - b) < taps.SEP_UM for _, a, b in out):
                continue
            x, y = tap_clear(t, x, y, [(a, b) for _, a, b in out])
            out.append((f"clk_t{len(out)}", x, y))
    return out


def core_taps(P, tn):
    """CP2: the type's EARLY core taps [(port, x, y, tap)] (type frame, unsnapped): clock.taps[] kind 'core' when
    clock.core_taps == 'early', ports clk_c<k> in taps[] order.  A tap names its core (`<inst>`, every clock pin) or one
    clock pin (`<inst>.<pin>`); tap['insertion_ps'] = the core's internal clock latency.  Otherwise []."""
    ck = P.types[tn].get("clock", {}) or {}
    if ck.get("core_taps") != "early":
        return []
    out = []
    for tp in ck.get("taps", []) or []:
        if tp.get("kind") == "core":
            out.append((f"clk_c{len(out)}", float(tp["xy"][0]), float(tp["xy"][1]), tp))
    return out


def core_tap_early_ps(P, tp):
    """how early the spine delivers a core tap: max(0, insertion_ps - the die common latency)."""
    return max(0.0, float(tp.get("insertion_ps", 0.0)) - float(P.clock["insertion_ps"]))


def _grid_taps(P, tn):
    """the R4 pitch grid of tap_grid (no added sink taps)."""
    t = P.types[tn]
    w, h = t["outline_um"]
    pitch = tap_pitch(P, tn)
    nx, ny = max(1, math.ceil(w / pitch - 1e-9)), max(1, math.ceil(h / pitch - 1e-9))
    if nx == 1 and ny == 1:
        x, y = t.get("clock", {}).get("tap_um", [w / 2, h / 2])
        return [("clk", float(x), float(y))]
    out = []
    for j in range(ny):
        for i in range(nx):
            k = len(out)
            x, y = tap_clear(t, (i + 0.5) * w / nx, (j + 0.5) * h / ny, [(a, b) for _, a, b in out])
            out.append(("clk" if k == 0 else f"clk_t{k}", x, y))
    return out


TAP_CLEAR_UM = 8.64       # tap pin (and its root buffer) >= one lattice step off every hard core / macro of the type
TAP_STEP_UM = 2.16


def tap_clear(t, x, y, taken=(), clear=TAP_CLEAR_UM):
    """S81-P8 10-23 (GEOM-REVIEW5 15:14 condition (b)): an R4 grid tap at a cell centre landed ON a ROM / hard-core
    macro in 4-10 of 10 interior pins of the S81 frame kits (h9_r1: all), so its root buffer sat on a macro.  Move the
    tap to the nearest point (rings of 2.16 um) that is >= `clear` from every hard_cores box of the type (a channel),
    inside the outline by `clear`, and >= `clear` from the taps already placed.  Types without hard cores, or whose
    tap is already in a channel, are unchanged."""
    w, h = t["outline_um"]
    boxes = []
    for c in t.get("hard_cores", []) or []:
        (ox, oy), (cw, ch) = c["origin_um"], c["outline_um"]
        boxes.append((ox - clear, oy - clear, ox + cw + clear, oy + ch + clear))

    def free(px, py):
        if not (clear <= px <= w - clear and clear <= py <= h - clear):
            return False
        if any(abs(px - a) < clear and abs(py - b) < clear for a, b in taken):
            return False
        return not any(x0 < px < x1 and y0 < py < y1 for x0, y0, x1, y1 in boxes)
    if not boxes or free(x, y):
        return x, y
    for r in range(1, int(max(w, h) / TAP_STEP_UM) + 1):
        d = r * TAP_STEP_UM
        ring = [(x + i * TAP_STEP_UM, y + s * d) for i in range(-r, r + 1) for s in (-1, 1)] + \
               [(x + s * d, y + i * TAP_STEP_UM) for i in range(-r + 1, r) for s in (-1, 1)]
        ok = [p for p in ring if free(*p)]
        if ok:
            px, py = min(ok, key=lambda p: ((p[0] - x) ** 2 + (p[1] - y) ** 2, p))
            return round(px, 4), round(py, 4)
    return x, y


def has_epoch(port):
    """a lane bundle carries one in-band reset epoch bit (bit index `width`, the MSB of the generated port) unless it is
    a clock/reset port, a die-IO port, or `epoch` is set false."""
    if "epoch" in port:
        return bool(port["epoch"])
    return port.get("kind", "data") in ("data", "ctl") and DIE_PART not in (port["src"]["part"], port["dst"]["part"])


def port_pins_count(port):
    return int(port["width"]) + (1 if has_epoch(port) else 0)


# Partition PG stripe bands per pin layer (gen_phys.PDN): (pitch, band centre offset, half exclusion width) in um.
# Each band is a VDD+VSS stripe pair. Its centre (2.16 + 4.32k, or 4.32 + 8.64k) is mirror-symmetric in every lattice
# frame (outlines are multiples of 8.64), so the same periodic pattern holds in the die frame and in every type frame,
# for every orient. Half exclusion = half the pair span + half the pin width + 2 track pitches. One pitch was too
# tight: DRT-0073 (no access point) on an M5 pin 0.048 um from an M5 stripe in the CP1 mock run.
# Pins on M5, M6 or M7 never sit on a stripe: the CP1 mock run on OpenROAD master found PSM-0043 shorts there
# (check_power_grid), from M7 frame_int pins on the N face.
PART_PG_BANDS = {"M5": (4.32, 2.16, 0.264), "M6": (4.32, 2.16, 0.48), "M7": (8.64, 4.32, 0.48),
                 # M8 (face_layers only): the DIE PG grid's M8 stripes (default die.pg: 0.48 wide, pitch 8.64,
                 # offset 4.32, VDD/VSS -> a stripe every 4.32 at 0 mod 4.32) run over every partition
                 "M8": (4.32, 0.0, 0.66),
                 # M9 (face_layers only, N/S faces: the vertical die layer): die M9 stripes, same default grid as M8
                 "M9": (4.32, 0.0, 0.66)}
# M8 band: die.pg default M8 stripes w0.48 pitch 8.64 offset 4.32, VDD + VSS (spacing pitch/2) -> one stripe every
# 4.32.  The band covers the stripe whether pdngen's offset names its edge ([4.32, 4.80]) or its centre ([4.08, 4.56])
# plus 2 M8 pitches; a plan with a different die.pg M8 grid must keep its stripes inside these bands.


def pg_blocked(ln, c):
    b = PART_PG_BANDS.get(ln)
    if not b:
        return False
    pitch, cen, half = b
    d = (c - cen) % pitch
    return min(d, pitch - d) < half - 1e-9


def spread(A, n, lo, hi):
    """n of the usable tracks A (sorted, track units), UNIFORM in coordinate over the window [lo, hi]: pin j goes to
    the usable track nearest its cell centre lo + (j + 0.5) (hi - lo) / n, so any sub-window holds the window's average
    density to within one pin (the G0 face check's measure).  Ties go toward the window centre and each half is picked
    from its own end, so the pick commutes with the frame mirror (the usable set is mirror-symmetric).  When nearest-
    track picks collide (window close to full), fall back to an even pick in index space.  Returns indices into A."""
    m = len(A)
    if n == 0:
        return []
    # exact arithmetic (KV-P2 10-23): window ends snapped to 1e-6 track and kept as Fractions, so the nearest-track ties
    # resolve identically in mirrored replicas (die-frame float error broke them: G0 'pin table differs')
    lo, hi = Fraction(str(round(lo, 6))), Fraction(str(round(hi, 6)))
    cen = (lo + hi) / 2
    L = hi - lo

    def nearest(t):
        i = bisect.bisect_left(A, t)
        best = None
        for k in (i - 1, i):
            if 0 <= k < m:
                # exact ties (fp-noise-free) -> nearer the window centre -> nearer the middle usable track (index
                # (m-1)/2): all three commute with the frame mirror, so the pick is mirror-equivariant whenever m is
                # odd (an odd pin count on an even usable-track count with the centre between two tracks has no
                # mirror-symmetric pick: generators size such windows to an odd track count)
                key = (round(abs(A[k] - t), 6), round(abs(A[k] - cen), 6), abs(2 * k - (m - 1)))
                if best is None or key < best[0]:
                    best = (key, k)
        return best[1]
    # lower half from the left end, upper half mirrored from the right end; a pick that collides with the previous
    # one (targets inside a PG band) moves to the next free usable track
    half = n // 2
    low, prev = [], -1
    for j in range(half):
        k = max(nearest(lo + (j + 0.5) * L / n), prev + 1)
        low.append(k)
        prev = k
    high, prev = [], m
    for j in range(half):
        k = min(nearest(hi - (j + 0.5) * L / n), prev - 1)
        high.append(k)
        prev = k
    mid = [nearest(cen)] if n % 2 else []
    idx = low + mid + list(reversed(high))
    if all(a < b for a, b in zip(idx, idx[1:])) and idx[0] >= 0 and idx[-1] < m:
        return idx
    if n == 1:
        return [(m - 1) // 2]
    lowh = [((j * (m - 1)) // (n - 1)) for j in range(n // 2)]
    return lowh + ([(m - 1) // 2] if n % 2 else []) + [m - 1 - i for i in reversed(lowh)]


def usable_tracks(L, ln, lo, hi):
    """number of tracks of layer ln (dict L: pitch_um, offset_um) inside [lo, hi] off the partition PG bands."""
    p, off = L["pitch_um"], L["offset_um"]
    k0 = math.ceil((lo - off) / p - 1e-9)
    k1 = math.floor((hi - off) / p + 1e-9)
    return sum(1 for k in range(k0, k1 + 1) if not pg_blocked(ln, off + k * p))


def window_for(lo, pins, names, layers=None, per_um=6.0, track_max=0.6):
    """helper for plan generators: the smallest hi (on a 0.016-um step) so that `pins` pins over the layer list `names`
    fit [lo, hi] at <= per_um pins/um and <= track_max of the usable (PG-band-free) tracks on every layer."""
    layers = layers or {L["name"]: L for L in ASAP7_LAYERS}
    nl = len(names)
    need = [len(range(i, pins, nl)) for i in range(nl)]
    hi = lo + max(pins / per_um, 0.016)
    while True:
        if all(usable_tracks(layers[ln], ln, lo, hi) * track_max >= n for ln, n in zip(names, need)):
            return round(hi, 4)
        hi += 0.016


def pin_positions(port, layers):
    """Deterministic pin assignment of one port, die frame: [(bit, layer, coord_um)] with coord along the face.

    Bits alternate over the port's layers (bit i -> layers[i % n]); on each layer the bits are spread evenly over
    [lo, hi] at an integer multiple of that layer's track pitch, snapped to offset + k * pitch.  Both partitions of a
    face use this same function, so their pins coincide by construction.  Raises ValueError if the window cannot hold
    the bits on whole tracks."""
    lo, hi = sorted(port["window_um"])
    names = port["layers"]
    w = port_pins_count(port)
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
        # usable tracks: in the window and off the partition PG stripe bands (PART_PG_BANDS)
        A = [k for k in range(k0, k1 + 1) if not pg_blocked(ln, off + k * p)]
        m = len(A)
        if m < n:
            raise ValueError(f"port {port['id']}: {n} bits on {ln} need {n} tracks, window has {m} off the PG "
                             f"stripes ({max(k1 - k0 + 1, 0)} in all)")
        idx = spread(A, n, (lo - off) / p, (hi - off) / p)
        for j, b in enumerate(bits):
            slot = (n - 1 - j) if rev else j
            out.append((b, ln, round(off + A[idx[slot]] * p, 6)))
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
            from ft_bit_sites import validate_slot
            try:
                validate_slot(s)
            except ValueError as exc:
                errs.append(f"type {tn} slot {s['name']}: {exc}")
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
    pids = {pr["id"] for pr in raw["ports"]}
    owned = {}
    for i, c in enumerate(raw["die"].get("channels", [])):
        nm = c.get("name", f"channels[{i}]")
        planned = any(k in c for k in ("between", "width_um", "layers", "ports"))
        if not planned and "rect_um" not in c:
            errs.append(f"die channel {nm}: needs rect_um (reserved gap) or between/width_um/layers/ports (planned)")
        if planned:
            miss = [k for k in ("between", "width_um", "layers", "ports") if k not in c]
            if miss:
                errs.append(f"die channel {nm}: planned channel lacks {miss}")
                continue
            for n in c["between"]:
                if n not in P.parts:
                    errs.append(f"die channel {nm}: unknown partition '{n}'")
            for q in c["ports"]:
                if q not in pids:
                    errs.append(f"die channel {nm}: unknown port '{q}'")
                elif q in owned:
                    errs.append(f"die channel {nm}: port '{q}' already in channel {owned[q]}")
                owned[q] = nm
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
        rp = P.ports[pid]
        if not all(k in rp for k in ("face", "layers", "window_um")):
            errs.append(f"port {pid}: no pin geometry (give face/layers/window_um on the port, or face/window_um/"
                        "layers on the src or dst type's bus / slot)")
            continue
        # a geometry declared on both sides (port and/or both types) must agree in the die frame
        decl = []
        if all(k in pr for k in ("face", "layers", "window_um")):
            decl.append(("port", (pr["face"], [float(v) for v in pr["window_um"]], list(pr["layers"]),
                                  pr.get("order", "lsb_low"))))
        for side in ("src", "dst"):
            try:
                g = P.port_geom_from(pr, side)
            except (KeyError, TypeError):
                g = None
            if g:
                decl.append((f"{side} type", (g[0], [float(v) for v in g[1]], list(g[2]), g[3])))
        for (na, ga), (nb, gb) in zip(decl, decl[1:]):
            if ga[0] != gb[0] or ga[2] != gb[2] or ga[3] != gb[3] or \
                    any(abs(x - y) > 1e-6 for x, y in zip(ga[1], gb[1])):
                errs.append(f"port {pid}: {na} geometry {ga} != {nb} geometry {gb} in the die frame")
        pr = rp
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
    for g in raw.get("latency_groups", []):
        for lid in g["lanes"]:
            if lid not in P.lanes:
                errs.append(f"latency_groups {g['name']}: unknown lane '{lid}'")
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
