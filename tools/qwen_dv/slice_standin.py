#!/usr/bin/env python3
"""DIAGNOSTIC-ONLY stand-in abstracts of the Q-DV slice hard children (QK-SLICE 10-18) for the hierarchical
qfd_dv_slice2_w cluster gate while the children have no routed view.  NEVER bindable: every output directory carries
STANDIN_NOT_A_VIEW and PROVISIONAL_NOT_A_VIEW, and the cluster kit that uses them is a pathfinding kit (critical, no submit).

Same body / timing form as tools/qwen_cluster/stn_standin.py (generalised to any kit spec):
  pins     the kit spec's face lists (spec["pins"][face] = port base names, in order), port widths / directions from the
           module's ANSI header in spec["sources"]; bits spread evenly over spec["pin_ranges"][port] or the whole face;
           S / N faces alternate M3 / M5, E / W faces M4, the clock port on M5 (child cap M5: the slice parent straps M6,
           PG M7 inside the die's M1-M7 grant).
  body     PG = M5 stripes (pitch 5.4) as pins; OBS M1-M4 and M5 between the stripes, minus pin-access windows.
  timing   every data pin registered on the clock port with an ASSUMED insertion R (min R-10 / max R+10) per corner,
           setup / hold / clk->q of one flop (ETM-shaped).  Replace R with the child's measured gate insertion.

    slice_standin.py SPEC.json OUT_DIR --ins TT,FF,SS [--master NAME]
    slice_standin.py --from-view VIEW_DIR OUT_DIR       M5 re-layer of a CLOSED view with M6 pins (qfd_xs_leaf_w130):
           same pins / positions / directions, every M6 pin moved to the nearest M4 track at the same face position,
           generated M1-M5 OBS with pin-access windows (as above); the view's TT/FF/SS libs and insertion.json are kept
           (measured on the M6 build: the M4 face re-pin changes only the last few um of each E/W pin net).
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import abstract_pin_windows as APW   # noqa: E402

FLOP = {"tt": (40.0, 15.0, 55.0), "ff": (30.0, 12.0, 40.0), "ss": (55.0, 20.0, 75.0)}   # setup, hold, clk->q
TRACK = {"M3": (0.009, 0.036), "M4": (0.012, 0.048), "M5": (0.012, 0.048)}


def preprocess(text, defines):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    out, stack = [], []
    for line in text.splitlines():
        m = re.match(r"\s*`(ifdef|ifndef|else|endif)\b\s*(\w*)", line)
        if not m:
            if all(stack) and not re.match(r"\s*`", line):
                out.append(line)
            continue
        kw, name = m.groups()
        if kw in ("ifdef", "ifndef"):
            stack.append((name in defines) == (kw == "ifdef"))
        elif kw == "else" and stack:
            stack[-1] = not stack[-1]
        elif kw == "endif" and stack:
            stack.pop()
    return "\n".join(out)


def header_ports(sources, top, defines):
    """{port: (dir, width)} from the ANSI header of module top"""
    for src in sources:
        t = preprocess((ROOT / src).read_text(), defines)
        m = re.search(r"\bmodule\s+%s\b" % re.escape(top), t)
        if not m:
            continue
        i = m.end()
        if t[i:].lstrip().startswith("#"):
            j = t.index("(", i)
            d = 0
            for k in range(j, len(t)):
                d += t[k] == "("
                d -= t[k] == ")"
                if d == 0:
                    i = k + 1
                    break
        j = t.index("(", i)
        d, k = 0, j
        for k in range(j, len(t)):
            d += t[k] == "("
            d -= t[k] == ")"
            if d == 0:
                break
        body = t[j + 1:k]
        ports, cur = {}, ("input", 1)
        for item in body.split(","):
            item = item.strip()
            mm = re.match(r"(input|output|inout)?\s*(?:wire|reg|logic)?\s*(?:signed\s*)?(\[([^\]:]+):([^\]]+)\])?\s*(\w+)$", item)
            if not mm:
                raise SystemExit(f"{top}: cannot parse port item {item!r}")
            if mm.group(1):
                w = 1
                if mm.group(2):
                    w = abs(int(eval(mm.group(3), {})) - int(eval(mm.group(4), {}))) + 1
                cur = (mm.group(1), w)
            ports[mm.group(5)] = cur
        return ports
    raise SystemExit(f"module {top} not found in {sources}")


def pins_of(spec, ports):
    W, H = spec["outline"]["w"], spec["outline"]["h"]
    rng = spec.get("pin_ranges", {})
    ck = spec["clock_port"]
    out = []
    for face, names in spec["pins"].items():
        span = W if face in "SN" else H
        nbits = sum(ports[n][1] for n in names if n not in rng)
        k = 0
        for n in names:
            bits = ports[n][1]
            for b in range(bits):
                if n in rng:
                    lo, hi = rng[n]
                    pos = lo + (hi - lo) * (b + 0.5) / bits
                else:
                    pos = 2.16 + (span - 4.32) * (k + 0.5) / max(nbits, 1)
                    k += 1
                if face in "SN":
                    lay = "M5" if n == ck else ("M3" if len(out) % 2 == 0 else "M5")
                else:
                    lay = "M4"
                off, pit = TRACK[lay]
                pos = off + round((pos - off) / pit) * pit
                out.append((f"{n}[{b}]" if bits > 1 else n, n, face, lay, round(pos, 3), ports[n][0]))
    return out


def lef(name, W, H, pl, ck):
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {name}", "  CLASS BLOCK ;",
         "  ORIGIN 0 0 ;", f"  FOREIGN {name} 0 0 ;", f"  SIZE {W} BY {H} ;", "  SYMMETRY X Y ;"]
    pinrects = []
    for p, base, face, lay, pos, d in pl:
        if face in "SN":
            y0, y1 = (0.0, 0.192) if face == "S" else (H - 0.192, H)
            r = (pos - 0.012, y0, pos + 0.012, y1)
        else:
            x0, x1 = (0.0, 0.192) if face == "W" else (W - 0.192, W)
            r = (x0, pos - 0.012, x1, pos + 0.012)
        pinrects.append((p, lay, r))
        L += [f"  PIN {p}", f"    DIRECTION {d.upper()} ;", f"    USE {'CLOCK' if base == ck else 'SIGNAL'} ;", "    PORT",
              f"      LAYER {lay} ;", "        RECT %.3f %.3f %.3f %.3f ;" % r, "    END", f"  END {p}"]
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
    lo = min(int(lay[1:]) for _p, lay, _r in pinrects) if pinrects else 4
    win = APW.windows(W, H, pinrects, dep, max(lo, 1), 5)
    L += ["  OBS"]
    for k in range(1, 5):
        L += [f"    LAYER M{k} ;"] + ["      RECT %.3f %.3f %.3f %.3f ;" % q
                                     for q in APW.minus_rect((E, E, W - E, H - E), win.get(k, []))]
    L += ["    LAYER M5 ;"]
    xs = sorted(stripes["VDD"] + stripes["VSS"])
    edges = [E] + [v for x in xs for v in (x, x + 0.12)] + [W - E]
    for a, b in zip(edges[::2], edges[1::2]):
        if b - a > 0.05:
            for q in APW.minus_rect((a, E + 0.4, b, H - E - 0.4), win.get(5, [])):
                L.append("      RECT %.3f %.3f %.3f %.3f ;" % q)
    L += ["  END", f"END {name}", "END LIBRARY"]
    return "\n".join(L) + "\n"


def lib(name, W, H, pl, corner, R, ck):
    su, ho, cq = FLOP[corner]
    r = R[corner]
    buses, scal, dirs = {}, [], {}
    for p, base, _f, _l, _x, d in pl:
        dirs[base] = d
        m = re.fullmatch(r"(\w+)\[(\d+)\]", p)
        if m:
            buses.setdefault(m.group(1), []).append(int(m.group(2)))
        else:
            scal.append(p)

    def body(p, base):
        if base == ck:
            arcs = []
            for tt, v in (("min_clock_tree_path", r - 10), ("max_clock_tree_path", r + 10)):
                arcs += [f"      timing() {{ timing_type : {tt}; timing_sense : positive_unate;",
                         f'        cell_rise(scalar) {{ values("{v:.1f}"); }} cell_fall(scalar) {{ values("{v:.1f}"); }} }}']
            return [f'    pin("{p}") {{', "      direction : input;", "      clock : true;", "      capacitance : 2.0;"] + arcs + ["    }"]
        if dirs[base] == "output":
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
        L += [f'    bus("{b}") {{', f"      bus_type : {b};", f"      direction : {dirs[b]};"]
        for i in sorted(idx, reverse=True):
            L += ["  " + x for x in body(f"{b}[{i}]", b)]
        L += ["    }"]
    L += ["  }", "}"]
    return "\n".join(L) + "\n"


def bb(name, ports):
    ps = [f"    {d} wire {'[%d:0] ' % (w - 1) if w > 1 else ''}{p}" for p, (d, w) in ports.items()]
    return f"(* blackbox *) module {name} (\n" + ",\n".join(ps) + "\n);\nendmodule\n"


def from_view(view, out):
    view = Path(view)
    lefp = view / f"{view.name}.lef"
    name = lefp.stem
    txt = lefp.read_text()
    W, H = (float(v) for v in re.search(r"SIZE ([\d.]+) BY ([\d.]+)", txt).groups())
    pl, stripes = [], {}
    for m in re.finditer(r"\n  PIN (\S+)\n(.*?)\n  END \1", txt, flags=re.S):
        p, body = m.groups()
        lay = re.search(r"LAYER (\w+)", body).group(1)
        rects = [tuple(float(v) for v in r) for r in re.findall(r"RECT\s+([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)", body)]
        if p in ("VDD", "VSS"):
            stripes[p] = (re.search(r"USE (\w+)", body).group(1), lay, rects)
            continue
        d = re.search(r"DIRECTION (\w+)", body).group(1)
        use = re.search(r"USE (\w+)", body).group(1)
        x0, y0, x1, y1 = rects[0]
        if lay == "M6":
            off, pit = TRACK["M4"]
            yc = off + round(((y0 + y1) / 2 - off) / pit) * pit
            x0, x1 = (0.0, 0.192) if x0 < W / 2 else (W - 0.192, W)
            lay, (y0, y1) = "M4", (round(yc - 0.012, 3), round(yc + 0.012, 3))
        pl.append((p, d, use, lay, (x0, y0, x1, y1)))
    seen = {}
    for p, _d, _u, lay, r in pl:
        k = (lay, r)
        if k in seen:
            raise SystemExit(f"{name}: {p} and {seen[k]} share one {lay} track after the re-layer")
        seen[k] = p
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {name}", "  CLASS BLOCK ;",
         "  ORIGIN 0 0 ;", f"  FOREIGN {name} 0 0 ;", f"  SIZE {W} BY {H} ;", "  SYMMETRY X Y ;"]
    for p, d, use, lay, r in pl:
        L += [f"  PIN {p}", f"    DIRECTION {d} ;", f"    USE {use} ;", "    PORT", f"      LAYER {lay} ;",
              "        RECT %.3f %.3f %.3f %.3f ;" % r, "    END", f"  END {p}"]
    xs = []
    for net, (use, lay, rects) in stripes.items():
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", f"      LAYER {lay} ;"]
        L += ["        RECT %.3f %.3f %.3f %.3f ;" % r for r in rects] + ["    END", f"  END {net}"]
        xs += [(r[0], r[2]) for r in rects]
    E = 0.5
    dep = min(float(os.environ.get("OT_ABS_PIN_WINDOW_UM", "10.8")), 0.25 * min(W, H))
    win = APW.windows(W, H, [(p, lay, r) for p, _d, _u, lay, r in pl], dep, 3, 5)
    L += ["  OBS"]
    for k in range(1, 5):
        L += [f"    LAYER M{k} ;"] + ["      RECT %.3f %.3f %.3f %.3f ;" % q
                                     for q in APW.minus_rect((E, E, W - E, H - E), win.get(k, []))]
    L += ["    LAYER M5 ;"]
    edges = [E] + [v for a, b in sorted(xs) for v in (a, b)] + [W - E]
    for a, b in zip(edges[::2], edges[1::2]):
        if b - a > 0.05:
            for q in APW.minus_rect((a, E + 0.4, b, H - E - 0.4), win.get(5, [])):
                L.append("      RECT %.3f %.3f %.3f %.3f ;" % q)
    L += ["  END", f"END {name}", "END LIBRARY"]
    d = Path(out) / name
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.lef").write_text("\n".join(L) + "\n")
    for f in list(view.glob(f"{name}_*.lib")) + [view / "insertion.json"]:
        (d / f.name).write_bytes(f.read_bytes())
    (d / "STANDIN_NOT_A_VIEW").write_text(f"diagnostic M5 re-layer of {view} (M6 pins -> M4, generated OBS); never bind\n")
    (d / "PROVISIONAL_NOT_A_VIEW").write_text("standin\n")
    print(name, len(pl), "pins", sum(1 for x in pl if x[3] == "M4"), "on M4", W, "x", H, "->", d)


def main():
    if "--from-view" in sys.argv:
        i = sys.argv.index("--from-view")
        return from_view(sys.argv[i + 1], [a for a in sys.argv[1:] if a not in ("--from-view", sys.argv[i + 1])][0])
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--ins", required=True, help="TT,FF,SS ASSUMED clock insertion (ps) to the child's pin flops")
    ap.add_argument("--master", help="module name (default spec top)")
    a = ap.parse_args()
    s = json.loads(Path(a.spec).read_text())
    name = a.master or s["top"]
    tt, ff, ss = (float(v) for v in a.ins.split(","))
    R = {"tt": tt, "ff": ff, "ss": ss}
    ports = header_ports(s["sources"], name, set(s.get("defines", [])))
    placed = {n for v in s["pins"].values() for n in v}
    missing = sorted(set(ports) - placed)
    if missing:
        raise SystemExit(f"{name}: ports with no face in the spec: {missing}")
    W, H = s["outline"]["w"], s["outline"]["h"]
    pl = pins_of(s, ports)
    d = Path(a.out) / name
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.lef").write_text(lef(name, W, H, pl, s["clock_port"]))
    for c in ("tt", "ff", "ss"):
        (d / f"{name}_{c}.lib").write_text(lib(name, W, H, pl, c, R, s["clock_port"]))
    ins = {"schema": "opentallas.closure_loop.ck_insertion.v1", "standin": True, "clock": s["clock_port"], "assumed_ps": R}
    for c in ("tt", "ff", "ss"):
        ins[c] = {"boundary": {"n": len(pl), "mean": R[c], "min": R[c] - 10, "max": R[c] + 10},
                  "all": {"n": len(pl), "mean": R[c], "min": R[c] - 10, "max": R[c] + 10}, "errors": []}
    (d / "insertion.json").write_text(json.dumps(ins, indent=1) + "\n")
    (d / f"{name}_bb.v").write_text("// DIAGNOSTIC stand-in blackbox (tools/qwen_dv/slice_standin.py); never bind\n" + bb(name, ports))
    (d / "STANDIN_NOT_A_VIEW").write_text(f"diagnostic stand-in from {a.spec} (pins / outline), assumed insertion {R}; never bind\n")
    (d / "PROVISIONAL_NOT_A_VIEW").write_text("standin\n")
    print(name, len(pl), "pins", W, "x", H, "->", d)


if __name__ == "__main__":
    main()
