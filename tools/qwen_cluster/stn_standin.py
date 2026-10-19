#!/usr/bin/env python3
"""DIAGNOSTIC-ONLY stand-in abstracts of the Q-CLUSTER3 station masters (qfd_c_stn516 / qfd_c_stn514 / qfd_c_xstn,
qc_stn_kit.py) for the qfd_c_b16_dv cluster gates while no routed station view exists.  NEVER bindable: every output
directory carries STANDIN_NOT_A_VIEW and PROVISIONAL_NOT_A_VIEW.

Pins: evenly spread inside the kit's pin_ranges, S / N data alternating M3 / M5 (the kit's pin_balance), E / W on M4,
clock-type pins on M5 (S face).  Body: PG = M5 stripes (pitch 5.4, VDD 0.300 + core margin, VSS +0.192: the leaf-tile
M5 grid) as pins; OBS M1-M4 inset 0.5 um, M5 only between the PG stripes.
Timing (ETM-shaped like a0_standin.py): every data pin registered on ck with insertion R (min R-10 / max R+10), setup /
hold / clk->q of one flop.  R per corner from --ins TT,FF,SS (default the ASSUMED 60,45,80 ps; replace with the station
gates' measured CTS insertion).

    stn_standin.py OUT_DIR [--ins TT,FF,SS]

The committed diag stand-ins use --ins 104,79,150: the station gates of a5f404c21 measured TT 103.7-104.4 / FF 78.4-81.9 /
SS 136-150 ps boundary-mean insertion (spread 3-10 ps) on all four masters.
"""
import argparse
import os
import sys
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTERS = ("qfd_c_stn516", "qfd_c_stn514", "qfd_c_xstn", "qfd_c_xstnw")
FLOP = {"tt": (40.0, 15.0, 55.0), "ff": (30.0, 12.0, 40.0), "ss": (55.0, 20.0, 75.0)}   # setup, hold, clk->q
WIDTH = {"d": None, "q": None, "b_d": 516, "a_d": 516, "tap_d": 508, "sidx": 3, "ck": 1, "rst_n": 1}
OUTS = {"q", "a_d", "tap_d"}
TRACK = {"M3": (0.009, 0.036), "M4": (0.012, 0.048), "M5": (0.012, 0.048)}   # (offset, pitch) of the pin coordinate


def pins_of(spec):
    w = {"qfd_c_stn516": 516, "qfd_c_stn514": 514}.get(spec["name"])
    out = []
    for face, names in spec["pins"].items():
        for n in names:
            bits = WIDTH[n] or w
            lo, hi = spec["pin_ranges"][n]
            for i in range(bits):
                pos = lo + (hi - lo) * (i + 0.5) / bits
                if face in "SN":
                    lay = "M5" if n in ("ck", "rst_n") else ("M3" if i % 2 == 0 else "M5")
                else:
                    lay = "M4"
                off, pit = TRACK[lay]
                pos = off + round((pos - off) / pit) * pit      # on the layer's track (asap7 make_tracks)
                out.append((f"{n}[{i}]" if bits > 1 else n, n, face, lay, round(pos, 3)))
    return out


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import abstract_pin_windows as APW   # noqa: E402


def lef(name, W, H, pl):
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {name}", "  CLASS BLOCK ;",
         "  ORIGIN 0 0 ;", f"  FOREIGN {name} 0 0 ;", f"  SIZE {W} BY {H} ;", "  SYMMETRY X Y ;"]
    pinrects = []
    for p, base, face, lay, pos in pl:
        d = "OUTPUT" if base in OUTS else "INPUT"
        use = "CLOCK" if base == "ck" else "SIGNAL"
        if face in "SN":
            y0, y1 = (0.0, 0.192) if face == "S" else (H - 0.192, H)
            r = (pos - 0.012, y0, pos + 0.012, y1)
        else:
            x0, x1 = (0.0, 0.192) if face == "W" else (W - 0.192, W)
            r = (x0, pos - 0.012, x1, pos + 0.012)
        pinrects.append((p, lay, r))
        L += [f"  PIN {p}", f"    DIRECTION {d} ;", f"    USE {use} ;", "    PORT", f"      LAYER {lay} ;",
              "        RECT %.3f %.3f %.3f %.3f ;" % r, "    END", f"  END {p}"]
    stripes = {}
    for net, use, off in (("VDD", "POWER", 2.16 + 0.300), ("VSS", "GROUND", 2.16 + 0.300 + 0.192)):
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", "      LAYER M5 ;"]
        x = off
        while x + 0.12 < W - 2.16:
            L.append("        RECT %.3f 0.500 %.3f %.3f ;" % (x, x + 0.12, H - 0.5))
            stripes.setdefault(net, []).append(x)
            x += 5.4
        L += ["    END", f"  END {net}"]
    # Q-DIE11 10-18 (coordinator): pin-access windows at every face pin cluster (tools/abstract_pin_windows.py,
    # OT_ABS_PIN_WINDOW_UM default 10.8, capped at a quarter of the short side) free of OBS on M<lowest pin layer>..M5.
    E = 0.5
    dep = min(float(os.environ.get("OT_ABS_PIN_WINDOW_UM", "10.8")), 0.25 * min(W, H))
    lo = min(int(lay[1:]) for _p, lay, _r in pinrects) if pinrects else 4
    win = APW.windows(W, H, pinrects, dep, max(lo, 1), 5)
    L += ["  OBS"]
    for k in range(1, 5):
        L += [f"    LAYER M{k} ;"] + ["      RECT %.3f %.3f %.3f %.3f ;" % q
                                     for q in APW.minus_rect((E, E, W - E, H - E), win.get(k, []))]
    L += ["    LAYER M5 ;"]
    xs = sorted(stripes["VDD"] + stripes["VSS"])
    edges = [E] + [v for x in xs for v in (x, x + 0.12)] + [W - E]      # OBS abuts every stripe: no own-layer pocket
    for a, b in zip(edges[::2], edges[1::2]):
        if b - a > 0.05:
            for q in APW.minus_rect((a, E + 0.4, b, H - E - 0.4), win.get(5, [])):
                L.append("      RECT %.3f %.3f %.3f %.3f ;" % q)
    L += ["  END", f"END {name}", "END LIBRARY"]
    return "\n".join(L) + "\n"


def lib(name, W, H, pl, corner, R):
    su, ho, cq = FLOP[corner]
    r = R[corner]
    buses, scal = {}, []
    for p, base, *_ in pl:
        m = re.fullmatch(r"(\w+)\[(\d+)\]", p)
        if m:
            buses.setdefault(m.group(1), []).append(int(m.group(2)))
        else:
            scal.append(p)

    def body(p, base):
        if base == "ck":
            arcs = []
            for tt, v in (("min_clock_tree_path", r - 10), ("max_clock_tree_path", r + 10)):
                arcs += [f"      timing() {{ timing_type : {tt}; timing_sense : positive_unate;",
                         f'        cell_rise(scalar) {{ values("{v:.1f}"); }} cell_fall(scalar) {{ values("{v:.1f}"); }} }}']
            return [f'    pin("{p}") {{', "      direction : input;", "      clock : true;", "      capacitance : 2.0;"] + arcs + ["    }"]
        if base in OUTS:
            t = [f'      timing() {{ related_pin : "ck"; timing_type : rising_edge;',
                 f'        cell_rise(scalar) {{ values("{r + cq:.1f}"); }} cell_fall(scalar) {{ values("{r + cq:.1f}"); }}',
                 '        rise_transition(scalar) { values("25.0"); } fall_transition(scalar) { values("25.0"); } }']
            return [f'    pin("{p}") {{', "      direction : output;"] + t + ["    }"]
        t = [f'      timing() {{ related_pin : "ck"; timing_type : setup_rising;',
             f'        rise_constraint(scalar) {{ values("{su - r:.1f}"); }} fall_constraint(scalar) {{ values("{su - r:.1f}"); }} }}',
             f'      timing() {{ related_pin : "ck"; timing_type : hold_rising;',
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
    widths = {}
    for p, base, *_ in pl:
        widths[base] = max(widths.get(base, 0), int(p.split("[")[1][:-1]) + 1 if "[" in p else 1)
    ps = [f"    {'output' if b in OUTS else 'input'} wire {'[%d:0] ' % (n - 1) if n > 1 else ''}{b}" for b, n in widths.items()]
    return f"(* blackbox *) module {name} (\n" + ",\n".join(ps) + "\n);\nendmodule\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--ins", default="60,45,80", help="TT,FF,SS clock insertion (ps) to the station flops")
    a = ap.parse_args()
    tt, ff, ss = (float(v) for v in a.ins.split(","))
    R = {"tt": tt, "ff": ff, "ss": ss}
    out = Path(a.out)
    bbs = []
    for name in MASTERS:
        s = json.loads((ROOT / "tools/ref_tile/specs_qcluster" / f"{name}.json").read_text())
        W, H = s["outline"]["w"], s["outline"]["h"]
        pl = pins_of(s)
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.lef").write_text(lef(name, W, H, pl))
        for c in ("tt", "ff", "ss"):
            (d / f"{name}_{c}.lib").write_text(lib(name, W, H, pl, c, R))
        ins = {"schema": "opentallas.closure_loop.ck_insertion.v1", "standin": True, "clock": "ck", "assumed_ps": R}
        for c in ("tt", "ff", "ss"):
            ins[c] = {"boundary": {"n": len(pl), "mean": R[c], "min": R[c] - 10, "max": R[c] + 10}, "errors": []}
        (d / "insertion.json").write_text(json.dumps(ins, indent=1) + "\n")
        (d / "STANDIN_NOT_A_VIEW").write_text("diagnostic stand-in from the station kit pin plan; never bind\n")
        (d / "PROVISIONAL_NOT_A_VIEW").write_text("standin\n")
        bbs.append(bb(name, pl))
        print(name, len(pl), "pins", W, "x", H)
    (out / "stn_bb.v").write_text("// DIAGNOSTIC stand-in blackboxes of the station masters (stn_standin.py); never bind\n" + "".join(bbs))


if __name__ == "__main__":
    main()
