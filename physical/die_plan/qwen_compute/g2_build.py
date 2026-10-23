#!/usr/bin/env python3
"""PLAN-QC G2 virtual-die probe inputs: partitions as blackboxes with their exact plan pins.

    python3 g2_build.py die_plan.json OUTDIR --tools TOOLS_DIE_PLAN_DIR

Writes OUTDIR/parts.lef (one CLASS BLOCK macro per partition type: every bus bit at its plan pin, OBS M1-M7 over the
outline = partition-owned layers, M9 clock and reset tap pins), OUTDIR/die.def (FIXED partitions, one net per port
bit, plus the clock spine net from the clock source tap to every partition tap and the async reset net from the reset
source to every synchronizer tap) and OUTDIR/g2.tcl (read-only global route, M2-M9 signal, congestion report).
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

plan_p, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, sys.argv[sys.argv.index("--tools") + 1])
import schema as S  # noqa: E402

raw = json.loads(plan_p.read_text())
P = S.Plan(raw)
out.mkdir(parents=True, exist_ok=True)
U = 1000
HW = {"M4": 0.012, "M5": 0.012, "M6": 0.016, "M7": 0.016, "M8": 0.02, "M9": 0.02}
DEPTH = 0.3

# type pin tables from the ports (type frame), consistent across instances (G0 checked)
tpins = defaultdict(dict)        # type -> {pin name: (layer, rect)}
nets = []
for pid, pr in P.ports.items():
    pins = P.port_pins(pid)
    ends = []
    for side in ("src", "dst"):
        e = pr[side]
        if e["part"] == S.DIE_PART:
            continue
        df = pr["face"] if side == "src" else S.OPP[pr["face"]]
        ends.append((e["part"], e["bus"], df, "OUTPUT" if side == "src" else "INPUT"))
    nn = []
    for bit, ln, c in pins:
        conn = []
        for part, bus, df, dr in ends:
            tn = P.parts[part]["type"]
            w, h = P.ptype(part)["outline_um"]
            x0d, y0d, x1d, y1d = P.rect(part)
            dpt = {"E": (x1d, c), "W": (x0d, c), "N": (c, y1d), "S": (c, y0d)}[df]
            tx, ty = P.to_type(part, dpt)
            tf = P.type_face(part, df)
            hw = HW[ln]
            if tf in "EW":
                x0, x1 = (w - DEPTH, w) if tf == "E" else (0.0, DEPTH)
                r = (x0, ty - hw, x1, ty + hw)
            else:
                y0, y1 = (h - DEPTH, h) if tf == "N" else (0.0, DEPTH)
                r = (tx - hw, y0, tx + hw, y1)
            name = f"{bus}[{bit}]" if pr["width"] > 1 else bus
            tpins[tn][name] = (ln, r, dr)
            conn.append((part, name))
        nets.append((f"{pid}_{bit}", conn))

# taps
for tn, t in P.types.items():
    x, y = t["clock"]["tap_um"]
    tpins[tn]["ck_tap"] = ("M9", (x - 0.2, y - 0.2, x + 0.2, y + 0.2), "INPUT")
    rx, ry = t["reset"].get("tap_um", [x, y])
    tpins[tn]["rst_tap"] = ("M9", (rx + 0.6, ry - 0.2, rx + 1.0, ry + 0.2), "INPUT")
ck_src, rst_src = raw["clock"]["source"]["part"], raw["reset"]["source"]["part"]
for src, nm in ((ck_src, "ck_root"), (rst_src, "rst_root")):
    tn = P.parts[src]["type"]
    x, y = P.types[tn]["clock"]["tap_um"]
    dx = 2.0 if nm == "ck_root" else 3.0
    tpins[tn][nm] = ("M9", (x + dx, y - 0.2, x + dx + 0.4, y + 0.2), "OUTPUT")
nets.append(("clk_spine", [(ck_src, "ck_root")] + [(n, "ck_tap") for n in P.parts]))
nets.append(("rst_async", [(rst_src, "rst_root")] + [(n, "rst_tap") for n in P.parts]))


def f(v):
    return f"{v:.3f}"


L = ["VERSION 5.8 ;", "BUSBITCHARS \"[]\" ;", "DIVIDERCHAR \"/\" ;"]
for tn, t in P.types.items():
    w, h = t["outline_um"]
    L += [f"MACRO P_{tn}", "  CLASS BLOCK ;", "  ORIGIN 0 0 ;", f"  SIZE {f(w)} BY {f(h)} ;", "  SYMMETRY X Y ;"]
    for pn, (ln, r, d) in sorted(tpins[tn].items()):
        L += [f"  PIN {pn}", f"    DIRECTION {d} ;", "    USE SIGNAL ;", "    PORT", f"      LAYER {ln} ;",
              f"        RECT {f(r[0])} {f(r[1])} {f(r[2])} {f(r[3])} ;", "    END", f"  END {pn}"]
    L += ["  OBS"] + [f"    LAYER M{k} ;\n      RECT 0 0 {f(w)} {f(h)} ;" for k in range(1, 8)] + ["  END",
                                                                                          f"END P_{tn}"]
L.append("END LIBRARY")
(out / "parts.lef").write_text("\n".join(L) + "\n")

D = ["VERSION 5.8 ;", "DIVIDERCHAR \"/\" ;", "BUSBITCHARS \"[]\" ;", "DESIGN qc_g2 ;", f"UNITS DISTANCE MICRONS {U} ;",
     f"DIEAREA ( 0 0 ) ( {round(P.W * U)} {round(P.H * U)} ) ;", f"COMPONENTS {len(P.parts)} ;"]
for n, p in P.parts.items():
    x, y = p["origin_um"]
    o = {"R0": "N", "MX": "FS", "MY": "FN", "R180": "S"}[p.get("orient", "R0")]
    D.append(f"- {n} P_{p['type']} + FIXED ( {round(x * U)} {round(y * U)} ) {o} ;")
D += ["END COMPONENTS", f"NETS {len(nets)} ;"]
for nm, conn in nets:
    D.append(f"- {nm} " + " ".join(f"( {i} {pn} )" for i, pn in conn) + " + USE SIGNAL ;")
D += ["END NETS", "END DESIGN"]
(out / "die.def").write_text("\n".join(D) + "\n")
print(f"types {len(P.types)} parts {len(P.parts)} nets {len(nets)}")
