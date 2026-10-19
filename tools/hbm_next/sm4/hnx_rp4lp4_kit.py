#!/usr/bin/env python3
"""HBM-NEXT-SM4 (10-19): ref_tile spec for the SM P = 4 tile hnx_rp4lp4 (kit physical/ref_tile/hnx_rp4lp4; ref_tile.py
hard-codes physical/ref_tile/, so the kit sits there under the hnx_ prefix; the spec source is physical/hbm_next/sm4/).

Forked from the d4g landed SM tile kit smh_tile_rp4lp (claude/pl-smt-1018 2444d768c, tools/hbm_sm_repack_1015/rp4_lp_kit.py)
by COPY: same CLOSED child views, same transport children, same port names / widths, same two lp.py regions n / s, same
PL-KIT landed-cluster clock (multiple_cts_roots ck_n / ck_s, landed_record).  Changes:
  * every leaf holds P = 4 LANE UNITS; a lane unit = the rp4lp leaf-0 arrangement (x store, block-dot column above it, the
    tct + two tcl BF16 tiles beside it): 336.96 x 401.76 um, children on the 4.32 lattice inside the unit, unit origins
    on the 43.2 lattice;
  * leaf = 2 x 2 lane units (columns A x 43.2, B x 475.2: 95 um vertical channel for the per-lane fan-out registers and
    the far-row buses); leaf 0 (region n) above the middle band in R0 (x stores face the band), leaf 1 (region s) below it
    mirrored (MX);
  * the middle band (302.4 um) holds the transport children 2-D instead of rp4lp's 745-um W-column stack: beat_t at the
    W edge, row_w 0/1, land_n / land_s beside the leaf x stores, row_e 0/1 + beat_e at the E edge;
  * W / E data pins: the rp4lp pin sites shifted up so the rin_s | bin | rin_n run (1,032 um, ~3.6 pins/um) is centred
    on the middle band; N / S pins as rp4lp (outline N face at H); ck_n / ck_s at the face centres;
  * gather mid stations re-targeted to the middle band.

  python3 tools/hbm_next/sm4/hnx_rp4lp4_kit.py   -> physical/hbm_next/sm4/hnx_rp4lp4_spec.json (+ pins / stations tcl)
  python3 tools/ref_tile/ref_tile.py gen physical/hbm_next/sm4/hnx_rp4lp4_spec.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NAME = "hnx_rp4lp4"
OUTD = ROOT / "physical/hbm_next/sm4"
TEMPLATE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/sm4_rp4lp_spec.json")   # rp4lp spec (pl-smt 2444d768c)
PINS_T = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/sm4_rp4lp_pins.tcl")
STAT_T = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("/tmp/sm4_rp4lp_stations.tcl")
P = 4
V = {"xs": "physical/ref_tile/smh_xs_ref_p45m/views/ot_hbm_accel_smh_xs",
     "bdc": "physical/ref_tile/smh_bdc_ref_p50/views/ot_hbm_accel_smh_bdc",
     "tcl": "physical/ref_tile/smh_tcl_ref_p45/views/ot_hbm_accel_smh_tcl",
     "tct": "physical/ref_tile/smh_tct_ref_p45/views/ot_hbm_accel_smh_tct",
     "land": "physical/ref_tile/smh_tr_group_land_ref/views/ot_smh_tr_group_land",
     "row_w": "physical/ref_tile/smh_tr_group_row_w_ref/views/ot_smh_tr_group_row_w",
     "beat": "physical/ref_tile/smh_tr_group_beat_e_ref/views/ot_smh_tr_group_beat_e",
     "row_e": "physical/ref_tile/smh_tr_group_row_e_ref/views/ot_smh_tr_group_row_e"}
SZ = {"xs": (302.4, 157.68), "bdc": (112.32, 142.56), "tcl": (86.4, 120.96), "tct": (194.4, 71.28)}
UNIT_H = 401.76
# lane unit (R0), offsets from the rp4lp leaf-0 arrangement (xs at (51.84, 1170.72) there)
UNIT = [("xs", "u_xs", 0.0, 0.0), ("bdc", "u_bdc", 0.0, 185.76), ("tct", "u_tcc.u_tr", 138.24, 185.76),
        ("tcl", "u_tcc.u_h0", 138.24, 280.8), ("tcl", "u_tcc.u_h1", 250.56, 280.8)]
XA, XB = 43.2, 475.2                       # lane columns
Y_L1 = (43.2, 518.4)                       # leaf 1 rows (MX), bottom -> top
Y_M = 950.4                                # middle band bottom
HM = 302.4
Y_L0 = (1296.0, 1728.0)                    # leaf 0 rows (R0)
W, H = 889.92, 2160.0
DY_PINS = 336.0                            # W / E pin run shift (rp4lp centre 765.6 -> middle band centre 1101.6)


def r3(x):
    return round(x + 1e-9, 3)


def children():
    out = []
    lanes = [(XA, 0), (XB, 1)]
    for leaf, rows, orient, reg in ((0, Y_L0, "R0", "n"), (1, Y_L1, "MX", "s")):
        k = 0
        for y0 in rows:
            for x0, _ in lanes:
                for kind, sub, dx, dy in UNIT:
                    h = SZ[kind][1]
                    y = y0 + dy if orient == "R0" else y0 + UNIT_H - dy - h
                    # the tct view's pins are on the tracks only in R0 (rp4lp leaf 1 keeps its tct R0 too)
                    o = "R0" if kind == "tct" else orient
                    out.append(dict(view=V[kind], count=1, at=[r3(x0 + dx), r3(y)], orient=o,
                                    inst=f"u_lf{leaf}.g_ln[{k}].u_lh.{sub}", region=reg))
                k += 1
    m = Y_M
    out += [dict(view=V["beat"], count=1, at=[60.48, r3(m + 43.2)], orient="R0", inst="u_beat_t", region="n"),
            dict(view=V["row_w"], count=1, at=[129.6, r3(m)], orient="MX", inst="u_row1", region="s"),
            dict(view=V["row_w"], count=1, at=[129.6, r3(m + HM - 90.72)], orient="R0", inst="u_row0", region="n"),
            dict(view=V["land"], count=1, at=[259.2, r3(m)], orient="MX", inst="u_land_s", region="s"),
            dict(view=V["land"], count=1, at=[259.2, r3(m + HM - 43.2)], orient="R0", inst="u_land_n", region="n"),
            dict(view=V["row_e"], count=1, at=[820.8, r3(m)], orient="MX", inst="u_rowe1", region="s"),
            dict(view=V["beat"], count=1, at=[756.0, r3(m + 43.2)], orient="R0", inst="u_beate", region="n"),
            dict(view=V["row_e"], count=1, at=[820.8, r3(m + HM - 90.72)], orient="R0", inst="u_rowe0", region="n")]
    return out


def pins_tcl():
    out = [f"# generated by tools/hbm_next/sm4/hnx_rp4lp4_kit.py from smh_tile_rp4lp_pins.tcl (pl-smt 2444d768c): outline {W} x {H};"
           f" W/E pins y +{DY_PINS}; E face x -> {W}; N face y -> {H}; ck_n / ck_s at the N / S face centre"]
    n = 0
    for ln in PINS_T.read_text().splitlines():
        m = re.match(r"(place_pin -pin_name \{([^}]+)\} -layer \w+ -location \{)([\d.]+) ([\d.]+)(\}.*)", ln)
        if not m:
            continue
        name, x, y = m.group(2), float(m.group(3)), float(m.group(4))
        if name in ("ck_n", "ck_s"):
            continue
        if x == 0.0:
            y += DY_PINS
        elif abs(x - 457.92) < 1e-6:
            x, y = W, y + DY_PINS
        elif abs(y - 1598.4) < 1e-6:
            y = H
        out.append(f"{m.group(1)}{x:.3f} {y:.3f}{m.group(5)}")
        n += 1
    cx = 444.96
    out.append(f"place_pin -pin_name {{ck_n}} -layer M5 -location {{{cx:.3f} {H:.3f}}} -pin_size {{0.024 0.192}} -force_to_die_boundary")
    out.append(f"place_pin -pin_name {{ck_s}} -layer M5 -location {{{cx:.3f} 0.000}} -pin_size {{0.024 0.192}} -force_to_die_boundary")
    return "\n".join(out) + "\n", n + 2


def stations_tcl():
    src = STAT_T.read_text()
    head = src[:src.index("st_group gl0_mid")]
    y = Y_M + HM / 2
    return ("# HBM-NEXT-SM4 hnx_rp4lp4: generated by tools/hbm_next/sm4/hnx_rp4lp4_kit.py from the rp4lp stations (procs unchanged).\n"
            "# N-region mid stages of the N->S gather lanes FIRM in the middle band gap (between row_w 1 / row_w 0 and land_s / land_n).\n"
            + head +
            f"st_group gl0_mid {{u_gn.g_gl[0].u_v2/ u_gn.g_gl[0].u_d2/ u_gn.g_gl\\[0\\].u_v2/ u_gn.g_gl\\[0\\].u_d2/}} 205 {y:.1f} 50\n"
            f"st_group gl1_mid {{u_gn.g_gl[1].u_v2/ u_gn.g_gl[1].u_d2/ u_gn.g_gl\\[1\\].u_v2/ u_gn.g_gl\\[1\\].u_d2/}} 300 {y:.1f} 50\n"
            f"st_group lf0_mid {{u_gn.u_grv2/ u_gn.u_grd2/}} 395 {y:.1f} 50\n"
            'puts "RP4_STATION fixed $::sr_fixed"\n')


def main():
    s = json.loads(TEMPLATE.read_text())
    src = json.loads((ROOT / "rtl/hbm_next/sm/sources.json").read_text())
    s["name"] = NAME
    s["top"] = "hnx_rp4lp4_flat_lp"
    s["sources"] = src["kit_sources"] + ["rtl/hbm_next/sm/lp/hnx_rp4lp4_flat_lp.sv"]
    s["defines"] = src["defines"]
    s["outline"] = {"w": W, "h": H}
    s["children"] = children()
    s["landed_record"] = "results/arch/hbm_next_1019/sm4/hnx_rp4lp4_flat_lp_record.json"
    pt, npins = pins_tcl()
    OUTD.mkdir(parents=True, exist_ok=True)
    (OUTD / f"{NAME}_pins.tcl").write_text(pt)
    (OUTD / f"{NAME}_stations.tcl").write_text(stations_tcl())
    s["io_tcl"] = f"physical/hbm_next/sm4/{NAME}_pins.tcl"
    s["orfs_vars"] = dict(s.get("orfs_vars", {}), POST_TAPCELL_TCL=f"physical/hbm_next/sm4/{NAME}_stations.tcl")
    s["route"] = dict(s["route"], peak_ram_gb=160, threads=16)
    s["pin_regs"] = dict(s["pin_regs"], reason=(
        "As rp4lp: actual RTL pin capture / launch registers (rin / bin pin flops in hnx_rp4l_pinrow / pinbeat, rout / bout launched "
        "by the hard row_e / beat_e cells, gin / gout by the gather registers, xs_* through the five-stage straps); TWO regional roots "
        "(ck_n, ck_s, lp.py landed regions), every n->s data net landed (bin_l 2,069 b, leaf-0 gather 50 b, pass-through gather 100 b). "
        "Inside each leaf every lane takes the row bundle and the x-write beat through its own kept register copy (+1)."))
    s["job"] = {
        "owner": "Claude HBM-NEXT-SM4", "branch": "claude/hbm-next-sm4-1019", "tag": "hnx_rp4lp4",
        "purpose": "NEXT-release HBM die (not a release gate): SM P = 4 matrix tile, 4 accumulator lanes per MAC column; "
                   "CRITICAL tile: coordinator PNG review before any submit (HBM-NEXT-PROG).",
        "structural_change": (
            "hnx_rp4lp4 (HBM-NEXT-SM4 10-19) = rp4lp (PL-SMT 2444d768c, landed regions n / s) with P = 4 lanes per leaf: 2 leaves x 4 "
            "lane units (each the closed x store + block-dot column + tct + 2 tcl) = 40 leaf hard children + the 8 rp4lp transport "
            f"children; outline {W} x {H} (2 x 2 lane units per leaf, compact 2-D middle band); per-lane kept fan-out registers (+1), "
            "lane-select x-write beats (zero beat one-hot), slot-major publish (lane p +p*8, collision = fault). Ports unchanged."),
        "extra_paths": ["physical/common_flow/anchor_row_packing.tcl", "tools/hbm_next", "results/arch/hbm_next_1019/sm4",
                        "rtl/hbm_next"],
        "benches": [
            {"name": "lp_lockstep", "expect": "pass", "pass_regex": "BENCH_EXIT 0", "threads": 8, "peak_ram_gb": 96,
             "cmd": "LP_ROOT=$PWD SIM=verilator bash rtl/hbm_next/sm/lp/hnx_rp4lp4_flat_lp_bench.sh {RUN}/lp"},
            {"name": "leaf_lanes_p4", "expect": "pass", "pass_regex": "BENCH PASS p4_m0_t0", "threads": 8, "peak_ram_gb": 24,
             "cmd": "bash rtl/hbm_next/sm/tb/run_leaf_bench.sh {RUN}/leaf 4 0 0"}]}
    (OUTD / f"{NAME}_spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print(f"{OUTD / (NAME + '_spec.json')}: {len(s['children'])} children, pins {npins}, outline {W} x {H}")


if __name__ == "__main__":
    main()
