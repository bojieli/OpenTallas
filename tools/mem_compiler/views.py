"""LEF, Liberty and Verilog writers shared by the SRAM and ROM compilers.

The views follow the conventions ORFS's own ASAP7 macros use (FakeRAM2.0's
``fakeram7_*``): signal pins on M4 at the left and right edges, VDD/VSS as
full-width horizontal M4 straps that the platform's macro PDN grid reaches with
M4-M5 vias, and M1-M4 obstructions over the body.  Liberty is NLDM in the
ASAP7 standard cells' own units (ps, fF, fJ, nW), one file per corner.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

from asap7 import METAL, snap_up

SLEW_INDEX_PS = [5.0, 20.0, 80.0, 160.0, 320.0]
LOAD_INDEX_FF = [0.72, 2.88, 11.52, 23.04, 46.08]


@dataclass
class Pin:
    name: str           # base name
    width: int          # 1 for a scalar
    direction: str      # input / output
    kind: str           # clock / data_in / data_out / control
    related: str = "clk"

    def bits(self) -> list[str]:
        if self.width == 1:
            return [self.name]
        return [f"{self.name}[{i}]" for i in range(self.width)]


@dataclass
class Timing:
    """Per-corner macro timing and power, all in ps / fF / fJ / nW."""
    corner: str
    voltage: float
    temperature: float
    clk_to_q_ps: float          # at the smallest slew and load index
    out_r_kohm: float           # output driver resistance: delay slope per fF
    out_slew_intrinsic_ps: float
    setup_ps: float
    hold_ps: float
    min_period_ps: float
    min_pulse_ps: float
    read_energy_fj: float
    write_energy_fj: float
    leakage_nw: float
    pin_cap_ff: float
    clk_cap_ff: float
    breakdown: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# LEF
# ---------------------------------------------------------------------------

def macro_outline(core_w: float, core_h: float, pins: list[Pin]) -> tuple[float, float, dict[str, Any]]:
    """Snap the macro to the placement grid and grow it until the pins fit.

    Signal pins sit on both vertical edges at METAL['pin_pitch_um'], leaving one
    strap pitch free at the top and bottom.  A macro too short for its pins is
    stretched and the stretch is reported, never hidden.
    """
    n_pins = sum(p.width for p in pins)
    per_edge = math.ceil(n_pins / 2)
    margin = METAL["strap_pitch_um"]
    pin_h = per_edge * METAL["pin_pitch_um"] + 2 * margin
    w = snap_up(core_w, METAL["width_snap_um"])
    h = snap_up(max(core_h, pin_h), METAL["height_snap_um"])
    info = {
        "signal_pins": n_pins,
        "pins_per_edge": per_edge,
        "pin_limited": pin_h > core_h,
        "pin_stretch_um": round(max(0.0, pin_h - core_h), 3),
        "snap_overhead_um2": round(w * h - core_w * max(core_h, pin_h), 3),
    }
    return w, h, info


def write_lef(name: str, w: float, h: float, pins: list[Pin], props: dict[str, int]) -> str:
    L = []
    L.append("# OpenTallas memory compiler (tools/mem_compiler), ASAP7 abstract view")
    L.append("VERSION 5.7 ;")
    L.append('BUSBITCHARS "[]" ;')
    L.append("DIVIDERCHAR \"/\" ;")
    L.append("PROPERTYDEFINITIONS")
    for key in props:
        L.append(f"  MACRO {key} INTEGER ;")
    L.append("END PROPERTYDEFINITIONS")
    L.append(f"MACRO {name}")
    for key, value in props.items():
        L.append(f"  PROPERTY {key} {value} ;")
    L.append(f"  FOREIGN {name} 0 0 ;")
    L.append("  SYMMETRY X Y R90 ;")
    L.append(f"  SIZE {w:.3f} BY {h:.3f} ;")
    L.append("  CLASS BLOCK ;")
    bits = [(p, b) for p in pins for b in p.bits()]
    per_edge = math.ceil(len(bits) / 2)
    pitch = METAL["pin_pitch_um"]
    pw = METAL["pin_width_um"]
    y0 = METAL["strap_pitch_um"]
    for i, (p, b) in enumerate(bits):
        left = i < per_edge
        k = i if left else i - per_edge
        y = y0 + k * pitch
        x1, x2 = (0.0, pw) if left else (w - pw, w)
        L.append(f"  PIN {b}")
        L.append(f"    DIRECTION {p.direction.upper()} ;")
        L.append("    USE CLOCK ;" if p.kind == "clock" else "    USE SIGNAL ;")
        L.append("    SHAPE ABUTMENT ;")
        L.append("    PORT")
        L.append(f"      LAYER {METAL['pin_layer']} ;")
        L.append(f"      RECT {x1:.3f} {y:.3f} {x2:.3f} {y + pw:.3f} ;")
        L.append("    END")
        L.append(f"  END {b}")
    # power straps: alternate VDD / VSS across the whole height
    sw = METAL["strap_width_um"]
    sp = METAL["strap_pitch_um"]
    xs1, xs2 = 0.3, w - 0.3
    straps = {"VDD": [], "VSS": []}
    y = sp / 2
    k = 0
    while y + sw < h:
        straps["VDD" if k % 2 == 0 else "VSS"].append(y)
        y += sp / 2
        k += 1
    for net, use in (("VDD", "POWER"), ("VSS", "GROUND")):
        L.append(f"  PIN {net}")
        L.append("    DIRECTION INOUT ;")
        L.append(f"    USE {use} ;")
        L.append("    PORT")
        L.append(f"      LAYER {METAL['pin_layer']} ;")
        for yy in straps[net]:
            L.append(f"      RECT {xs1:.3f} {yy:.3f} {xs2:.3f} {yy + sw:.3f} ;")
        L.append("    END")
        L.append(f"  END {net}")
    L.append("  OBS")
    for layer in METAL["obs_layers"][:-1]:
        L.append(f"    LAYER {layer} ;")
        L.append(f"    RECT 0 0 {w:.3f} {h:.3f} ;")
    L.append(f"    LAYER {METAL['obs_layers'][-1]} ;")
    L.append(f"    RECT 0.072 0 {w - 0.072:.3f} {h:.3f} ;")
    L.append("  END")
    L.append(f"END {name}")
    L.append("")
    L.append("END LIBRARY")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
# Liberty
# ---------------------------------------------------------------------------

def _fmt_row(vals: list[float]) -> str:
    return '"' + ", ".join(f"{v:.4f}" for v in vals) + '"'


def _table(values: Callable[[float, float], float], i1: list[float], i2: list[float]) -> list[str]:
    rows = [_fmt_row([values(a, b) for b in i2]) for a in i1]
    return [f'  index_1 ("{", ".join(f"{v:g}" for v in i1)}");',
            f'  index_2 ("{", ".join(f"{v:g}" for v in i2)}");',
            "  values ( \\", *[f"    {r}, \\" for r in rows[:-1]], f"    {rows[-1]} \\", "  );"]


def write_liberty(name: str, t: Timing, pins: list[Pin], area: float, memory: dict[str, int] | None,
                  comment: str) -> str:
    L: list[str] = []
    lib = f"{name}_{t.corner}"
    L += [f"library ({lib}) {{",
          f'  comment : "{comment}";',
          "  technology (cmos);", "  delay_model : table_lookup;", '  revision : "1.0";',
          '  time_unit : "1ps";', '  voltage_unit : "1V";', '  current_unit : "1mA";',
          '  leakage_power_unit : "1nW";', '  pulling_resistance_unit : "1kohm";',
          "  capacitive_load_unit (1, ff);",
          f"  nom_process : 1;", f"  nom_voltage : {t.voltage:g};", f"  nom_temperature : {t.temperature:g};",
          f"  operating_conditions (PVT_{t.corner}) {{",
          f"    process : 1; voltage : {t.voltage:g}; temperature : {t.temperature:g};", "  }",
          f"  default_operating_conditions : PVT_{t.corner};",
          f"  voltage_map (VDD, {t.voltage:g});", "  voltage_map (VSS, 0);",
          "  default_max_transition : 320;", "  default_fanout_load : 1;",
          "  default_cell_leakage_power : 0;", "  default_inout_pin_cap : 0;",
          "  default_input_pin_cap : 0;", "  default_output_pin_cap : 0;",
          "  slew_lower_threshold_pct_rise : 10;", "  slew_upper_threshold_pct_rise : 90;",
          "  slew_lower_threshold_pct_fall : 10;", "  slew_upper_threshold_pct_fall : 90;",
          "  input_threshold_pct_rise : 50;", "  input_threshold_pct_fall : 50;",
          "  output_threshold_pct_rise : 50;", "  output_threshold_pct_fall : 50;",
          "  slew_derate_from_library : 1;",
          "  lu_table_template (mc_delay) {", "    variable_1 : input_net_transition;",
          "    variable_2 : total_output_net_capacitance;",
          f'    index_1 ("{", ".join(f"{v:g}" for v in SLEW_INDEX_PS)}");',
          f'    index_2 ("{", ".join(f"{v:g}" for v in LOAD_INDEX_FF)}");', "  }",
          "  lu_table_template (mc_constraint) {", "    variable_1 : constrained_pin_transition;",
          "    variable_2 : related_pin_transition;",
          f'    index_1 ("{", ".join(f"{v:g}" for v in SLEW_INDEX_PS)}");',
          f'    index_2 ("{", ".join(f"{v:g}" for v in SLEW_INDEX_PS)}");', "  }",
          "  power_lut_template (mc_energy) {", "    variable_1 : input_transition_time;",
          f'    index_1 ("{", ".join(f"{v:g}" for v in SLEW_INDEX_PS)}");', "  }"]
    for p in pins:
        if p.width > 1:
            L += [f"  type ({name}_{p.name}_t) {{", "    base_type : array;", "    data_type : bit;",
                  f"    bit_width : {p.width};", f"    bit_from : {p.width - 1};", "    bit_to : 0;",
                  "    downto : true;", "  }"]
    L += [f"  cell ({name}) {{", f"    area : {area:.4f};", "    dont_use : true;", "    dont_touch : true;",
          "    interface_timing : true;", f"    cell_leakage_power : {t.leakage_nw:.4f};",
          '    pg_pin (VDD) { voltage_name : VDD; pg_type : primary_power; }',
          '    pg_pin (VSS) { voltage_name : VSS; pg_type : primary_ground; }']
    if memory:
        L += ["    memory () {", f"      type : {memory['type']};",
              f"      address_width : {memory['address_width']};", f"      word_width : {memory['word_width']};",
              "    }"]
    clocks = [p for p in pins if p.kind == "clock"]
    for c in clocks:
        L += [f"    pin ({c.name}) {{", "      direction : input;", "      clock : true;",
              f"      capacitance : {t.clk_cap_ff:.4f};", "      related_power_pin : VDD;",
              "      related_ground_pin : VSS;",
              f"      min_period : {t.min_period_ps:.3f};",
              f"      min_pulse_width_high : {t.min_pulse_ps:.3f};",
              f"      min_pulse_width_low : {t.min_pulse_ps:.3f};",
              "      internal_power () {",
              "        rise_power (mc_energy) {",
              f'          index_1 ("{", ".join(f"{v:g}" for v in SLEW_INDEX_PS)}");',
              f'          values ({_fmt_row([t.read_energy_fj] * len(SLEW_INDEX_PS))});', "        }",
              "        fall_power (mc_energy) {",
              f'          index_1 ("{", ".join(f"{v:g}" for v in SLEW_INDEX_PS)}");',
              f'          values ({_fmt_row([0.0] * len(SLEW_INDEX_PS))});', "        }", "      }", "    }"]
    for p in pins:
        if p.kind == "clock":
            continue
        head = f"    bus ({p.name}) {{" if p.width > 1 else f"    pin ({p.name}) {{"
        L.append(head)
        if p.width > 1:
            L.append(f"      bus_type : {name}_{p.name}_t;")
        L += [f"      direction : {p.direction};", "      related_power_pin : VDD;", "      related_ground_pin : VSS;"]
        if p.direction == "output":
            L += ["      max_capacitance : 46.08;", "      timing () {", f'        related_pin : "{p.related}";',
                  "        timing_type : rising_edge;", "        timing_sense : non_unate;"]
            for kind in ("cell_rise", "cell_fall"):
                L.append(f"        {kind} (mc_delay) {{")
                L += ["        " + s for s in _table(
                    lambda s, c: t.clk_to_q_ps + 0.20 * (s - SLEW_INDEX_PS[0]) + t.out_r_kohm * (c - LOAD_INDEX_FF[0]),
                    SLEW_INDEX_PS, LOAD_INDEX_FF)]
                L.append("        }")
            for kind in ("rise_transition", "fall_transition"):
                L.append(f"        {kind} (mc_delay) {{")
                L += ["        " + s for s in _table(
                    lambda s, c: t.out_slew_intrinsic_ps + 2.2 * t.out_r_kohm * c, SLEW_INDEX_PS, LOAD_INDEX_FF)]
                L.append("        }")
            L.append("      }")
        else:
            L.append(f"      capacitance : {t.pin_cap_ff:.4f};")
            for ttype, base, sgn in (("setup_rising", t.setup_ps, 1.0), ("hold_rising", t.hold_ps, -1.0)):
                L += ["      timing () {", f'        related_pin : "{p.related}";', f"        timing_type : {ttype};"]
                for kind in ("rise_constraint", "fall_constraint"):
                    L.append(f"        {kind} (mc_constraint) {{")
                    L += ["        " + s for s in _table(
                        lambda d, c, base=base, sgn=sgn: base + sgn * (0.25 * (d - SLEW_INDEX_PS[0])
                                                                      - 0.10 * (c - SLEW_INDEX_PS[0])),
                        SLEW_INDEX_PS, SLEW_INDEX_PS)]
                    L.append("        }")
                L.append("      }")
        L.append("    }")
    L += ["  }", "}"]
    return "\n".join(L) + "\n"


def verilog_port_decl(pins: list[Pin]) -> str:
    out = []
    for p in pins:
        rng = f"[{p.width - 1}:0] " if p.width > 1 else ""
        kind = "output reg " if p.direction == "output" else "input  wire "
        out.append(f"    {kind}{rng}{p.name}")
    return ",\n".join(out)


def blackbox_verilog(name: str, pins: list[Pin], header: str) -> str:
    ports = []
    for p in pins:
        rng = f"[{p.width - 1}:0] " if p.width > 1 else ""
        ports.append(f"    {p.direction} wire {rng}{p.name}")
    return (f"// {header}\n// Blackbox view for synthesis and place-and-route (the hard macro).\n"
            f"(* blackbox *)\nmodule {name} (\n" + ",\n".join(ports) + "\n);\nendmodule\n")
