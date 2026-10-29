#!/usr/bin/env python3
"""DIE-HBM-20-EPB: rewrite a copied hfd_ep_static kit (ep_my, synth reused) into the WIDER-SLOT 2x2-SRAM probe shape.
usage: mk_epb.py KITDIR SHAPE   (SHAPE in SHAPES below). Same RTL/netlist; only outline, macro xy/orient, plan pins,
in-core island (clock entry + 4 tree leaves) positions change. Probe only (not a generated kit)."""
import json, re, sys
from pathlib import Path

G = 4.32
SW, SH = 171.288, 77.784
# shape: die w,h ; SRAM column x (A left, B right) ; row y (r0 bottom, r1 top) ; island centres
# macro x on the 0.054 site grid, y on the M4 pin track grid (y = 0.012 mod 0.048, as gen_core_kit_hbm snap)
SHAPES = {
 # B1: logic band S (y 4.32..121), SRAM 2x2 above, heavy (W: rd_out+wd 266+ctl) sides face the 42.2-um mid channel.
 "B1": dict(w=432.0, h=319.68, xa=21.6, xb=235.062, y0=125.292, y1=216.012,
            isl={0: (216.0, 108.0), 1: (108.0, 60.48), 2: (216.0, 164.16), 3: (324.0, 60.48), 4: (216.0, 254.88)}),
 # B2: narrower mid channel (25.9 um usable), 4.32 less S band; 414.72 x 302.4
 "B2": dict(w=414.72, h=302.4, xa=21.6, xb=222.102, y0=112.332, y1=203.052,
            isl={0: (211.68, 99.36), 1: (90.72, 56.16), 2: (211.68, 151.2), 3: (315.36, 56.16), 4: (211.68, 241.92)}),  # off the B2 tap columns (2_3 tapcell odb)
  # B3 (informed by B1 AUTO-GEOM: GRT 0 but fill/empty/partial_face/clock_reach FAIL): macro share >= 50 % (444.96 x
  # 237.6, S band 43 um), mid channel 50.5 um, outer channels 21.6 um, W/E pins at 0.288 (3.5/um < 4/um partial-face
  # density), N status pins centred over the mid channel, clock leaves in the outer channels + mid channel.
 "B3": dict(w=444.96, h=237.6, xa=25.92, xb=247.752, y0=47.532, y1=138.276 - 0.024, wep=0.288, nx0=166.104, npitch=8.64,
            isl={0: (216.0, 25.92), 1: (12.96, 108.0), 2: (216.0, 129.6), 3: (432.0, 108.0), 4: (216.0, 194.4)}),  # off the B3 tap columns (2_3 tapcell odb)
  # B4 (informed by B3: GRT 0, only channel_h 1.74 est. FAIL in the 12.96-um row gap at the B column = the B-row1
  # light-side wd_in 246 crossing from the mid channel): row gap 21.6, outer channels 12.96 (macro share kept >= 50 %).
 "B4": dict(w=427.68, h=246.24, xa=17.28, xb=239.112, y0=47.532, y1=146.892, wep=0.288, nx0=161.784, npitch=8.64,
            isl={0: (220.32, 25.92), 1: (8.64, 108.0), 2: (220.32, 129.6), 3: (419.04, 108.0), 4: (220.32, 194.4)}),  # off the B4 tap columns
}
OLD_ISL = {0: (120.96, 198.72), 1: (25.92, 99.36), 2: (25.92, 298.08), 3: (216.0, 99.36), 4: (216.0, 298.08)}
# row0 = mem[0] of both blocks, row1 = mem[1]: the two banks of one bit slice face each other across the mid channel
MACROS = [("u_fcore.u_rxb.g_block\\[0\\].u_block.g_mem\\[0\\].u_mem.u_sram", "A", 0),
          ("u_fcore.u_rxb.g_block\\[1\\].u_block.g_mem\\[0\\].u_mem.u_sram", "B", 0),
          ("u_fcore.u_rxb.g_block\\[0\\].u_block.g_mem\\[1\\].u_mem.u_sram", "A", 1),
          ("u_fcore.u_rxb.g_block\\[1\\].u_block.g_mem\\[1\\].u_mem.u_sram", "B", 1)]


def r3(v):
    return round(v + 1e-9, 4)


def new_pins(S, old):
    """old pins.json list -> new list (same names/bits/layers per face rule)."""
    w, h = S["w"], S["h"]
    by = {}
    for p in old:
        by.setdefault(p["bus"], []).append(p)
    out = []
    def put(bus, bit, layer, x, y, face):
        out.append(dict(bus=bus, bit=bit, layer=layer, x=r3(x), y=r3(y), face=face))
    # N: status (13 bits), same 17.28 pitch as the plan
    k = 0
    for bus in ("rx_block_ready", "fault_cause"):
        for p in sorted(by[bus], key=lambda q: q["bit"]):
            put(bus, p["bit"], "M5", S.get("nx0", 17.304) + S.get("npitch", 17.28) * k, h, "N"); k += 1
    # S: control (old S face, 8.64 pitch from x 12.984), then sd_tx and sd_rx at 0.288 pitch (M5)
    ctl = [p for p in old if p["face"] == "S"]
    ctl.sort(key=lambda q: q["x"])
    for i, p in enumerate(ctl):
        put(p["bus"], p["bit"], "M5", 4.584 + 0.864 * i, 0.0, "S")
    x_tx = 4.584 + 0.864 * len(ctl) + 4.32
    for p in sorted(by["sd_tx"], key=lambda q: q["bit"]):
        put("sd_tx", p["bit"], "M5", x_tx + 0.288 * p["bit"], 0.0, "S")
    x_rx = w / 2 + 12.96 + 0.024   # on the M5 track grid (0.024 + 0.048 k)
    for p in sorted(by["sd_rx"], key=lambda q: q["bit"]):
        put("sd_rx", p["bit"], "M5", x_rx + 0.288 * p["bit"], 0.0, "S")
    # W: tx_frame, E: rx_pin_flit, 0.192 pitch M4 in the S band
    for p in sorted(by["tx_frame"], key=lambda q: q["bit"]):
        put("tx_frame", p["bit"], "M4", 0.0, 4.584 + S.get("wep", 0.192) * p["bit"], "W")
    for p in sorted(by["rx_pin_flit"], key=lambda q: q["bit"]):
        put("rx_pin_flit", p["bit"], "M4", w, 4.584 + S.get("wep", 0.192) * p["bit"], "E")
    clk = by["clk"][0]
    put("clk", clk["bit"], clk["layer"], S["isl"][0][0] + 0.024, S["isl"][0][1], clk.get("face", "IN"))
    assert len(out) == len(old), (len(out), len(old))
    assert max(q["x"] for q in out if q["face"] == "S") < w - 4.32
    return out


def name(p, buses_w):
    return p["bus"] if buses_w[p["bus"]] == 1 and p["bus"] in ("clk", "fault", "phy_up", "rst_n", "rx_arm_bank", "rx_arm_v", "rx_pin_v", "rx_release_bank", "rx_release_v", "rx_slot_bank", "rx_slot_v", "tx_v") else f"{p['bus']}[{p['bit']}]"


def main():
    K = Path(sys.argv[1]); S = SHAPES[sys.argv[2]]
    w, h = S["w"], S["h"]
    old = json.loads((K / "pins.json").read_text())
    pins = new_pins(S, old)
    widths = {}
    for p in old:
        widths[p["bus"]] = widths.get(p["bus"], 0) + 1
    (K / "pins.json").write_text(json.dumps(pins))
    # io.tcl: centre moved PIN_LEN/2 inward (gen_phys form), size as the original per layer/face
    L = ["# DIE-HBM-20-EPB probe: wider-slot pins (mk_epb.py %s), core frame um." % sys.argv[2]]
    pp = []
    for p in pins:
        nm = name(p, widths)
        x, y, f = p["x"], p["y"], p["face"]
        if nm == "clk":
            L.append("place_pin -pin_name {clk} -layer M5 -location {%.4f %.4f} -pin_size {0.048 0.48}" % (x, y))
            pp.append(dict(name=nm, layer="M5", x=x, y=y)); continue
        if f == "N": y -= 0.096; sz = "0.0240 0.1920"
        elif f == "S": y += 0.096; sz = "0.0240 0.1920"
        elif f == "W": x += 0.096; sz = "0.1920 0.0240"
        else: x -= 0.096; sz = "0.1920 0.0240"
        L.append("place_pin -pin_name {%s} -layer %s -location {%.4f %.4f} -pin_size {%s}" % (nm, p["layer"], x, y, sz))
        pp.append(dict(name=nm, layer=p["layer"], x=r3(x), y=r3(y)))
    (K / "io.tcl").write_text("\n".join(L) + "\n")
    d = json.loads((K / "plan_pins.json").read_text()); d["pins"] = pp; d["source"] = "DIE-HBM-20-EPB mk_epb.py " + sys.argv[2]
    (K / "plan_pins.json").write_text(json.dumps(d, indent=1))
    # config.mk
    c = (K / "config.mk").read_text()
    c = re.sub(r"export DIE_AREA = .*", "export DIE_AREA = 0 0 %.2f %.2f" % (w, h), c)
    c = re.sub(r"export CORE_AREA = .*", "export CORE_AREA = %.2f %.2f %.2f %.2f" % (G, G, w - G, h - G), c)
    (K / "config.mk").write_text(c)
    # macros: A = MY (heavy W pin edge -> E, mid channel), B = R0 (heavy W edge faces the mid channel)
    L = ["foreach {inst master x y orient} {"]
    for inst, col, row in MACROS:
        L.append("  {%s} ot_sram_1r1w_64x512_m1_r2c2 %.3f %.3f %s" % (inst, S["xa"] if col == "A" else S["xb"], S["y0"] if row == 0 else S["y1"], "MY" if col == "A" else "R0"))
    L += ["} {", "  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact", "}"]
    (K / "macro_placement.tcl").write_text("\n".join(L) + "\n")
    # islands: translate each island's cells/ports/rect by its own offset
    def mv(x, y):
        best = min(OLD_ISL, key=lambda i: abs(OLD_ISL[i][0] - x) + abs(OLD_ISL[i][1] - y))
        ox, oy = OLD_ISL[best]; nx, ny = S["isl"][best]
        return x - ox + nx, y - oy + ny
    t = (K / "master_core_infra.tcl").read_text().splitlines()
    o = []
    for ln in t:
        m = re.match(r"(ot_ci_(?:port|cell|clock_entry) \{?[\w\[\]]+\}? (?:\w+ )?)([\d.]+) ([\d.]+)(.*)", ln)
        if m:
            x, y = mv(float(m.group(2)), float(m.group(3)))
            rest = m.group(4)
            rm = re.search(r"\{([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)\}", rest)
            if rm:
                a, b = mv(float(rm.group(1)) + 4.32, float(rm.group(2)) + 4.32)
                rest = rest.replace(rm.group(0), "{%g %g %g %g}" % (r3(a - 4.32), r3(b - 4.32), r3(a + 4.32), r3(b + 4.32)))
            ln = "%s%g %g%s" % (m.group(1), r3(x), r3(y), rest)
        o.append(ln)
    (K / "master_core_infra.tcl").write_text("\n".join(o) + "\n")
    ci = json.loads((K / "core_infra_plan.json").read_text())
    ci["outline_um"] = [w, h]
    for cc in ci["cells"]:
        cc["xy_um"] = list(map(r3, mv(*cc["xy_um"])))
        a, b = mv(cc["rect_um"][0] + 4.32, cc["rect_um"][1] + 4.32); cc["rect_um"] = [r3(a - 4.32), r3(b - 4.32), r3(a + 4.32), r3(b + 4.32)]
    for pt in ci["ports"]:
        pt["xy_um"] = list(map(r3, mv(*pt["xy_um"])))
    ci["clock_entry"]["xy_um"] = [r3(S["isl"][0][0] + 0.024), S["isl"][0][1]]
    (K / "core_infra_plan.json").write_text(json.dumps(ci))
    ms = json.loads((K / "master_slice.json").read_text())
    ms["outline_um"] = [w, h]
    for isl in ms["islands"] + ms["keepouts"]:
        cx, cy = (isl["rect_um"][0] + isl["rect_um"][2]) / 2, (isl["rect_um"][1] + isl["rect_um"][3]) / 2
        nx, ny = mv(cx, cy)
        isl["rect_um"] = [r3(nx - 4.32), r3(ny - 4.32), r3(nx + 4.32), r3(ny + 4.32)]
        if "centre_um" in isl: isl["centre_um"] = [r3(nx), r3(ny)]
        if isl.get("clock_pin"): isl["clock_pin"]["xy_um"] = [r3(nx), r3(ny)]
    (K / "master_slice.json").write_text(json.dumps(ms, indent=1))
    print("EPB", sys.argv[2], "die", w, h, "area", round(w * h), "pins", len(pins))


if __name__ == "__main__":
    main()
