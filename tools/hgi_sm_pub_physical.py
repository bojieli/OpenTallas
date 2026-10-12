#!/usr/bin/env python3
"""Physical hierarchy of the HGI-1 SM result publication, HIER form (el1011-hbm-smh/pub, 2026-10-11).

rtl/hbm_accel/generic/peers/ot_hgi_sm_pub.sv: ot_hgi_sm_pub_hier (parent) over 8 hardened ot_hgi_sm_pub_slice (4 SMs
each).  The physical spec is in claude-takeover-20261007/el1011-hbm-smh.log ("[hbm-smh/pub] PHYSICAL SPEC").

  slice   259.2 x 302.4 um; 8 x 128x256 SRAM in 2 columns x 4 rows (col A R0 / col B MY: write pins face the middle
          channel, read pins the outer strips); N face = the 4 SM result ports, S face = command / VM packet / STREAM /
          done / fault; routes M2-M6 with power on M6 (the parent owns M7); own clock tree.
  parent  1,149.12 x 743.04 um; slices 2 rows x 4 columns (N row R0, S row MX), 103.68 um central channel; command /
          clients 0-1 / STREAM on the W face, clients 2-3 on the E face, SM ports straight onto the slice pins.

Reuses the ORFS work-directory writers of tools/hbm_accel_smh_physical.py (config.mk, SDC, abstract, run.sh).

    python3 tools/hgi_sm_pub_physical.py block --piece slice --out DIR --src SRC --label L ...
    python3 tools/hgi_sm_pub_physical.py block --piece parent --views VIEWDIR --out DIR --src SRC --label L ...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_accel_smh_physical as smh  # noqa: E402

SRAM = "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2"
SRAM32 = "physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1"   # smmv AD 32: arrival data, 2 a local SM (u_lo / u_hi)
SRC_RTL = ["rtl/lib/ot_rst_relay.sv", "rtl/hbm_accel/generic/peers/ot_hgi_sm_pub.sv",
           SRAM + "/ot_sram_1r1w_128x256_m1_r2c2_bb.v", SRAM32 + "/ot_sram_1r1w_32x128_m1_bb.v"]
NSS, NC, NSL, NCOL = 4, 8, 8, 4
# smmv 10-12 (AD 32 + sm_cr): the slice gains 8 x 32x128 arrival SRAMs (51.408 x 20.79).  Outline grown from 259.2 x
# 302.4 so macros + std cells stay <= 55 % (macros 39.7k + ~11k cells in 104.6k um2 = ~48 %): the 2 big columns keep their
# rows; a 4-wide band of arrival SRAMs under the N face (the SM result ports) + a 4-high centre column between the big
# columns, >= 21.38 um channels everywhere (centre column 22.68 / 21.38 to the big columns, band 21.6 above the top row).
SW, SH = 319.68, 327.24                    # slice outline
MW, MH = 94.824, 41.04                     # 128x256 SRAM
XA, YB, RP = 17.28, 34.56, 62.64           # col A x, first macro row y, macro row pitch (21.6 um channels)
XB = round(SW - XA - MW, 3)
SW32, SH32 = 51.408, 20.79                  # 32x128 SRAM
XC32 = 134.784                              # centre column x (channels 22.68 / 21.38 to columns A / B)
YBAND = round(YB + 3 * RP + MH + 21.6, 3)   # N band y (21.6 above the top big row)
XBAND0, XBP = 24.624, round(SW32 + 21.6, 3)  # band x0, band pitch (4 macros, 24.6 um to each side edge)
YC32 = [round(241.92 - i * 43.2, 3) for i in range(4)]   # centre column, top down (0.864 grid: pins on track;
#                                                        22.41 um channels, 22.41 to the band)
EDGE, GAP, CH = 17.28, 25.92, 103.68       # parent: edge margin, column gap, central channel
PW = round(2 * EDGE + NCOL * SW + (NCOL - 1) * GAP, 3)
PH = round(2 * EDGE + 2 * SH + CH, 3)
VSLICE = "ot_hgi_sm_pub_slice"


def sm_pin_names(s):
    return [f"sm_rv[{s}]"] + [f"sm_rrow[{s*12+i}]" for i in range(12)] + \
        [f"sm_rdata[{s*NC*32+i}]" for i in range(NC * 32)]


def slice_pins():
    """(name, layer, edge, x, y): N face = SM ports (M5, 0.192), S face = the rest (M5, 0.192), centred."""
    def row(names, y, pitch=0.192):
        x0 = round((SW - len(names) * pitch) / 2 / 0.048) * 0.048 + 0.012
        return [(n, "M5", None, round(x0 + i * pitch, 3), y) for i, n in enumerate(names)]
    north = [n for s in range(NSS) for n in sm_pin_names(s)]
    south = (["clk", "rst_n", "c_go", "c_sm", "c_bf"] + smh.bits("c_ob", 18) + smh.bits("c_ost", 18) + smh.bits("c_mm", 20)
             + smh.bits("c_qq", 13) + smh.bits("c_pp", 4) + smh.bits("sid", 3) + smh.bits("sm_en", NSS)
             + ["w_v"] + smh.bits("w_pkt", 279) + ["w_ack", "so_v"] + smh.bits("so_idx", 20) + smh.bits("so_data", 32)
             + ["so_cr", "s_done", "s_fault"])
    return row(north, SH), row(south, 0.0)


def slice_xy(k):
    """lower-left and orientation of slice k in the parent (N row R0, S row MX)."""
    col = k % NCOL
    x = round(EDGE + col * (SW + GAP), 3)
    return (x, round(PH - EDGE - SH, 3), "R0") if k < NCOL else (x, EDGE, "MX")


def parent_pins():
    north, south = slice_pins()
    pins = []
    for k in range(NSL):
        x0, _, _ = slice_xy(k)
        for n, layer, _, x, _ in north:
            base, idx = n[:-1].split("[")
            idx = int(idx)
            per = 1 if base == "sm_rv" else (12 if base == "sm_rrow" else NC * 32)
            pins.append((f"{base}[{k*NSS*per + idx}]", layer, None, round(x0 + x, 3), PH if k < NCOL else 0.0))
    # W / E faces: the channel band carries every connected pin (M4, 0.096); the unused vmr bits sit below it
    y_lo = EDGE + SH
    def band(names, x):
        y0 = round((y_lo + (CH - len(names) * 0.096) / 2) / 0.048) * 0.048 + 0.012
        return [(n, "M4", None, x, round(y0 + i * 0.096, 3)) for i, n in enumerate(names)]
    def low(names, x):
        y0 = 0.012 + 8.64
        return [(n, "M4", None, x, round(y0 + i * 0.192, 3)) for i, n in enumerate(names)]
    used = {273, 256}
    west = (["clk", "rst_n", "pub_v", "pub_rdy"] + smh.bits("pub_base", 40) + smh.bits("pub_stride", 32)
            + smh.bits("pub_space", 2) + smh.bits("pub_m", 20) + smh.bits("pub_q", 13) + smh.bits("pub_p", 4)
            + ["pub_bf16", "pub_done", "pub_fault", "s0_v"] + smh.bits("s0_idx", 20) + smh.bits("s0_data", 32))
    for c in (0, 1):
        west += [f"vmq[{c*338+i}]" for i in range(338)] + [f"vmr[{c*274+i}]" for i in sorted(used)]
    east = []
    for c in (2, 3):
        east += [f"vmq[{c*338+i}]" for i in range(338)] + [f"vmr[{c*274+i}]" for i in sorted(used)]
    pins += band(west, 0.0) + band(east, PW)
    pins += low([f"vmr[{c*274+i}]" for c in (0, 1) for i in range(274) if i not in used], 0.0)
    pins += low([f"vmr[{c*274+i}]" for c in (2, 3) for i in range(274) if i not in used], PW)
    return pins


def slice_macros_tcl():
    t = ["set ot_n 0", "foreach ot_inst [[ord::get_db_block] getInsts] {",
         "  if {![[$ot_inst getMaster] isBlock]} { continue }",
         "  set n [string map {\"\\\\\" \"\"} [$ot_inst getName]]",
         "  if {[regexp {g_af\\[(\\d+)\\]\\.u_(lo|hi)} $n -> a h]} {",
         "    set k [expr {2 * $a + ($h eq \"hi\" ? 1 : 0)}]",
         f"    if {{$k < 4}} {{ set x [expr {{{XBAND0} + $k * {XBP}}}]; set y {YBAND} }} \\",
         f"    else {{ set x {XC32}; set y [lindex {{{' '.join(str(v) for v in YC32)}}} [expr {{$k - 4}}]] }}",
         "    place_macro -macro_name [$ot_inst getName] -location [list $x $y] -orientation R0",
         "    incr ot_n; continue",
         "  }",
         "  if {![regexp {g_m\\[(\\d+)\\]\\.u_m} $n -> q]} { error \"no slot for $n\" }",
         f"  set y [expr {{{YB} + ($q % 4) * {RP}}}]",
         f"  if {{$q < 4}} {{ place_macro -macro_name [$ot_inst getName] -location [list {XA} $y] -orientation R0 }} \\",
         f"  else {{ place_macro -macro_name [$ot_inst getName] -location [list {XB} $y] -orientation MY }}",
         "  incr ot_n", "}", "puts \"ot macro_place: $ot_n SRAM macros\""]
    return "\n".join(t) + "\n"


def parent_macros_tcl():
    t = ["set ot_n 0", "foreach ot_inst [[ord::get_db_block] getInsts] {",
         "  if {![[$ot_inst getMaster] isBlock]} { continue }",
         "  set n [string map {\"\\\\\" \"\"} [$ot_inst getName]]",
         "  if {![regexp {g_s\\[(\\d+)\\]\\.u$} $n -> k]} { error \"no slot for $n\" }"]
    for k in range(NSL):
        x, y, o = slice_xy(k)
        t.append(f"  if {{$k == {k}}} {{ place_macro -macro_name [$ot_inst getName] -location [list {x} {y}] -orientation {o} }}")
    t += ["  incr ot_n", "}", "puts \"ot macro_place: $ot_n slices\""]
    return "\n".join(t) + "\n"


def cmd_block(a):
    a.hold_margin = smh.loop_hold_margin(a.hold_margin)
    work = Path(a.out)
    work.mkdir(parents=True, exist_ok=True)
    smh.RTL = SRC_RTL
    extra = {"PLACE_DENSITY": a.pd, "MIN_ROUTING_LAYER": "M2", "HOLD_SLACK_MARGIN": a.hold_margin}
    if a.grt_allow:
        extra["GLOBAL_ROUTE_ARGS"] = "-congestion_report_iter_step 5 -verbose -allow_congestion -congestion_iterations 60"
    if a.hold_buffer_pct:
        (work / "rt_hook.tcl").write_text(
            "if {[info commands ::ot_rth_orig] eq \"\"} { rename ::repair_timing_helper ::ot_rth_orig }\n"
            f"proc ::repair_timing_helper {{args}} {{ ::ot_rth_orig {{*}}$args -max_buffer_percent {a.hold_buffer_pct} }}\n")
        extra["PRE_CTS_TCL"] = "/work/rt_hook.tcl"
        extra["PRE_GLOBAL_ROUTE_TCL"] = "/work/rt_hook.tcl"
    if a.piece == "slice":
        name, die = VSLICE, (SW, SH)
        north, south = slice_pins()
        pins = north + south
        macros = [SRAM, SRAM32]
        extra.update({"MAX_ROUTING_LAYER": "M6", "PDN_TCL": "/src/tools/chip_assembly/tcl/pdn_hgi_pub_child.tcl",
                      "MACRO_PLACE_HALO": "3 3", "GDS_ALLOW_EMPTY": "(ot_sram.*)"})
        (work / "macros.tcl").write_text(slice_macros_tcl())
        sdc = smh.sdc_block(a.lat, nbr_in="c_* sm_rv* sm_rrow* sm_rdata* w_ack so_cr", static_inputs=("sid*", "sm_en*"),
                            lat_ff=a.lat_ff, period=a.period, skew=a.skew, die_skew=a.die_skew)
    else:
        if not a.views:
            raise ValueError("--piece parent needs --views (the slice view dir, named after the master)")
        if Path(a.views).name != VSLICE:
            raise ValueError(f"--views must be a directory named {VSLICE}")
        name, die = "ot_hgi_sm_pub_hier", (PW, PH)
        pins = parent_pins()
        macros = [a.views]
        extra.update({"MAX_ROUTING_LAYER": "M7", "PDN_TCL": "/src/tools/chip_assembly/tcl/pdn_hgi_pub_hier.tcl",
                      "MACRO_PLACE_HALO": "0.5 0.5", "GDS_ALLOW_EMPTY": "(ot_sram.*|ot_hgi_sm_pub_slice.*)"})
        (work / "macros.tcl").write_text(parent_macros_tcl())
        sdc = smh.sdc_block(a.lat, nbr_in="pub_* sm_* vmr*", lat_ff=a.lat_ff, period=a.period, skew=a.die_skew,
                            die_skew=a.die_skew)
    (work / "pins.tcl").write_text(smh.pin_tcl([(n, l, e, x, y) for n, l, e, x, y in pins]))
    (work / "hops.tcl").write_text(smh.PIN_TCL.replace("ot_pin_place_auto {.*} 16\n", f"ot_pin_place_auto {{.*}} {a.pin_depth}\n"))
    extra["POST_TAPCELL_TCL"] = "/work/hops.tcl"
    (work / "constraint.sdc").write_text(sdc)
    nick = f"hgipub_{a.piece}_{a.label}"
    (work / "config.mk").write_text(smh.config_mk(name, nick, die, macros, extra))
    smh.write_abstract(work, name, macros, name, tt=True)
    mx = " ".join(f"{k}={v}" for k, v in (x.split("=", 1) for x in (a.make_var or [])))
    smh.run_sh(work, a.label, a.src, a.need, a.cores, macros, target=a.stop_after or "finish", admit=not a.no_admit,
               make_extra=(mx + " ") if mx else "", tt=True)
    (work / "geometry.json").write_text(json.dumps(dict(piece=a.piece, die=die, pins=len(pins), macros=macros,
                                                        slice=dict(w=SW, h=SH, xa=XA, xb=XB, yb=YB, rp=RP),
                                                        parent=dict(w=PW, h=PH, edge=EDGE, gap=GAP, ch=CH,
                                                                    slots=[slice_xy(k) for k in range(NSL)])),
                                                   indent=1) + "\n")
    print(f"{name}: die {die[0]} x {die[1]}, {len(pins)} pins, macros {macros}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("block")
    b.add_argument("--piece", choices=("slice", "parent"), required=True)
    b.add_argument("--views", default=None, help="parent: repo path of the slice view dir (named ot_hgi_sm_pub_slice)")
    b.add_argument("--label", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--src", required=True)
    b.add_argument("--pd", default="0.50")
    b.add_argument("--lat", default="300")
    b.add_argument("--lat-ff", default="180")
    b.add_argument("--period", default="770")
    b.add_argument("--skew", default="90")
    b.add_argument("--die-skew", default="150")
    b.add_argument("--hold-margin", default="1")
    b.add_argument("--hold-buffer-pct", default=None)
    b.add_argument("--pin-depth", default="16")
    b.add_argument("--grt-allow", action="store_true")
    b.add_argument("--need", default="48")
    b.add_argument("--cores", default="16")
    b.add_argument("--stop-after", default=None, choices=("cts",))
    b.add_argument("--no-admit", action="store_true")
    b.add_argument("--make-var", action="append", default=None)
    a = ap.parse_args(argv)
    cmd_block(a)


if __name__ == "__main__":
    main()
