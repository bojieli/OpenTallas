#!/usr/bin/env python3
"""DIAGNOSTIC-ONLY stand-in abstracts of the A0 ROM-leaf parents (qfd_tile_{nk,nl}_rp2_romleaf_rr, Q-ROMPARENT-2 c1)
for the qfd_c_b16_dv cluster gates while no CLOSED A0 view exists.  NEVER bindable: every output directory carries
STANDIN_NOT_A_VIEW and PROVISIONAL_NOT_A_VIEW, and the cluster kit that uses them is a *_diag kit with submit false.

Pins: exact locations / layers from the c1 pin scripts (tools/qwen_romleaf/parent_{nk,nl}_c1_pins.tcl at A0_REF).
Body: OBS M1-M7 over the whole outline (A0 is a cluster: signals + PG <= M7) minus pin-access windows at every face pin
cluster (tools/abstract_pin_windows.py, Q-DIE11 10-18).
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
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import abstract_pin_windows as APW   # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
A0_REF = "30d3d3510"   # Q-ROMPARENT-2 c1r6 (codex/romleaf-native-1621): ck_tx4/5 on E face M4, mirror-legal
W, H = 457.92, 1166.4
R = {"tt": 220.0, "ff": 170.0, "ss": 290.0}
# Q-CLUSTER4 (coordinator 0de+6 (1)): every A0 clock entry carries its MEASURED internal insertion (pin latency, so the
# cluster CTS balances at child flops).  Entries passed straight to a closed leaf take that leaf view's measured
# insertion.json 'all' (mean, min, max) per corner (origin/main views); entries that are A0 c1 CTS roots take the A0 c1
# gate measurements (Q-ROMPARENT-2 HANDOFF 0cg: NK c1r4 / NL c1r6 TT max: ck 190.5 NK / 197.4 NL, tx4 219.4, tx5 214.1
# NK (b3) / 208.3 NL, tx3 202.0, every other root <= 150 -> 150), FF / SS scaled by the romleaf FF/TT, SS/TT ratios.
LEAF = {"rp": {"tt": (201.5, 175.3, 228.1), "ff": (168.2, 139.4, 194.9), "ss": (256.8, 229.4, 282.3)},   # ot_qwen_tile_romleaf
        "lsl": {"tt": (165.3, 159.2, 176.7), "ff": (133.6, 127.5, 144.9), "ss": (220.5, 213.6, 231.9)},  # ot_qwen_tile_lsl_fp1
        "node": {"tt": (243.1, 227.9, 267.6), "ff": (197.4, 183.8, 219.8), "ss": (321.0, 302.9, 350.7)}}  # ot_qwen_tile_node
A0_ROOT_TT = {"nk": {"ck": 190.5, "ck_tx4": 219.4, "ck_tx5": 214.1, "ck_tx3": 202.0},
              "nl": {"ck": 197.4, "ck_tx4": 219.4, "ck_tx5": 208.3, "ck_tx3": 202.0}}
SCALE = {"tt": 1.0, "ff": 168.2 / 201.5, "ss": 256.8 / 201.5}


def pin_ins(kind, pin, corner):
    """(mean, min, max) measured insertion of one A0 clock entry"""
    for k in ("rp", "lsl", "node"):
        if pin.startswith("ck_" + k):
            return LEAF[k][corner]
    v = A0_ROOT_TT[kind].get(pin, 150.0) * SCALE[corner]
    return (v, v - 15.0, v)
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
    pinrects = []
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
        pinrects.append((p, lay, r))
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
    # stripes (no bloat over the PG layer, child_lint (a)).
    # Q-DIE11 10-18 (coordinator): the inset alone left the W/E face gcells capacity 0 on M4-M6 (Q-CLUSTER4 c_b16 GRT
    # overflow 585k-747k, mostly M6, in strips along the A0 W/E pin faces).  Every face pin cluster now gets a
    # pin-access window (tools/abstract_pin_windows.py, OT_ABS_PIN_WINDOW_UM, default 10.8 um = one A0 PG period x2)
    # free of OBS on M<lowest pin layer>..M7; M1-M3 stay obstructed.  The closed A0 must keep the windows free there.
    E = 0.5
    rects = [(p, lay, r) for p, lay, r in pinrects]
    dep = float(os.environ.get("OT_ABS_PIN_WINDOW_UM", "10.8"))
    lo = min(int(lay[1:]) for _p, lay, _r in rects) if rects else 4
    win = APW.windows(W, H, rects, dep, max(lo, 1), 7)
    L += ["  OBS"]
    for k in range(1, 7):
        L += [f"    LAYER M{k} ;"] + ["      RECT %.3f %.3f %.3f %.3f ;" % q
                                     for q in APW.minus_rect((E, E, W - E, H - E), win.get(k, []))]
    L += ["    LAYER M7 ;"]
    x = 1.0 + 0.288 + 0.2
    while x < W - E:
        nxt = x + 5.4 - 0.288 - 0.4
        for q in APW.minus_rect((x, E, min(nxt, W - E), H - E), win.get(7, [])):
            L.append("      RECT %.3f %.3f %.3f %.3f ;" % q)
        x = nxt + 0.288 + 0.4
    L += ["  END", f"END {name}", "END LIBRARY"]
    return "\n".join(L) + "\n"


def lib(name, pl, corner, nl):
    su, ho, cq = FLOP[corner]
    kind = "nl" if nl else "nk"
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
            _, lo, hi = pin_ins(kind, p, corner)
            for tt, v in (("min_clock_tree_path", lo), ("max_clock_tree_path", hi)):
                arcs += [f"      timing() {{ timing_type : {tt}; timing_sense : positive_unate;",
                         f'        cell_rise(scalar) {{ values("{v:.1f}"); }} cell_fall(scalar) {{ values("{v:.1f}"); }} }}']
            return [f'    pin("{p}") {{', "      direction : input;", "      clock : true;", "      capacitance : 2.0;"] + arcs + ["    }"]
        if base in ("tie_hi", "tie_lo"):
            return [f'    pin("{p}") {{', "      direction : output;", "    }"]
        ck = rel[base]
        r = pin_ins(kind, ck, corner)[0]
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
        cks = [p for p, *_ in pl if p.startswith("ck")]
        ins["per_pin"] = {c: {p: pin_ins(kind, p, c) for p in cks} for c in ("tt", "ff", "ss")}
        for c in ("tt", "ff", "ss"):
            v = [pin_ins(kind, p, c) for p in cks]
            ins[c] = {"boundary": {"n": len(pl), "mean": round(sum(x[0] for x in v) / len(v), 1),
                                   "min": round(min(x[1] for x in v), 1), "max": round(max(x[2] for x in v), 1)}, "errors": []}
        (d / "insertion.json").write_text(json.dumps(ins, indent=1) + "\n")
        (d / "STANDIN_NOT_A_VIEW").write_text("diagnostic stand-in from c1 pins; never bind\n")
        (d / "PROVISIONAL_NOT_A_VIEW").write_text("standin\n")
        print(name, len(pl), "pins")
    (out / "a0_rr_bb.v").write_text("// DIAGNOSTIC stand-in blackboxes of the A0 c1 parents (a0_standin.py); never bind\n" + "".join(bbs))


if __name__ == "__main__":
    main(sys.argv[1])
