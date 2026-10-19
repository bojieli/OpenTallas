#!/usr/bin/env python3
"""HBM-NEXT-SM4 (10-19): ref_tile spec for the LEVER (a) SM P = 4 tile hnx_rp4lp4x (PROG-adopted base: one SHARED 4-lane x
store hnx_xs4 per leaf).  Same ports, transport children, landed regions n / s and clocking as hnx_rp4lp4
(tools/hbm_next/sm4/hnx_rp4lp4_kit.py, from rp4lp pl-smt 2444d768c); the leaf is re-packed around the shared store:

  leaf (R0, leaf 0 above the middle band; leaf 1 below it mirrored MX, tct kept R0 as rp4lp / hnx_rp4lp4):

        +-----------+ +--------------------------------+ +-----------+
        | lane 1    | |  bdc0   bdc1   bdc2   bdc3      | | lane 3    |   bdc S faces (operands) face the store's N face
        | tcl  tcl  | |  (4 x 112.32 at 129.6 pitch)    | | tcl  tcl  |
        | tct       | +--------------------------------+ | tct       |
        +-----------+ +--------------------------------+ +-----------+
        | lane 0    | |  hnx_xs4 501.12 x 289.44         | | lane 2    |   store W / E faces -> BF16 lanes 0-1 / 2-3
        | tcl  tcl  | |  N: o_iwb/o_ixb  S: landing in   | | tcl  tcl  |   (face split, rtl/hbm_next/sm/hnx_xs4.sv)
        | tct       | |                                  | |           |
        +-----------+ +--------------------------------+ +-----------+
                      ^ land_n (2,069 b) + row_w0 (818 b) N faces, middle band

  * lane stack = the d4g rp4lp leaf-0 BF16 arrangement unchanged (tct, two tcl above it): 198.72 x 216 um;
  * 4 block-dot columns in one row on the store's N face (+25.92 um XREL station band);
  * leaf 457.92 um tall (store 289.44 + 25.92 + bdc 142.56 = 2 x 216 + 25.92), 43.2-um operand channels between the
    lane stacks and the store/bdc column;
  * middle band 259.2 um (rp4lp transport children: land_n / row_w0 under leaf 0's store, land_s / row_w1 MX above
    leaf 1's store, beat_t at the W edge, beat_e + row_e at the E edge).

  python3 tools/hbm_next/sm4/hnx_rp4lp4x_kit.py [rp4lp_spec rp4lp_pins rp4lp_stations]
        -> physical/hbm_next/sm4/hnx_rp4lp4x_spec.json (+ pins / stations tcl), outline in results/arch/hbm_next_1019/sm4/geometry.json
  python3 tools/ref_tile/ref_tile.py gen physical/hbm_next/sm4/hnx_rp4lp4x_spec.json   (needs the CLOSED hnx_xs4 view)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NAME = "hnx_rp4lp4x"
OUTD = ROOT / "physical/hbm_next/sm4"
TEMPLATE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/sm4_rp4lp_spec.json")   # rp4lp spec (pl-smt 2444d768c)
PINS_T = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/sm4_rp4lp_pins.tcl")
STAT_T = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("/tmp/sm4_rp4lp_stations.tcl")
P = 4
XS4_VIEW = "physical/ref_tile/hnx_rp4lp4_xs4/views/hnx_xs4"          # exists once the xs4 kit is routed (closed view)
V = {"xs4": XS4_VIEW,
     "bdc": "physical/ref_tile/smh_bdc_ref_p50/views/ot_hbm_accel_smh_bdc",
     "tcl": "physical/ref_tile/smh_tcl_ref_p45/views/ot_hbm_accel_smh_tcl",
     "tct": "physical/ref_tile/smh_tct_ref_p45/views/ot_hbm_accel_smh_tct",
     "land": "physical/ref_tile/smh_tr_group_land_ref/views/ot_smh_tr_group_land",
     "row_w": "physical/ref_tile/smh_tr_group_row_w_ref/views/ot_smh_tr_group_row_w",
     "beat": "physical/ref_tile/smh_tr_group_beat_e_ref/views/ot_smh_tr_group_beat_e",
     "row_e": "physical/ref_tile/smh_tr_group_row_e_ref/views/ot_smh_tr_group_row_e"}
SZ = {"xs4": (501.12, 289.44), "bdc": (112.32, 142.56), "tcl": (86.4, 120.96), "tct": (194.4, 71.28)}
HARD_UM2 = {"xs4": 501.12 * 289.44, "bdc": 112.32 * 142.56, "tcl": 86.4 * 120.96, "tct": 194.4 * 71.28,
            "land": 216.0 * 43.2, "row_w": 86.4 * 90.72, "beat": 43.2 * 216.0, "row_e": 43.2 * 90.72}
STACK_W, STACK_H = 198.72, 216.0
GAP_X = 43.2                               # operand channel lane stack | store / bdc column
GAP_ST = 25.92                             # between the two lane stacks of a side / store -> bdc XREL station band
LEAF_H = SZ["xs4"][1] + GAP_ST + SZ["bdc"][1]
assert abs(LEAF_H - (2 * STACK_H + GAP_ST)) < 1e-6, LEAF_H
X0 = 43.2                                  # leaf origin x (43.2 lattice); children inside on the 4.32 lattice
XS_DX = STACK_W + GAP_X                    # store x inside the leaf
XE_DX = XS_DX + SZ["xs4"][0] + GAP_X       # E stack x inside the leaf
W = 1080.0
H = 1339.2
Y_L1 = 43.2                                # leaf 1 origin (MX)
Y_M = 531.36                               # middle band bottom
HM = 259.2
Y_L0 = 820.8                               # leaf 0 origin (R0)
assert X0 + XE_DX + STACK_W <= W - 43.2 + 1e-6
assert Y_L1 + LEAF_H + 30.24 - 1e-6 <= Y_M and Y_M + HM + 30.24 - 1e-6 <= Y_L0 and Y_L0 + LEAF_H + 43.2 <= H + 1e-6
RP4LP_W, RP4LP_H, RP4LP_PIN_YC = 457.92, 1598.4, 765.6
DY_PINS = (Y_M + HM / 2) - RP4LP_PIN_YC     # rp4lp W/E pin run centre -> middle band centre


def r3(x):
    return round(x + 1e-9, 3)


def leaf_children():
    """(kind, inst suffix, dx, dy) in the R0 leaf frame (origin bottom-left, store at the bottom facing the band)."""
    out = [("xs4", "g_xs.u_xs", XS_DX, 0.0)]
    by = SZ["xs4"][1] + GAP_ST
    for p in range(P):
        out.append(("bdc", f"g_ln[{p}].u_bdc", XS_DX + 129.6 * p, by))
    # BF16 lane stacks: lanes 0 / 1 W (lower / upper), lanes 2 / 3 E -- matches the store's face split (PW = 2)
    for p, (sx, sy) in enumerate(((0.0, 0.0), (0.0, STACK_H + GAP_ST), (XE_DX, 0.0), (XE_DX, STACK_H + GAP_ST))):
        out += [("tct", f"g_ln[{p}].u_tcc.u_tr", sx, sy),
                ("tcl", f"g_ln[{p}].u_tcc.u_h0", sx, sy + 95.04),
                ("tcl", f"g_ln[{p}].u_tcc.u_h1", sx + 112.32, sy + 95.04)]
    return out


def children():
    out = []
    for leaf, y0, orient, reg in ((0, Y_L0, "R0", "n"), (1, Y_L1, "MX", "s")):
        for kind, sub, dx, dy in leaf_children():
            h = SZ[kind][1]
            y = y0 + dy if orient == "R0" else y0 + LEAF_H - dy - h
            o = "R0" if kind == "tct" else orient      # the tct view's pins are on the tracks only in R0 (as rp4lp leaf 1)
            out.append(dict(view=V[kind], count=1, at=[r3(X0 + dx), r3(y)], orient=o, inst=f"u_lf{leaf}.{sub}", region=reg))
    m = Y_M
    xs = X0 + XS_DX
    out += [dict(view=V["beat"], count=1, at=[86.4, r3(m + 21.6)], orient="R0", inst="u_beat_t", region="n"),
            dict(view=V["row_w"], count=1, at=[r3(xs + 17.28), r3(m)], orient="MX", inst="u_row1", region="s"),
            dict(view=V["row_w"], count=1, at=[r3(xs + 17.28), r3(m + HM - 90.72)], orient="R0", inst="u_row0", region="n"),
            dict(view=V["land"], count=1, at=[r3(xs + 190.08), r3(m)], orient="MX", inst="u_land_s", region="s"),
            dict(view=V["land"], count=1, at=[r3(xs + 190.08), r3(m + HM - 43.2)], orient="R0", inst="u_land_n", region="n"),
            dict(view=V["beat"], count=1, at=[950.4, r3(m + 21.6)], orient="R0", inst="u_beate", region="n"),
            dict(view=V["row_e"], count=1, at=[1010.88, r3(m)], orient="MX", inst="u_rowe1", region="s"),
            dict(view=V["row_e"], count=1, at=[1010.88, r3(m + HM - 90.72)], orient="R0", inst="u_rowe0", region="n")]
    return out


def overlaps(ch):
    box = []
    for c in ch:
        k = next(k for k, v in V.items() if v == c["view"])
        w, h = SZ.get(k, {"land": (216.0, 43.2), "row_w": (86.4, 90.72), "beat": (43.2, 216.0), "row_e": (43.2, 90.72)}.get(k))
        box.append((c["inst"], c["at"][0], c["at"][1], c["at"][0] + w, c["at"][1] + h))
    bad = []
    for i in range(len(box)):
        a = box[i]
        if a[1] < 0 or a[2] < 0 or a[3] > W + 1e-6 or a[4] > H + 1e-6:
            bad.append(("outside", a[0]))
        for b in box[i + 1:]:
            if a[1] < b[3] - 10.8 and b[1] < a[3] - 10.8 and a[2] < b[4] - 10.8 and b[2] < a[4] - 10.8:
                bad.append((a[0], b[0]))
            elif a[1] < b[3] + 10.8 - 1e-6 and b[1] < a[3] + 10.8 - 1e-6 and a[2] < b[4] + 10.8 - 1e-6 and b[2] < a[4] + 10.8 - 1e-6:
                bad.append(("halo", a[0], b[0]))
    return bad


def pins_tcl():
    out = [f"# generated by tools/hbm_next/sm4/hnx_rp4lp4x_kit.py from smh_tile_rp4lp_pins.tcl (pl-smt 2444d768c): outline {W} x {H};"
           f" W/E pins y {DY_PINS:+.2f} (rp4lp run centred on the middle band); E face x -> {W}; N face y -> {H}; ck_n / ck_s at the"
           " N / S face centre"]
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
        elif abs(x - RP4LP_W) < 1e-6:
            x, y = W, y + DY_PINS
        elif abs(y - RP4LP_H) < 1e-6:
            y = H
        assert 0 <= y <= H and 0 <= x <= W, ln
        out.append(f"{m.group(1)}{x:.3f} {y:.3f}{m.group(5)}")
        n += 1
    cx = W / 2
    out.append(f"place_pin -pin_name {{ck_n}} -layer M5 -location {{{cx:.3f} {H:.3f}}} -pin_size {{0.024 0.192}} -force_to_die_boundary")
    out.append(f"place_pin -pin_name {{ck_s}} -layer M5 -location {{{cx:.3f} 0.000}} -pin_size {{0.024 0.192}} -force_to_die_boundary")
    return "\n".join(out) + "\n", n + 2


def stations_tcl():
    src = STAT_T.read_text()
    head = src[:src.index("st_group gl0_mid")]
    y = Y_M + HM / 2
    xs = X0 + XS_DX
    return ("# HBM-NEXT-SM4 hnx_rp4lp4x: generated by tools/hbm_next/sm4/hnx_rp4lp4x_kit.py from the rp4lp stations (procs unchanged).\n"
            "# N-region mid stages of the N->S gather lanes FIRM in the middle band centre (between land_s and land_n).\n"
            + head +
            f"st_group gl0_mid {{u_gn.g_gl[0].u_v2/ u_gn.g_gl[0].u_d2/ u_gn.g_gl\\[0\\].u_v2/ u_gn.g_gl\\[0\\].u_d2/}} {xs + 210:.0f} {y:.1f} 50\n"
            f"st_group gl1_mid {{u_gn.g_gl[1].u_v2/ u_gn.g_gl[1].u_d2/ u_gn.g_gl\\[1\\].u_v2/ u_gn.g_gl\\[1\\].u_d2/}} {xs + 300:.0f} {y:.1f} 50\n"
            f"st_group lf0_mid {{u_gn.u_grv2/ u_gn.u_grd2/}} {xs + 390:.0f} {y:.1f} 50\n"
            'puts "RP4_STATION fixed $::sr_fixed"\n')


def main():
    s = json.loads(TEMPLATE.read_text())
    src = json.loads((ROOT / "rtl/hbm_next/sm/sources.json").read_text())
    ch = children()
    bad = overlaps(ch)
    assert not bad, bad
    s["name"] = NAME
    s["top"] = "hnx_rp4lp4x_flat_lp"
    s["sources"] = src["kit_sources"] + ["rtl/hbm_next/sm/lp/hnx_rp4lp4x_flat_lp.sv"]
    s["defines"] = src["defines"]
    s["outline"] = {"w": W, "h": H}
    s["children"] = ch
    s["landed_record"] = "results/arch/hbm_next_1019/sm4/hnx_rp4lp4x_flat_lp_record.json"
    pt, npins = pins_tcl()
    OUTD.mkdir(parents=True, exist_ok=True)
    (OUTD / f"{NAME}_pins.tcl").write_text(pt)
    (OUTD / f"{NAME}_stations.tcl").write_text(stations_tcl())
    s["io_tcl"] = f"physical/hbm_next/sm4/{NAME}_pins.tcl"
    s["orfs_vars"] = dict(s.get("orfs_vars", {}), POST_TAPCELL_TCL=f"physical/hbm_next/sm4/{NAME}_stations.tcl")
    s["route"] = dict(s["route"], peak_ram_gb=160, threads=16)
    s["pin_regs"] = dict(s["pin_regs"], reason=(
        "As rp4lp / hnx_rp4lp4: actual RTL pin capture / launch registers (rin / bin pin flops in hnx_rp4l_pinrow / pinbeat, rout / bout "
        "launched by the hard row_e / beat_e cells, gin / gout by the gather registers, xs_* through the five-stage straps); TWO regional "
        "roots (ck_n, ck_s, lp.py landed regions), every n->s data net landed (bin_l 2,069 b, leaf-0 gather 50 b, pass-through gather "
        "100 b). Inside each leaf ONE kept lane-front register copy feeds the shared x store; per lane the XREL operand stations (+0, d4g)."))
    s["job"] = {
        "owner": "Claude HBM-NEXT-SM4", "branch": "claude/hbm-next-sm4-1019", "tag": NAME,
        "purpose": "NEXT-release HBM die (not a release gate): SM P = 4 matrix tile, LEVER (a) shared 4-lane x store (PROG-adopted base); "
                   "CRITICAL tile: coordinator PNG review before any submit (HBM-NEXT-PROG).",
        "structural_change": (
            f"{NAME} (HBM-NEXT-SM4 10-19) = hnx_rp4lp4 with the leaves on the SHARED x store: per leaf one hnx_xs4 (face split: N "
            "block-dot operands, W / E BF16 operands) + 4 bdc in one row on its N face + 4 BF16 lane stacks (tct + 2 tcl, d4g arrangement) "
            f"beside it (lanes 0-1 W, 2-3 E) = 2 x 17 leaf hard children + the 8 rp4lp transport children; outline {W} x {H}, middle "
            "band 259.2. Ports, regions, landings and cycle timing as hnx_rp4lp4."),
        "extra_paths": ["physical/common_flow/anchor_row_packing.tcl", "tools/hbm_next", "results/arch/hbm_next_1019/sm4",
                        "rtl/hbm_next"],
        "benches": [
            {"name": "lp_lockstep", "expect": "pass", "pass_regex": "BENCH_EXIT 0", "threads": 8, "peak_ram_gb": 96,
             "cmd": "LP_ROOT=$PWD SIM=verilator bash rtl/hbm_next/sm/lp/hnx_rp4lp4x_flat_lp_bench.sh {RUN}/lp"},
            {"name": "leaf_lanes_p4_xs4", "expect": "pass", "pass_regex": "BENCH PASS p4_m0_t0", "threads": 8, "peak_ram_gb": 24,
             "cmd": "bash rtl/hbm_next/sm/tb/run_leaf_bench.sh {RUN}/leaf 4 0 0 -DHNX_XS4"}]}
    (OUTD / f"{NAME}_spec.json").write_text(json.dumps(s, indent=1) + "\n")
    hard = 2 * (HARD_UM2["xs4"] + P * (HARD_UM2["bdc"] + HARD_UM2["tct"] + 2 * HARD_UM2["tcl"])) + \
        2 * (HARD_UM2["land"] + HARD_UM2["row_w"] + HARD_UM2["beat"] + HARD_UM2["row_e"])
    print(json.dumps({"spec": str(OUTD / (NAME + "_spec.json")), "children": len(ch), "pins": npins, "outline_um": [W, H],
                      "area_mm2": round(W * H / 1e6, 4), "hard_um2": round(hard), "hard_fill": round(hard / (W * H), 3)}))


if __name__ == "__main__":
    main()
