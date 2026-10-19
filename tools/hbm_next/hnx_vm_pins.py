#!/usr/bin/env python3
"""HBM-NEXT-UNITS-VM 2026-10-19: exact pin plan of the hnx 2^19-word VM bank kit (hnx_vms_bank, top hnx_vms_bank_q0_faces).

Derived from the d4g kit vm_native_q0_faces_g313c pin file (physical/ref_tile_specs/smh/vm_q0_faces_g313_pins.tcl, read from
git origin/main):
  N / S (M5): the d4g data slots in order, every widened bus gets its new top bit right after its old top bit, later pins
              shift by one d4g slot; the face end gets 2 (N) / 3 (S) new slots on the d4g pitch; clk / clk_n / clk_s keep their
              d4g coordinates.
  W / E (M4): the tile is 90.72 um taller (4th macro), so the W / E data pins are re-spread at 7 M4 tracks (0.336 um) from
              5.436 um (d4g: ~5.5 tracks over 302 um), in d4g order with the new top bits inserted; clk_w / clk_e at the
              centre of the data span; clk_macro0..3 at each SRAM clk pin y (macro origin + 0.78, as d4g).
Writes physical/hbm_next/vm/hnx_vms_bank_pins.tcl and prints pin_ranges JSON for the spec.
usage: hnx_vm_pins.py D4G_PINS_TCL OUT_TCL OUT_RANGES_JSON
"""
import json, re, sys
from collections import OrderedDict

GROW = {"rq0": 17, "rq1": 17, "rq2": 17, "rq3": 17, "rq4": 17, "wq0": 281, "wq1": 281, "dq": 281, "kq": 281,
        "xq": 276, "xq2": 276, "eg": 276, "pq": 285}          # new top bit index per widened port
CLOCKS = {"clk", "clk_n", "clk_s", "clk_e", "clk_w", "clk_macro0", "clk_macro1", "clk_macro2"}
TRK, PH = 0.048, 0.012
MACRO_Y = [30.672, 121.296, 211.92, 302.544]                # u_a (A0), u_b (B), u_c (C), u_a1 (A1)
CLK_OFF = 0.78

def on_track(x):
    k = (x - PH) / TRK
    return abs(k - round(k)) < 1e-6

def main(src, out_tcl, out_rng):
    ents = [m.groups() for m in re.finditer(r"^ \{(\S+) ([NSEW]) (M\d) ([0-9.]+)\}", open(src).read(), re.M)]
    plan = []                                               # (name, face, layer, pos)
    for face in "NSWE":
        fe = sorted([(float(p), n, l) for n, f, l, p in ents if f == face])
        data = [(p, n, l) for p, n, l in fe if n not in CLOCKS]
        clks = [(p, n, l) for p, n, l in fe if n in CLOCKS]
        names = []
        for p, n, l in data:
            names.append(n)
            m = re.match(r"(\w+)\[(\d+)\]$", n)
            if m and m.group(1) in GROW and int(m.group(2)) == GROW[m.group(1)] - 1:
                names.append(f"{m.group(1)}[{GROW[m.group(1)]}]")
        layer = data[0][2]
        if face in "NS":
            slots = [p for p, _, _ in data]
            pitch = slots[-1] - slots[-2]
            while len(slots) < len(names):
                slots.append(round(slots[-1] + pitch, 3))
            for p, n, l in clks:
                plan.append((n, face, l, p))
        else:
            ck = [round(m + CLK_OFF, 3) for m in MACRO_Y] if face == "W" else []
            pos, slots = 5.436, []
            while len(slots) < len(names):
                if all(abs(pos - c) > 3 * TRK - 1e-9 for c in ck + [192.012]):
                    slots.append(round(pos, 3))
                pos += 7 * TRK
            plan.append((f"clk_{face.lower()}", face, layer, 192.012))
            for i, c in enumerate(ck):
                plan.append((f"clk_macro{i}", face, layer, c))
        for n, p in zip(names, slots):
            plan.append((n, face, layer, p))
    # checks: tracks, spacing >= 2 tracks per face/layer, unique names
    assert len({n for n, *_ in plan}) == len(plan)
    for n, f, l, p in plan:
        assert on_track(p), (n, p)
    for face in "NSWE":
        ps = sorted(p for _, f, _, p in plan if f == face)
        gaps = [b - a for a, b in zip(ps, ps[1:])]
        assert min(gaps) >= 2 * TRK - 1e-9, (face, min(gaps))
        print(f"face {face}: {len(ps)} pins {ps[0]:.3f}..{ps[-1]:.3f} um, min gap {min(gaps):.3f}, {len(ps)/(ps[-1]-ps[0]):.2f}/um")
    with open(out_tcl, "w") as o:
        o.write("# HBM-NEXT-UNITS-VM 2026-10-19 (tools/hbm_next/hnx_vm_pins.py): hnx_vms_bank exact pins, derived from the d4g\n"
                "# vm_q0_faces_g313 plan (phase .012): N/S d4g slots + inserted widened-bus bits; W/E re-spread at 7 M4 tracks on the\n"
                "# 403.92 um face; 5 CTS roots + 4 direct SRAM clock entries (W face at each SRAM clk pin y).\n"
                "source /src/physical/common_flow/assigned_pin_exact.tcl\nset vm_expected {\n")
        for n, f, l, p in plan:
            o.write(f" {{{n} {f} {l} {p:.3f}}}\n")
        o.write("}\nforeach vm_item $vm_expected {lassign $vm_item vm_p vm_f vm_l vm_x;ot_assigned_pin_exact $vm_p $vm_l $vm_f $vm_x}\n")
    rng = OrderedDict()
    for n, f, l, p in plan:
        b = n.split("[")[0]
        lo, hi = rng.get(b, (1e9, -1e9))
        rng[b] = (min(lo, p - 0.048), max(hi, p + 0.048))
    json.dump({k: [round(v[0], 3), round(v[1], 3)] for k, v in rng.items()}, open(out_rng, "w"), indent=1)
    print(f"{len(plan)} pins -> {out_tcl}")

if __name__ == "__main__":
    main(*sys.argv[1:4])
