#!/usr/bin/env python3
"""DIAGNOSTIC-ONLY stand-in abstracts of the A0 ROM-leaf parents (qfd_tile_{nk,nl}_rp2_romleaf_rr, Q-ROMPARENT-2 c1)
for the qfd_c_b16_dv cluster gates while no CLOSED A0 view exists.  NEVER bindable: every output directory carries
STANDIN_NOT_A_VIEW and PROVISIONAL_NOT_A_VIEW, and the cluster kit that uses them is a *_diag kit with submit false.

Pins: exact locations / layers from the c1 pin scripts (tools/qwen_romleaf/parent_{nk,nl}_c1_pins.tcl at A0_REF).
Body: OBS M1-M7 over the whole outline (A0 is a cluster: signals + PG <= M7).
Timing (ETM-shaped, same form as ref_tile exports): every data pin registered on its A0 face root
(tap / tile_id / rst_n: ck_fa4, n_a: ck_fa0, n_b: ck_fa1, t_out: ck_fa2, n_y: ck_fa3; NL: t_out ck_fa2, rest ck_fa4);
setup / hold / clk->q = assumed insertion R + a flop, R = insertion.json boundary mean (TT 220, FF 170, SS 290 ps:
the A0 c1 gate target <= 220 / 190).  These numbers are assumptions, not measurements.

    a0_standin.py OUT_DIR
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A0_REF = "origin/codex/romleaf-native-1621"
W, H = 457.92, 1166.4
R = {"tt": 220.0, "ff": 170.0, "ss": 290.0}
FLOP = {"tt": (40.0, 15.0, 55.0), "ff": (30.0, 12.0, 40.0), "ss": (55.0, 20.0, 75.0)}   # setup, hold, clk->q
REL_NK = {"tap": "ck_fa4", "tile_id": "ck_fa4", "rst_n": "ck_fa4", "n_a": "ck_fa0", "n_b": "ck_fa1",
          "t_out": "ck_fa2", "n_y": "ck_fa3"}
OUTS = {"t_out", "n_y", "tie_hi", "tie_lo"}


def pins(kind):
    src = subprocess.run(["git", "-C", str(ROOT), "show", f"{A0_REF}:tools/qwen_romleaf/parent_{kind}_c1_pins.tcl"],
                         check=True, capture_output=True, text=True).stdout
    out = []
    for m in re.finditer(r"place_pin -pin_name \{([^}]+)\} -layer (M\d) -location \{([\d.]+) ([\d.]+)\}", src):
        out.append((m.group(1), m.group(2), float(m.group(3)), float(m.group(4))))
    return out


def lef(name, pl):
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {name}", "  CLASS BLOCK ;",
         "  ORIGIN 0 0 ;", f"  FOREIGN {name} 0 0 ;", f"  SIZE {W} BY {H} ;", "  SYMMETRY X Y ;"]
    for p, lay, x, y in pl:
        base = p.split("[")[0]
        d = "OUTPUT" if base in OUTS else "INPUT"
        use = "CLOCK" if base.startswith("ck") else "SIGNAL"
        if lay == "M4":       # W / E face, horizontal stub
            x0, x1 = (0.0, 0.192) if x < W / 2 else (W - 0.192, W)
            r = (x0, y - 0.012, x1, y + 0.012)
        else:                 # S / N face, vertical stub
            y0, y1 = (0.0, 0.192) if y < H / 2 else (H - 0.192, H)
            r = (x - 0.012, y0, x + 0.012, y1)
        L += [f"  PIN {p}", f"    DIRECTION {d} ;", f"    USE {use} ;", "    PORT", f"      LAYER {lay} ;",
              "        RECT %.3f %.3f %.3f %.3f ;" % r, "    END", f"  END {p}"]
    for net, use, off in (("VDD", "POWER", 1.0), ("VSS", "GROUND", 6.4)):   # A0 PG: M7 stripes pitch 10.8 (cluster PG M7)
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", "      LAYER M7 ;"]
        x = off
        while x + 0.288 < W:
            L.append("        RECT %.3f 0.000 %.3f %.3f ;" % (x, x + 0.288, H))
            x += 10.8
        L += ["    END", f"  END {net}"]
    # OBS like a ref_tile export: inset 0.5 um from every face (face-pin access, child_lint (f)); M7 only between the PG
    # stripes (no bloat over the PG layer, child_lint (a))
    E = 0.5
    L += ["  OBS"] + [f"    LAYER M{k} ;\n      RECT {E:.3f} {E:.3f} {W - E:.3f} {H - E:.3f} ;" for k in range(1, 7)]
    L += ["    LAYER M7 ;"]
    x = 1.0 + 0.288 + 0.2
    while x < W - E:
        nxt = x + 5.4 - 0.288 - 0.4
        L.append("      RECT %.3f %.3f %.3f %.3f ;" % (x, E, min(nxt, W - E), H - E))
        x = nxt + 0.288 + 0.4
    L += ["  END", f"END {name}", "END LIBRARY"]
    return "\n".join(L) + "\n"


def lib(name, pl, corner, nl):
    su, ho, cq = FLOP[corner]
    r = R[corner]
    buses, scal = {}, []
    for p, *_ in pl:
        m = re.fullmatch(r"(\w+)\[(\d+)\]", p)
        if m:
            buses.setdefault(m.group(1), []).append(int(m.group(2)))
        else:
            scal.append(p)
    rel = dict(REL_NK)
    if nl:
        rel.update({k: "ck_fa4" for k in ("n_a", "n_b", "n_y")})

    def body(p, base):
        if base.startswith("ck"):
            arcs = []
            for tt, v in (("min_clock_tree_path", r - 15), ("max_clock_tree_path", r + 15)):
                arcs += [f"      timing() {{ timing_type : {tt}; timing_sense : positive_unate;",
                         f'        cell_rise(scalar) {{ values("{v:.1f}"); }} cell_fall(scalar) {{ values("{v:.1f}"); }} }}']
            return [f'    pin("{p}") {{', "      direction : input;", "      clock : true;", "      capacitance : 2.0;"] + arcs + ["    }"]
        if base in ("tie_hi", "tie_lo"):
            return [f'    pin("{p}") {{', "      direction : output;", "    }"]
        ck = rel[base]
        if base in OUTS:
            t = [f'      timing() {{ related_pin : "{ck}"; timing_type : rising_edge;',
                 f'        cell_rise(scalar) {{ values("{r + cq:.1f}"); }} cell_fall(scalar) {{ values("{r + cq:.1f}"); }}',
                 '        rise_transition(scalar) { values("25.0"); } fall_transition(scalar) { values("25.0"); } }']
            return [f'    pin("{p}") {{', "      direction : output;"] + t + ["    }"]
        t = [f'      timing() {{ related_pin : "{ck}"; timing_type : setup_rising;',
             f'        rise_constraint(scalar) {{ values("{su - r:.1f}"); }} fall_constraint(scalar) {{ values("{su - r:.1f}"); }} }}',
             f'      timing() {{ related_pin : "{ck}"; timing_type : hold_rising;',
             f'        rise_constraint(scalar) {{ values("{ho + r:.1f}"); }} fall_constraint(scalar) {{ values("{ho + r:.1f}"); }} }}']
        return [f'    pin("{p}") {{', "      direction : input;", "      capacitance : 1.0;"] + t + ["    }"]
    L = [f"library ({name}_{corner}) {{", "  delay_model : table_lookup;", "  capacitive_load_unit (1,fF);",
         '  time_unit : "1ps";', '  voltage_unit : "1v";', '  current_unit : "1mA";', '  pulling_resistance_unit : "1kohm";',
         '  leakage_power_unit : 1pW;', "  input_threshold_pct_rise : 50;", "  input_threshold_pct_fall : 50;",
         "  output_threshold_pct_rise : 50;", "  output_threshold_pct_fall : 50;", "  slew_lower_threshold_pct_rise : 10;",
         "  slew_lower_threshold_pct_fall : 10;", "  slew_upper_threshold_pct_rise : 90;", "  slew_upper_threshold_pct_fall : 90;",
         "  nom_process : 1.0;", "  nom_temperature : 25.0;", "  nom_voltage : 0.70;"]
    for b, idx in buses.items():
        L += [f'  type ("{b}") {{ base_type : array; data_type : bit; bit_width : {len(idx)}; bit_from : {max(idx)}; bit_to : 0; }}']
    L += [f'  cell ("{name}") {{', f"    area : {W * H:.1f};", "    is_macro_cell : true;"]
    for p in scal:
        L += body(p, p)
    for b, idx in buses.items():
        L += [f'    bus("{b}") {{', f"      bus_type : {b};", f"      direction : {'output' if b in OUTS else 'input'};"]
        for i in sorted(idx, reverse=True):
            L += ["  " + x for x in body(f"{b}[{i}]", b)]
        L += ["    }"]
    L += ["  }", "}"]
    return "\n".join(L) + "\n"


def bb(name, pl):
    """blackbox module (ports only) for the parent's synthesis: the child is a hard LEF / LIB instance"""
    widths = {}
    for p, *_ in pl:
        b = p.split("[")[0]
        widths[b] = max(widths.get(b, 0), int(p.split("[")[1][:-1]) + 1 if "[" in p else 1)
    ps = []
    for b, n in widths.items():
        d = "output" if b in OUTS else "input"
        ps.append(f"    {d} wire {'[%d:0] ' % (n - 1) if n > 1 else ''}{b}")
    return f"(* blackbox *) module {name} (\n" + ",\n".join(ps) + "\n);\nendmodule\n"


def main(out):
    out = Path(out)
    bbs = []
    for kind in ("nk", "nl"):
        name = f"qfd_tile_{kind}_rp2_romleaf_rr"
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        pl = pins(kind)
        bbs.append(bb(name, pl))
        (d / f"{name}.lef").write_text(lef(name, pl))
        for c in ("tt", "ff", "ss"):
            (d / f"{name}_{c}.lib").write_text(lib(name, pl, c, kind == "nl"))
        ins = {"schema": "opentallas.closure_loop.ck_insertion.v1", "standin": True, "clock": "ck_fa4"}
        for c in ("tt", "ff", "ss"):
            ins[c] = {"boundary": {"n": len(pl), "mean": R[c], "min": R[c] - 15, "max": R[c] + 15}, "errors": []}
        (d / "insertion.json").write_text(json.dumps(ins, indent=1) + "\n")
        (d / "STANDIN_NOT_A_VIEW").write_text("diagnostic stand-in from c1 pins; never bind\n")
        (d / "PROVISIONAL_NOT_A_VIEW").write_text("standin\n")
        print(name, len(pl), "pins")
    (out / "a0_rr_bb.v").write_text("// DIAGNOSTIC stand-in blackboxes of the A0 c1 parents (a0_standin.py); never bind\n" + "".join(bbs))


if __name__ == "__main__":
    main(sys.argv[1])
