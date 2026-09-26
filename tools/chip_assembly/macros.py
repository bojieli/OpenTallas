"""Placeholder macro views: LEF, Liberty and a blackbox Verilog stub.

The memory compilers (tools/mem_compiler/, another workstream) will emit the
real SRAM and via-programmed ROM macros.  Until they land, every memory the
tile needs that the ASAP7 platform does not ship as a ``fakeram7_*`` macro,
and every PHY or link, is a placeholder generated here.  A placeholder is the
same kind of object the platform's own fakeram is (FakeRAM 2.0 style):

* LEF: CLASS BLOCK, a size, signal pins on the edges the floorplan names
  (M4 on the west and east edges, M5 on the north and south edges, on the
  routing tracks), power stripes on M4 like the fakeram macros so the
  platform's macro PDN grid (M4-M5) connects them, and OBS on the layers the
  macro occupies;
* Liberty: one clock, clock-to-output arcs on every output and setup/hold
  checks on every input, with constant tables (the fakeram convention);
* Verilog: a ``(* blackbox *)`` module with the exact port list.

Area and timing come from stated models, never from a layout:

* SRAM: the bit density of ``fakeram7_256x256`` (33.25 um x 84 um for 64 Kib:
  0.04262 um^2/bit) times a port factor, clock-to-q 0.218 ns and setup
  0.050 ns, both read from that macro's liberty;
* ROM: 9.630 MB/mm^2, the ASAP7 via-programmed ROM density the project
  measured (docs/RESEARCH_PROVENANCE.md, ``measured_asap7_7nm_via_programmed``);
* PHY / link: the area the architecture assigns (docs/ARCHITECTURE_ATLAS.html
  die budget), with a registered interface on the core side.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# FakeRAM 2.0 ``fakeram7_256x256`` (platforms/asap7/lef, lib/NLDM).
FAKERAM_BIT_AREA_UM2 = 33.25 * 84.0 / (256 * 256)
FAKERAM_CLK_TO_Q_NS = 0.218
FAKERAM_SETUP_NS = 0.050
FAKERAM_HOLD_NS = 0.050
# docs/RESEARCH_PROVENANCE.md: measured_asap7_7nm_via_programmed, 9.630 MB/mm^2.
ROM_BYTES_PER_MM2 = 9.630e6

# ASAP7 routing tracks (platforms/asap7/openRoad/make_tracks.tcl).
M4_Y_OFFSET, M4_PITCH = 0.012, 0.048
M5_X_OFFSET, M5_PITCH = 0.012, 0.048
PIN_WIDTH = 0.024
PIN_DEPTH = 0.192
# The placement grid macros snap to (the M2 pitch and the row height).
SITE_W, SITE_H = 0.054, 0.270

EDGES = ("W", "E", "N", "S")


@dataclass
class Pin:
    name: str
    direction: str  # input | output
    width: int = 1  # 1: scalar
    edge: Any = "W"  # an edge, or [(first bit, last bit, edge), ...]
    timed: bool = True  # False: no arc (static configuration straps)
    delay_ns: float | None = None  # clock-to-output (output) or setup (input); None: macro default
    span: tuple[float, float] | None = None  # (from, to) um along the edge; None: the whole edge

    def bits(self) -> list[str]:
        if self.width == 1:
            return [self.name]
        return [f"{self.name}[{i}]" for i in range(self.width)]

    def edge_of_bit(self, bit: int) -> str:
        return self.place_of_bit(bit)[0]

    def place_of_bit(self, bit: int) -> tuple[str, tuple[float, float] | None]:
        """(edge, span) of one bit; edge entries are (lo, hi, edge[, span])."""
        if isinstance(self.edge, str):
            return self.edge, self.span
        for lo, hi, edge, *rest in self.edge:
            if lo <= bit <= hi:
                return edge, (tuple(rest[0]) if rest else self.span)
        raise ValueError(f"{self.name}[{bit}] has no edge")


@dataclass
class MacroSpec:
    name: str
    width_um: float
    height_um: float
    pins: list[Pin]
    clock: str = "clk"
    clk_to_q_ns: float = FAKERAM_CLK_TO_Q_NS
    setup_ns: float = FAKERAM_SETUP_NS
    hold_ns: float = FAKERAM_HOLD_NS
    input_cap_pf: float = 0.002
    obs_layers: tuple[str, ...] = ("M1", "M2", "M3", "M4")
    kind: str = "sram"
    basis: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def area_um2(self) -> float:
        return self.width_um * self.height_um

    def pin_count(self) -> int:
        return sum(p.width for p in self.pins) + 1


def snap(value: float, grid: float) -> float:
    return round(math.ceil(value / grid - 1e-9) * grid, 4)


def square_for_area(area_um2: float, aspect: float = 1.0) -> tuple[float, float]:
    """(width, height) on the placement grid for an area and width/height aspect."""
    h = math.sqrt(area_um2 / aspect)
    w = area_um2 / h
    return snap(w, SITE_W), snap(h, SITE_H)


def sram_area_um2(bits: int, port_factor: float = 1.0) -> float:
    return bits * FAKERAM_BIT_AREA_UM2 * port_factor


def rom_area_um2(bits: int) -> float:
    return bits / 8.0 / ROM_BYTES_PER_MM2 * 1e6


# --------------------------------------------------------------------------
# LEF
# --------------------------------------------------------------------------


def _edge_positions(n: int, length: float, offset: float, pitch: float,
                    margin: float) -> list[float]:
    """n on-track centre coordinates spread evenly over [margin, length - margin]."""
    tracks = int((length - 2 * margin) / pitch)
    if n > tracks:
        raise ValueError(f"{n} pins do not fit {tracks} tracks on an edge of {length} um")
    first = math.ceil((margin - offset) / pitch)
    if n == 1:
        return [round(offset + (first + tracks // 2) * pitch, 4)]
    step = tracks / n
    return [round(offset + (first + int(i * step)) * pitch, 4) for i in range(n)]


def pin_rects(spec: MacroSpec) -> dict[str, tuple[str, tuple[float, float, float, float]]]:
    """bit name -> (layer, rect), the clock first on the west edge.

    Pins are grouped by (edge, span); a group is spread evenly over its span
    (the whole edge when the pin names none), in declaration order.
    """
    groups: dict[tuple[str, Any], list[str]] = {("W", None): [spec.clock]}
    for pin in spec.pins:
        for i, bit in enumerate(pin.bits()):
            edge, span = pin.place_of_bit(i)
            if edge not in EDGES:
                raise ValueError(f"{spec.name}.{pin.name}: edge {edge!r} not in {EDGES}")
            groups.setdefault((edge, span), []).append(bit)
    rects: dict[str, tuple[str, tuple[float, float, float, float]]] = {}
    w, h = spec.width_um, spec.height_um
    margin = 0.5
    hw = PIN_WIDTH / 2
    # whole-edge groups share their edge with any spans; keep them off the spans
    for (edge, span), names in groups.items():
        length = h if edge in ("W", "E") else w
        lo, hi = span if span else (0.0, length)
        lo, hi = max(lo, 0.0), min(hi, length)
        offset, pitch = (M4_Y_OFFSET, M4_PITCH) if edge in ("W", "E") else (M5_X_OFFSET, M5_PITCH)
        coords = [c + lo for c in _edge_positions(len(names), hi - lo, offset - lo % pitch, pitch, margin)]
        for name, c in zip(names, coords):
            if edge in ("W", "E"):
                x0 = 0.0 if edge == "W" else w - PIN_DEPTH
                rects[name] = ("M4", (x0, c - hw, x0 + PIN_DEPTH, c + hw))
            else:
                y0 = 0.0 if edge == "S" else h - PIN_DEPTH
                rects[name] = ("M5", (c - hw, y0, c + hw, y0 + PIN_DEPTH))
    return rects


def lef_text(spec: MacroSpec) -> str:
    w, h = spec.width_um, spec.height_um
    out = [
        "# Placeholder macro written by tools/chip_assembly/macros.py",
        f"# kind: {spec.kind}; {spec.basis}",
        "VERSION 5.7 ;",
        'BUSBITCHARS "[]" ;',
        f"MACRO {spec.name}",
        f"  FOREIGN {spec.name} 0 0 ;",
        "  SYMMETRY X Y R90 ;",
        f"  SIZE {w:.3f} BY {h:.3f} ;",
        "  CLASS BLOCK ;",
    ]
    directions = {spec.clock: "INPUT"}
    for pin in spec.pins:
        for bit in pin.bits():
            directions[bit] = pin.direction.upper()
    for name, (layer, (x0, y0, x1, y1)) in pin_rects(spec).items():
        out += [
            f"  PIN {name}",
            f"    DIRECTION {directions[name]} ;",
            "    USE SIGNAL ;",
            "    SHAPE ABUTMENT ;",
            "    PORT",
            f"      LAYER {layer} ;",
            f"      RECT {x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f} ;",
            "    END",
            f"  END {name}",
        ]
    # Power: M4 stripes across the macro, clear of the edge pins, alternating
    # VSS / VDD every 2.4 um (the platform macro grid drops M4-M5 vias on them).
    x0, x1 = PIN_DEPTH + 0.3, w - PIN_DEPTH - 0.3
    pitch, width = 2.4, 0.096
    for net, use, phase in (("VSS", "GROUND", 0.0), ("VDD", "POWER", pitch / 2)):
        out += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT"]
        out.append("      LAYER M4 ;")
        y = 1.2 + phase
        while y + width < h - 1.0:
            out.append(f"      RECT {x0:.3f} {y:.3f} {x1:.3f} {y + width:.3f} ;")
            y += pitch
        out += ["    END", f"  END {net}"]
    out.append("  OBS")
    for layer in spec.obs_layers:
        out += [f"    LAYER {layer} ;", f"    RECT 0 0 {w:.3f} {h:.3f} ;"]
    out += ["  END", f"END {spec.name}", "", "END LIBRARY", ""]
    return "\n".join(out)


# --------------------------------------------------------------------------
# Liberty
# --------------------------------------------------------------------------


def _table(name: str, template: str, value: float) -> list[str]:
    return [
        f"            {name}({template}) {{",
        '                index_1 ("0.005, 0.500");',
        '                index_2 ("0.001, 0.500");',
        f'                values ("{value:.4f}, {value:.4f}", "{value:.4f}, {value:.4f}");',
        "            }",
    ]


def liberty_text(spec: MacroSpec) -> str:
    n = spec.name
    out = [
        f"library({n}) {{",
        "    technology (cmos);",
        "    delay_model : table_lookup;",
        '    time_unit : "1ns";',
        '    voltage_unit : "1V";',
        '    current_unit : "1uA";',
        '    leakage_power_unit : "1uW";',
        '    pulling_resistance_unit : "1kohm";',
        "    capacitive_load_unit (1,pf);",
        "    nom_process : 1;",
        "    nom_temperature : 25.000;",
        "    nom_voltage : 0.7;",
        "    operating_conditions(tt_0p7_25) { process : 1; temperature : 25.000; voltage : 0.7; tree_type : balanced_tree; }",
        "    default_operating_conditions : tt_0p7_25;",
        "    default_max_transition : 0.320;",
        "    default_fanout_load : 1;",
        "    default_input_pin_cap : 0.0;",
        "    default_output_pin_cap : 0.0;",
        "    default_inout_pin_cap : 0.0;",
        "    default_cell_leakage_power : 0;",
        "    default_leakage_power_density : 0.0;",
        "    slew_lower_threshold_pct_rise : 20.000;",
        "    slew_upper_threshold_pct_rise : 80.000;",
        "    slew_lower_threshold_pct_fall : 20.000;",
        "    slew_upper_threshold_pct_fall : 80.000;",
        "    input_threshold_pct_rise : 50.000;",
        "    input_threshold_pct_fall : 50.000;",
        "    output_threshold_pct_rise : 50.000;",
        "    output_threshold_pct_fall : 50.000;",
        f"    lu_table_template({n}_delay) {{ variable_1 : input_net_transition; variable_2 : total_output_net_capacitance; index_1 (\"1000, 1001\"); index_2 (\"1000, 1001\"); }}",
        f"    lu_table_template({n}_slew) {{ variable_1 : input_net_transition; variable_2 : total_output_net_capacitance; index_1 (\"1000, 1001\"); index_2 (\"1000, 1001\"); }}",
        f"    lu_table_template({n}_check) {{ variable_1 : related_pin_transition; variable_2 : constrained_pin_transition; index_1 (\"1000, 1001\"); index_2 (\"1000, 1001\"); }}",
    ]
    widths = sorted({p.width for p in spec.pins if p.width > 1})
    for wd in widths:
        out += [
            f"    type ({n}_bus{wd}) {{ base_type : array; data_type : bit; bit_width : {wd}; bit_from : {wd - 1}; bit_to : 0; downto : true; }}",
        ]
    out += [
        f"    cell({n}) {{",
        f"        area : {spec.area_um2:.3f};",
        "        interface_timing : true;",
        "        dont_use : true;",
        "        dont_touch : true;",
        f"        pin({spec.clock}) {{ direction : input; capacitance : 0.020; clock : true; }}",
    ]
    for pin in spec.pins:
        head = (f"        bus({pin.name}) {{ bus_type : {n}_bus{pin.width};"
                if pin.width > 1 else f"        pin({pin.name}) {{")
        body = [head, f"            direction : {pin.direction};"]
        if pin.direction == "input":
            body.append(f"            capacitance : {spec.input_cap_pf:.4f};")
            if pin.timed:
                setup = spec.setup_ns if pin.delay_ns is None else pin.delay_ns
                for kind, value in (("setup_rising", setup), ("hold_rising", spec.hold_ns)):
                    body += [
                        "            timing() {",
                        f"                related_pin : \"{spec.clock}\";",
                        f"                timing_type : {kind};",
                        *(_table(t, f"{n}_check", value) for t in ("rise_constraint", "fall_constraint")),
                        "            }",
                    ]
        else:
            body.append("            max_capacitance : 0.500;")
            if pin.timed:
                body += [
                    "            timing() {",
                    f"                related_pin : \"{spec.clock}\";",
                    "                timing_type : rising_edge;",
                    "                timing_sense : non_unate;",
                    *(_table(t, f"{n}_delay", spec.clk_to_q_ns if pin.delay_ns is None else pin.delay_ns)
                      for t in ("cell_rise", "cell_fall")),
                    *(_table(t, f"{n}_slew", 0.020) for t in ("rise_transition", "fall_transition")),
                    "            }",
                ]
        # flatten nested lists from the generator expressions above
        flat: list[str] = []
        for item in body:
            if isinstance(item, list):
                flat.extend(item)
            else:
                flat.append(item)
        out += flat
        out.append("        }")
    out += ["    }", "}", ""]
    return "\n".join(out)


# --------------------------------------------------------------------------
# Verilog stub
# --------------------------------------------------------------------------


def verilog_stub(spec: MacroSpec) -> str:
    ports = [f"    input  wire {spec.clock}"]
    for pin in spec.pins:
        rng = f"[{pin.width - 1}:0] " if pin.width > 1 else ""
        kw = "input  wire" if pin.direction == "input" else "output wire"
        ports.append(f"    {kw} {rng}{pin.name}")
    return (
        f"// Placeholder macro ({spec.kind}) written by tools/chip_assembly/macros.py\n"
        f"(* blackbox *)\nmodule {spec.name} (\n" + ",\n".join(ports) + "\n);\nendmodule\n"
    )


def write_views(spec: MacroSpec, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "lef": out_dir / f"{spec.name}.lef",
        "lib": out_dir / f"{spec.name}.lib",
        "v": out_dir / f"{spec.name}.v",
    }
    paths["lef"].write_text(lef_text(spec), encoding="utf-8")
    paths["lib"].write_text(liberty_text(spec), encoding="utf-8")
    paths["v"].write_text(verilog_stub(spec), encoding="utf-8")
    return paths


def describe(spec: MacroSpec) -> dict:
    return {
        "name": spec.name,
        "kind": spec.kind,
        "width_um": spec.width_um,
        "height_um": spec.height_um,
        "area_um2": round(spec.area_um2, 3),
        "signal_pins": spec.pin_count(),
        "clk_to_q_ns": spec.clk_to_q_ns,
        "setup_ns": spec.setup_ns,
        "basis": spec.basis,
        **spec.extra,
    }


def pins(*items: Iterable) -> list[Pin]:
    """Pin list from (name, direction, width, edge[, timed]) tuples."""
    out = []
    for item in items:
        name, direction, width, edge, *rest = item
        out.append(Pin(name, direction, width, edge, rest[0] if rest else True))
    return out
