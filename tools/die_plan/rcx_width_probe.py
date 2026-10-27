#!/usr/bin/env python3
"""CLOCK-128-R6: two-width OpenRCX probe on straight M8/M9 wires (ASAP7 1x tech LEF only, no cells).

Cases (each an isolated 100-um straight wire, 20 um from any other case, BTerms at both ends on the wire layer):
  <L>_w04       default width 0.04, no neighbours            (inside the rules' only width entry)
  <L>_w16       0.16 (clock NDR 4W), no neighbours
  <L>_w04_sh    0.04 between two VSS stripes of 0.04 at 0.04 space (rules pattern geometry)
  <L>_w16_sh    0.16 between two VSS stripes of 0.16 at 0.08 space (the die clock shield geometry, die_clock_128.shield_geom)
  <L>_w32_sh    0.32 (8W) between 0.32 stripes at 0.08 space
for L in M8 (horizontal), M9 (vertical).  `gen DIR` writes probe.def + probe.tcl (+ run.sh); `report DIR` reads
rcx*.spef and prints per-um R and C per case (json).
"""
import json
import os
import re
import sys

DBU = 1000
LEN_UM = 100.0
CASES = [("w04", 0.04, None), ("w16", 0.16, None), ("w04_sh", 0.04, 0.04), ("w16_sh", 0.16, 0.08),
         ("w32_sh", 0.32, 0.08)]
LAYERS = ("M8", "M9")
# ASAP7 1x tech LEF default WIDTH / SPACING of M1-M7
DEFAULT_LOWER = [("M1", 0.018, 0.018), ("M2", 0.018, 0.018), ("M3", 0.018, 0.018), ("M4", 0.024, 0.024),
                 ("M5", 0.024, 0.024), ("M6", 0.032, 0.032), ("M7", 0.032, 0.032)]


def i(v):
    return int(round(v * DBU))


def gen(d, rules=("stock",)):
    os.makedirs(d, exist_ok=True)
    nets, pins, sw, ndr = [], [], [], {}
    k = 0
    for L in LAYERS:
        for name, w, sp in CASES:
            nm = f"{L}_{name}"
            c = 20.0 + 20.0 * k          # centre line (y for M8, x for M9)
            k += 1
            a0, a1 = 10.0, 10.0 + LEN_UM
            hw = w / 2
            rule = None
            if abs(w - 0.04) > 1e-9:
                rule = f"ndr_{int(round(w * 1000))}"
                ndr[rule] = w
            def pt(a, cc=c):
                return (a, cc) if L == "M8" else (cc, a)
            for tag, a in (("a", a0), ("b", a1)):
                x, y = pt(a)
                pins.append(f"- {nm}_{tag} + NET {nm} + DIRECTION INPUT + USE CLOCK\n"
                            f"  + LAYER {L} ( {-i(hw)} {-i(hw)} ) ( {i(hw)} {i(hw)} ) + FIXED ( {i(x)} {i(y)} ) N ;")
            (x0, y0), (x1, y1) = pt(a0), pt(a1)
            r = f" + NONDEFAULTRULE {rule}" if rule else ""
            nets.append(f"- {nm} ( PIN {nm}_a ) ( PIN {nm}_b ) + USE CLOCK{r}\n"
                        f"  + FIXED {L} ( {i(x0)} {i(y0)} ) ( {i(x1)} {i(y1)} ) ;")
            if sp is not None:
                off = w + sp
                for s in (-1, 1):
                    (u0, v0), (u1, v1) = pt(a0 - 1.0, c + s * off), pt(a1 + 1.0, c + s * off)
                    sw.append(f"  NEW {L} {i(w)} + SHAPE STRIPE ( {i(u0)} {i(v0)} ) ( {i(u1)} {i(v1)} )")
    die = i(20.0 + 20.0 * k + 20.0)
    # ODB rejects an NDR that omits a routing layer (ODB-0387): lower layers keep their LEF default width / spacing
    low = " ".join(f"+ LAYER {l} WIDTH {i(w0)} SPACING {i(s0)}" for l, w0, s0 in DEFAULT_LOWER)
    ndr_lines = [f"- {n} {low} + LAYER M8 WIDTH {i(w)} SPACING 80 + LAYER M9 WIDTH {i(w)} SPACING 80 ;"
                 for n, w in ndr.items()]
    sw[0] = sw[0].replace("  NEW ", "  + ROUTED ", 1)
    txt = "\n".join([
        "VERSION 5.8 ;", "DIVIDERCHAR \"/\" ;", "BUSBITCHARS \"[]\" ;", "DESIGN rcx_width_probe ;",
        f"UNITS DISTANCE MICRONS {DBU} ;", f"DIEAREA ( 0 0 ) ( {die} {die} ) ;",
        f"NONDEFAULTRULES {len(ndr_lines)} ;", *ndr_lines, "END NONDEFAULTRULES",
        f"PINS {len(pins)} ;", *pins, "END PINS",
        "SPECIALNETS 1 ;", "- VSS ( * VSS ) + USE GROUND", *sw, " ;", "END SPECIALNETS",
        f"NETS {len(nets)} ;", *nets, "END NETS", "END DESIGN", ""])
    open(os.path.join(d, "probe.def"), "w").write(txt)
    tcl = ["read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef",
           "read_def /out/probe.def",
           "set blk [ord::get_db_block]",
           "foreach n [$blk getNets] { set w [$n getWire]; if {$w == \"NULL\"} { continue }; "
           "set s [odb::dbShape]; for {set q 0} {$q < [$w length]} {incr q} { if {[catch {$w getShape $q $s}]} { continue }; "
           "puts \"OT_WIRE [$n getName] $q [$s getDX] [$s getDY]\" } }"]
    for r in rules:
        f = "/OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules" if r == "stock" else f"/out/{r}"
        tag = "stock" if r == "stock" else os.path.splitext(os.path.basename(r))[0]
        tcl += [f"extract_parasitics -ext_model_file {f}", f"write_spef /out/rcx_{tag}.spef"]
    open(os.path.join(d, "probe.tcl"), "w").write("\n".join(tcl) + "\n")


def spef_nets(path):
    """net -> (C_total fF, R_total ohm, cc fF) from an OpenRCX SPEF (PF/OHM units read from the header)."""
    t = open(path).read()
    cu = {"PF": 1e3, "FF": 1.0}[re.search(r"\*C_UNIT 1 (\w+)", t).group(1)]
    ru = {"OHM": 1.0, "KOHM": 1e3}[re.search(r"\*R_UNIT 1 (\w+)", t).group(1)]
    nm = {}
    for m in re.finditer(r"^\*(\d+) (\S+)$", t.split("*PORTS")[0], re.M):
        nm[m.group(1)] = m.group(2)
    out = {}
    for blk in t.split("*D_NET ")[1:]:
        head, body = blk.split("\n", 1)
        n, ctot = head.split()[0], float(head.split()[1]) * cu
        n = nm.get(n.lstrip("*"), n)
        cap = body.split("*CAP")[1].split("*RES")[0] if "*CAP" in body else ""
        cc = sum(float(l.split()[-1]) * cu for l in cap.strip().splitlines() if len(l.split()) == 4)
        res = body.split("*RES")[1].split("*END")[0] if "*RES" in body else ""
        r = sum(float(l.split()[-1]) * ru for l in res.strip().splitlines() if len(l.split()) == 4)
        out[n] = (ctot, r, cc)
    return out


def report(d):
    res = {}
    for f in sorted(os.listdir(d)):
        if f.startswith("rcx_") and f.endswith(".spef"):
            res[f[4:-5]] = {n: dict(c_ff_per_um=round(c / LEN_UM, 5), r_ohm_per_um=round(r / LEN_UM, 4),
                                    cc_ff_per_um=round(cc / LEN_UM, 5))
                            for n, (c, r, cc) in spef_nets(os.path.join(d, f)).items()}
    return res


if __name__ == "__main__":
    if sys.argv[1] == "gen":
        gen(sys.argv[2], tuple(sys.argv[3:]) or ("stock",))
    else:
        print(json.dumps(report(sys.argv[2]), indent=1, sort_keys=True))
