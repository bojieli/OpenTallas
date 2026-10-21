#!/usr/bin/env python3
"""DIAGNOSTIC-ONLY stand-in abstract of a GATED (not yet closed) tile, for a parent cluster gate while the tile's route
runs (PL-TP192 10-18; generalises tools/qwen_cluster/stn_standin.py).  NEVER bindable: the output carries
STANDIN_NOT_A_VIEW and PROVISIONAL_NOT_A_VIEW.

    standin_from_gate.py KIT_DIR OUT_DIR [--ss-scale 1.35]

From KIT_DIR (a tools/ref_tile kit): spec.json (outline, clock_ports, clock_entry_domains or clock_port, layer_cap),
io_spread.tcl / any place_pin script named by spec io_tcl (exact pin names, layers, locations, sizes) and
gate_result.json (clock.clock_measurements: per clock port boundary mean/min/max at TT and FF; SS = TT x --ss-scale,
assumed).  Every data pin is registered on its domain's clock pin with that insertion (ETM-shaped like stn_standin).
Body: PG M5 stripes (pitch 5.4) as pins; OBS M1-M4 full, M5 between the stripes, M6+ free (child_lint (c)),
pin-access windows (tools/abstract_pin_windows.py) at every face pin cluster.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import abstract_pin_windows as APW   # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TRACK = {"M3": (0.009, 0.036), "M4": (0.012, 0.048), "M5": (0.012, 0.048), "M6": (0.016, 0.064)}   # asap7 make_tracks
FLOP = {"tt": (40.0, 15.0, 55.0), "ff": (30.0, 12.0, 40.0), "ss": (55.0, 20.0, 75.0)}   # setup, hold, clk->q


def rtl_dirs(spec):
    """port base -> 'in' / 'out' from the top module header in the spec sources"""
    txt = "\n".join((ROOT / f).read_text(errors="replace") for f in spec["sources"])
    txt = re.sub(r"//[^\n]*", "", txt)
    # skip a #(parameter ...) list (e86 FAN32/SEAM) before the port list
    m = re.search(rf"\bmodule\s+{re.escape(spec['top'])}\b\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s*\((.*?)\);", txt, re.S)
    out, d = {}, None
    for it in m.group(1).split(","):
        it = " ".join(it.split())
        mm = re.match(r"(input|output)?\s*(?:wire|reg|logic)?\s*(\[[^\]]*\])?\s*(\w+)$", it)
        if mm:
            d = mm.group(1) or d
            out[mm.group(3)] = "in" if d == "input" else "out"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kit")
    ap.add_argument("out")
    ap.add_argument("--ss-scale", type=float, default=1.35)
    a = ap.parse_args()
    kit = Path(a.kit)
    spec = json.loads((kit / "spec.json").read_text())
    name = spec["top"]
    W, H = float(spec["outline"]["w"]), float(spec["outline"]["h"])
    dirs = rtl_dirs(spec)
    cks = spec.get("clock_ports") or [spec["clock_port"]]
    dom = {}
    for dn, d in (spec.get("clock_entry_domains") or {}).items():
        for p in d.get("inputs", []) + d.get("outputs", []):
            dom[p] = d["ports"][0]
    g = json.loads((kit / "gate_result.json").read_text())
    R, NALL, INTERNAL = {}, {}, set()
    for m in g["clock"]["clock_measurements"]:
        for c in ("tt", "ff"):
            b = (m.get(c) or {}).get("boundary") or (m.get(c) or {}).get("all")
            if b:
                R.setdefault(m["source"], {})[c] = (b["mean"], b["min"], b["max"])
            if not (m.get(c) or {}).get("boundary") and (m.get(c) or {}).get("all"):
                # HBM-TP192 10-21: an internal-only CTS root of the gated tile (no boundary flops, no ETM check arc;
                # e86 clk_r1/clk_r2) is recorded like the routed view records it: an all-internal-sink reference, no
                # boundary -> the parent's clock_entry_constraints measures it directly on its region root
                INTERNAL.add(m["source"])
                NALL[m["source"]] = int((m.get(c) or {})["all"]["n"])
    for ck in cks:
        R.setdefault(ck, R.get(cks[0], {}))
        R[ck]["ss"] = tuple(v * a.ss_scale for v in R[ck]["tt"])
    io = ROOT / spec["io_tcl"] if spec.get("io_tcl") else kit / "io_spread.tcl"
    pins = []
    for mm in re.finditer(r"place_pin -pin_name \{([^}]+)\} -layer (M\d) -location \{([\d.]+) ([\d.]+)\} -pin_size \{([\d.]+) ([\d.]+)\}",
                          io.read_text()):
        p, lay, x, y, sw, sh = mm.group(1), mm.group(2), *map(float, mm.groups()[2:])
        base = p.split("[")[0]
        off, pit = TRACK.get(lay, (0.012, 0.048))   # along-face centre on the layer's track (place_pin snaps the same)
        if y >= H - 1e-3 or y <= 1e-3:
            x = round(off + round((x - off) / pit) * pit, 4)
        else:
            y = round(off + round((y - off) / pit) * pit, 4)
        # -pin_size {w h} is absolute (x, y); -force_to_die_boundary puts the rect inside the die at its face
        if y >= H - 1e-3:
            r = (x - sw / 2, H - sh, x + sw / 2, H)
        elif y <= 1e-3:
            r = (x - sw / 2, 0.0, x + sw / 2, sh)
        elif x <= 1e-3:
            r = (0.0, y - sh / 2, sw, y + sh / 2)
        else:
            r = (W - sw, y - sh / 2, W, y + sh / 2)
        pins.append((p, base, lay, tuple(round(v, 4) for v in r)))
    seen = {p[1] for p in pins}
    miss = [b for b in dirs if b not in seen]
    if miss:
        raise SystemExit(f"ports without a place_pin: {miss}")
    cap = int(str(spec.get("layer_cap", "M5"))[1:])
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {name}", "  CLASS BLOCK ;",
         "  ORIGIN 0 0 ;", f"  FOREIGN {name} 0 0 ;", f"  SIZE {W} BY {H} ;", "  SYMMETRY X Y ;"]
    for p, base, lay, r in pins:
        L += [f"  PIN {p}", f"    DIRECTION {'OUTPUT' if dirs[base] == 'out' else 'INPUT'} ;",
              f"    USE {'CLOCK' if base in cks else 'SIGNAL'} ;", "    PORT", f"      LAYER {lay} ;",
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
    E = 0.5
    dep = min(float(os.environ.get("OT_ABS_PIN_WINDOW_UM", "10.8")), 0.25 * min(W, H))
    pr = [(p, lay, r) for p, _b, lay, r in pins]
    lo = min(int(lay[1:]) for _p, lay, _r in pr)
    top = 5
    win = APW.windows(W, H, pr, dep, max(lo, 1), top)
    L += ["  OBS"]
    for k in [1, 2, 3, 4]:          # M6 left free (child_lint (c): the parent strap layer above the M5 PG)
        L += [f"    LAYER M{k} ;"] + ["      RECT %.3f %.3f %.3f %.3f ;" % q
                                     for q in APW.minus_rect((E, E, W - E, H - E), win.get(k, []))]
    L += ["    LAYER M5 ;"]
    xs = sorted(stripes["VDD"] + stripes["VSS"])
    edges = [E] + [v for x in xs for v in (x, x + 0.12)] + [W - E]
    for x0, x1 in zip(edges[::2], edges[1::2]):
        if x1 - x0 > 0.05:
            for q in APW.minus_rect((x0, E + 0.4, x1, H - E - 0.4), win.get(5, [])):
                L.append("      RECT %.3f %.3f %.3f %.3f ;" % q)
    L += ["  END", f"END {name}", "END LIBRARY"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.lef").write_text("\n".join(L) + "\n")
    buses = {}
    for p, base, *_ in pins:
        mm = re.fullmatch(r"(\w+)\[(\d+)\]", p)
        if mm:
            buses.setdefault(base, []).append(int(mm.group(2)))
    for c in ("tt", "ff", "ss"):
        su, ho, cq = FLOP[c]

        def body(p, base):
            if base in cks:
                mean, mn, mx = R[base][c]
                arcs = []
                for tt, v in (("min_clock_tree_path", mn), ("max_clock_tree_path", mx)):
                    arcs += [f"      timing() {{ timing_type : {tt}; timing_sense : positive_unate;",
                             f'        cell_rise(scalar) {{ values("{v:.1f}"); }} cell_fall(scalar) {{ values("{v:.1f}"); }} }}']
                return [f'    pin("{p}") {{', "      direction : input;", "      clock : true;", "      capacitance : 2.0;"] + arcs + ["    }"]
            ck = dom.get(base, cks[0])
            r = R[ck][c][0]
            if dirs[base] == "out":
                return [f'    pin("{p}") {{', "      direction : output;",
                        f'      timing() {{ related_pin : "{ck}"; timing_type : rising_edge;',
                        f'        cell_rise(scalar) {{ values("{r + cq:.1f}"); }} cell_fall(scalar) {{ values("{r + cq:.1f}"); }}',
                        '        rise_transition(scalar) { values("25.0"); } fall_transition(scalar) { values("25.0"); } }', "    }"]
            return [f'    pin("{p}") {{', "      direction : input;", "      capacitance : 1.0;",
                    f'      timing() {{ related_pin : "{ck}"; timing_type : setup_rising;',
                    f'        rise_constraint(scalar) {{ values("{su - r:.1f}"); }} fall_constraint(scalar) {{ values("{su - r:.1f}"); }} }}',
                    f'      timing() {{ related_pin : "{ck}"; timing_type : hold_rising;',
                    f'        rise_constraint(scalar) {{ values("{ho + r:.1f}"); }} fall_constraint(scalar) {{ values("{ho + r:.1f}"); }} }}', "    }"]
        Lb = [f"library ({name}_{c}) {{", "  delay_model : table_lookup;", "  capacitive_load_unit (1,fF);",
              '  time_unit : "1ps";', '  voltage_unit : "1v";', '  current_unit : "1mA";', '  pulling_resistance_unit : "1kohm";',
              '  leakage_power_unit : 1pW;', "  input_threshold_pct_rise : 50;", "  input_threshold_pct_fall : 50;",
              "  output_threshold_pct_rise : 50;", "  output_threshold_pct_fall : 50;", "  slew_lower_threshold_pct_rise : 10;",
              "  slew_lower_threshold_pct_fall : 10;", "  slew_upper_threshold_pct_rise : 90;", "  slew_upper_threshold_pct_fall : 90;",
              "  nom_process : 1.0;", "  nom_temperature : 25.0;", "  nom_voltage : 0.70;"]
        for b, idx in buses.items():
            Lb += [f'  type ("{b}") {{ base_type : array; data_type : bit; bit_width : {len(idx)}; bit_from : {max(idx)}; bit_to : 0; }}']
        Lb += [f'  cell ("{name}") {{', f"    area : {W * H:.1f};", "    is_macro_cell : true;"]
        for p, base, *_ in pins:
            if base not in buses:
                Lb += body(p, base)
        for b, idx in buses.items():
            Lb += [f'    bus("{b}") {{', f"      bus_type : {b};", f"      direction : {'output' if dirs[b] == 'out' else 'input'};"]
            for i in sorted(idx, reverse=True):
                Lb += ["  " + x for x in body(f"{b}[{i}]", b)]
            Lb += ["    }"]
        Lb += ["  }", "}"]
        (out / f"{name}_{c}.lib").write_text("\n".join(Lb) + "\n")
    ins = {"schema": "opentallas.closure_loop.ck_insertion.v1", "standin": True, "clock": cks[0],
           "source": str(kit / "gate_result.json"), "ss_assumed_scale": a.ss_scale}
    for c in ("tt", "ff", "ss"):
        mean, mn, mx = R[cks[0]][c]
        ins[c] = {"boundary": {"n": len(pins), "mean": mean, "min": mn, "max": mx}, "errors": [],
                  "per_clock": {ck: dict(zip(("mean", "min", "max"), R[ck][c])) for ck in cks}}
    if len(cks) > 1:
        # multi-root child (ck_insertion.py form): one record per Liberty clock pin, so a parent's clock_entry_constraints
        # binds each pin to its own boundary (else: 'ambiguous routed clock pin association')
        ins["clock_measurements"] = {ck: {"lib_clock_pin": ck, "clock": ck, "standin": True, **{
            c: ({"all": {"n": NALL[ck], **dict(zip(("mean", "min", "max"), R[ck][c]))}, "errors": []} if ck in INTERNAL else
                {"boundary": {"n": len(pins), **dict(zip(("mean", "min", "max"), R[ck][c]))}, "errors": []})
            for c in ("tt", "ff", "ss")}} for ck in cks}
    (out / "insertion.json").write_text(json.dumps(ins, indent=1) + "\n")
    widths = {}
    for p, base, *_ in pins:
        widths[base] = max(widths.get(base, 0), int(p.split("[")[1][:-1]) + 1 if "[" in p else 1)
    ps = [f"    {'output' if dirs[b] == 'out' else 'input'} wire {'[%d:0] ' % (n - 1) if n > 1 else ''}{b}" for b, n in widths.items()]
    (out / f"{name}_bb.v").write_text(f"// DIAGNOSTIC stand-in blackbox (standin_from_gate.py); never bind\n(* blackbox *) module {name} (\n"
                                      + ",\n".join(ps) + "\n);\nendmodule\n")
    (out / "STANDIN_NOT_A_VIEW").write_text(f"diagnostic stand-in from {kit} (gate, not a closed route); never bind\n")
    (out / "PROVISIONAL_NOT_A_VIEW").write_text("standin\n")
    print(f"{name}: {len(pins)} pins, {W} x {H}, clocks {cks}, TT ins {R[cks[0]]['tt']}")


if __name__ == "__main__":
    main()
