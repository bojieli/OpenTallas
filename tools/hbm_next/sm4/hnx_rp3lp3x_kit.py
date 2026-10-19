#!/usr/bin/env python3
"""HBM-NEXT-P3-SM (10-19, OWNER 0le P3+(a)): ref_tile spec for the SM P = 3 matrix tile hnx_rp3lp3x (RTL top
hnx_rp3lp3x_flat_lp: hnx_rp4lp4x at P = 3 + NREL = 2 gather relays per half) in the DIE SM slot 630.72 x 2,203.2
(DIE f4c_t9p3 stand-in = "lever 630.72 x 2203.2").  Same ports / regions / landings / transport children as hnx_rp4lp4x;
each leaf holds one hnx_xs3 (561.6 x 289.44, the P3 shared x store) + 3 bdc + 3 BF16 lane stacks.

SAFE-DESIGN layout rules applied (owner 10-19 checklist item 6): EVERY hard-child origin on the 43.2-um lattice (tile x, y
multiples of 43.2; the tile itself sits on the DIE 43.2 lattice), >= 10.8-um halos, one std-cell band per gap.

  y (um)       leaf 0 (n region, R0; store at the band)                       x: 43.2 ............................ 604.8
  2030.4       row B : lane 1 tcl h0 (43.2) | tcl h1 (172.8) | tct (302.4)          (lane 1 flat: tcls nearest the W face)
  1857.6/1771.2 row A: lane 0 stack W (tct 43.2, tcl 43.2 / 172.8) | lane 2 stack E (tct 388.8, tcl 388.8 / 518.4)
  1598.4       bdc row: 3 x bdc at x 129.6 / 259.2 / 388.8 (S faces on the store's N face)
  1296         hnx_xs3 (43.2 .. 604.8): N block-dot operands, W BF16 lanes 0-1, E BF16 lane 2, S landing inputs
  950.4-1257   band: beat_t (43.2) | land_s / row_w1 / row_w0 / land_n (129.6-345.6) | beat_e (388.8) | row_e1 / row_e0 (475.2)
  648          hnx_xs3 (MX) of leaf 1 (s region), bdc row 475.2 (MX), row A tcl 302.4 / tct 216, row B 43.2
REACH (item 2): gather lanes run in the W margin (x ~ 20) with FIRM stations every ~300 um (N edge 2185 -> 1880 -> 1580 ->
mid 1280 | landing ring 1290 -> read 1000 -> 670 -> 340 -> S edge 15); gin / gout pins moved to the W corner (x 2.4-40.8);
lane-1 BF16 XREL stations FIRM between the store's W face and row B (each hop <= ~400 um).  W / E tile pins (bin / rin /
bout / rout, 3,705 per face) compressed to a 640-um run centred on the band (5.8 pins/um).

  python3 tools/hbm_next/sm4/hnx_rp3lp3x_kit.py   -> physical/hbm_next/sm4/hnx_rp3lp3x_spec.json (+ pins / stations tcl)
  python3 tools/ref_tile/ref_tile.py gen physical/hbm_next/sm4/hnx_rp3lp3x_spec.json   (needs the hnx_xs3 view)
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTD = ROOT / "physical/hbm_next/sm4"
TEMPLATE = OUTD / "hnx_rp4lp4x_spec.json"                    # hnx_rp4lp4x spec (rp4lp kit fields, SM4)
PINS_T = ROOT / "results/arch/hbm_next_1019/sm4/p3/rp4lp_pins_src.tcl"   # rp4lp pin plan (pl-smt 2444d768c), copied
STAT_T = ROOT / "physical/hbm_next/sm4/hnx_rp4lp4x_stations.tcl"
NAME = "hnx_rp3lp3x"
P = 3
G = 43.2
W, H = 630.72, 2203.2
V = {"xs3": "physical/ref_tile/hnx_rp3lp3_xs3/views/hnx_xs3",
     "bdc": "physical/ref_tile/smh_bdc_ref_p50/views/ot_hbm_accel_smh_bdc",
     "tcl": "physical/ref_tile/smh_tcl_ref_p45/views/ot_hbm_accel_smh_tcl",
     "tct": "physical/ref_tile/smh_tct_ref_p45/views/ot_hbm_accel_smh_tct",
     "land": "physical/ref_tile/smh_tr_group_land_ref/views/ot_smh_tr_group_land",
     "row_w": "physical/ref_tile/smh_tr_group_row_w_ref/views/ot_smh_tr_group_row_w",
     "beat": "physical/ref_tile/smh_tr_group_beat_e_ref/views/ot_smh_tr_group_beat_e",
     "row_e": "physical/ref_tile/smh_tr_group_row_e_ref/views/ot_smh_tr_group_row_e"}
SZ = {"xs3": (561.6, 289.44), "bdc": (112.32, 142.56), "tcl": (86.4, 120.96), "tct": (194.4, 71.28),
      "land": (216.0, 43.2), "row_w": (86.4, 90.72), "beat": (43.2, 216.0), "row_e": (43.2, 90.72)}
HALO = 10.8
# leaf rows (y of each child kind), leaf 0 (n, R0) / leaf 1 (s, MX; tct always R0 as rp4lp)
ROWS = {0: dict(xs=1296.0, bdc=1598.4, tctA=1771.2, tclA=1857.6, rowB=2030.4),
        1: dict(xs=648.0, bdc=475.2, tctA=216.0, tclA=302.4, rowB=43.2)}
BAND_Y = (950.4, 1257.12)
PIN_YC = (BAND_Y[0] + 1252.8) / 2          # band centre 1101.6: centre of the compressed W / E pin runs
RP4LP_PIN_YC, RP4LP_W, RP4LP_H = 765.6, 457.92, 1598.4
PIN_SCALE = 0.62                           # rp4lp W / E run 1,032 um -> 640 um (3,705 pins / face -> 5.8 / um)
TRK = 0.048                                # M4 / M5 track pitch; pins keep the rp4lp track offset 0.012
TRK_OFF = 0.012


def r3(x):
    return round(x + 1e-9, 3)


def children():
    out = []
    for leaf in (0, 1):
        R = ROWS[leaf]
        o = "R0" if leaf == 0 else "MX"
        reg = "n" if leaf == 0 else "s"
        pre = f"u_lf{leaf}."
        out.append(("xs3", pre + "g_xs3.u_xs", 43.2, R["xs"], o, reg))
        for p in range(P):
            out.append(("bdc", pre + f"g_ln[{p}].u_bdc", 129.6 + 129.6 * p, R["bdc"], o, reg))
        for p, x in ((0, 43.2), (2, 388.8)):                      # row A: lane 0 W, lane 2 E (store W / E faces)
            out += [("tct", pre + f"g_ln[{p}].u_tcc.u_tr", x, R["tctA"], "R0", reg),
                    ("tcl", pre + f"g_ln[{p}].u_tcc.u_h0", x, R["tclA"], o, reg),
                    ("tcl", pre + f"g_ln[{p}].u_tcc.u_h1", x + 129.6, R["tclA"], o, reg)]
        out += [("tcl", pre + "g_ln[1].u_tcc.u_h0", 43.2, R["rowB"], o, reg),     # row B: lane 1 (W face) flat
                ("tcl", pre + "g_ln[1].u_tcc.u_h1", 172.8, R["rowB"], o, reg),
                ("tct", pre + "g_ln[1].u_tcc.u_tr", 302.4, R["rowB"], "R0", reg)]
    out += [("beat", "u_beat_t", 43.2, 993.6, "R0", "n"),
            ("land", "u_land_s", 129.6, 950.4, "MX", "s"),
            ("row_w", "u_row1", 129.6, 1036.8, "MX", "s"),
            ("row_w", "u_row0", 259.2, 1036.8, "R0", "n"),
            ("land", "u_land_n", 129.6, 1166.4, "R0", "n"),
            ("beat", "u_beate", 388.8, 993.6, "R0", "n"),
            ("row_e", "u_rowe1", 475.2, 950.4, "MX", "s"),
            ("row_e", "u_rowe0", 475.2, 1166.4, "R0", "n")]
    return out


def check(ch):
    bad = []
    box = []
    for k, inst, x, y, o, reg in ch:
        w, h = SZ[k]
        for a in (x, y):
            if abs(a / G - round(a / G)) > 1e-6:
                bad.append(("off-lattice", inst, a))
        if x < 0 or y < 0 or x + w > W + 1e-6 or y + h > H + 1e-6:
            bad.append(("outside", inst))
        box.append((inst, x, y, x + w, y + h))
    for i, a in enumerate(box):
        for b in box[i + 1:]:
            if a[1] < b[3] + HALO - 1e-6 and b[1] < a[3] + HALO - 1e-6 and a[2] < b[4] + HALO - 1e-6 and b[2] < a[4] + HALO - 1e-6:
                bad.append(("halo/overlap", a[0], b[0]))
    return bad


def snap(v):
    return r3(TRK_OFF + round((v - TRK_OFF) / TRK) * TRK)


def pins_tcl():
    """rp4lp pin plan re-targeted: W / E runs compressed around the band centre; gout / gin in the W corner (gin[j] at the x
    of gout[100 + j], the pass lanes, so tiles stacked in the SM column line up); N / S straps, rst_n as rp4lp; ck_n / ck_s at
    the face centres."""
    out = [f"# generated by tools/hbm_next/sm4/hnx_rp3lp3x_kit.py from the rp4lp pin plan (pl-smt 2444d768c): outline {W} x {H};"
           f" W/E runs scaled {PIN_SCALE} about y {PIN_YC}; gin/gout in the W corner (x 2.4-40.8); ck_n / ck_s at the face centres"]
    n = 0
    seen = {}
    for ln in PINS_T.read_text().splitlines():
        m = re.match(r"(place_pin -pin_name \{([^}]+)\} -layer (\w+) -location \{)([\d.]+) ([\d.]+)(\}.*)", ln)
        if not m:
            continue
        name, layer, x, y = m.group(2), m.group(3), float(m.group(4)), float(m.group(5))
        base = name.split("[")[0]
        if base in ("ck_n", "ck_s"):
            continue
        if base in ("gout", "gin"):
            i = int(name.split("[")[1].rstrip("]")) + (100 if base == "gin" else 0)
            x = snap(2.412 + 0.192 * i)
            y = 0.0 if base == "gout" else H
        elif x == 0.0 or abs(x - RP4LP_W) < 1e-6:
            y = snap(PIN_YC + (y - RP4LP_PIN_YC) * PIN_SCALE)
            x = 0.0 if x == 0.0 else W
        elif abs(y - RP4LP_H) < 1e-6:
            y = H
        key = (x, y, layer)
        assert key not in seen, (name, seen.get(key))
        seen[key] = name
        out.append(f"{m.group(1)}{x:.3f} {y:.3f}{m.group(6)}")
        n += 1
    cx = snap(W / 2)
    out.append(f"place_pin -pin_name {{ck_n}} -layer M5 -location {{{cx:.3f} {H:.3f}}} -pin_size {{0.024 0.192}} -force_to_die_boundary")
    out.append(f"place_pin -pin_name {{ck_s}} -layer M5 -location {{{cx:.3f} 0.000}} -pin_size {{0.024 0.192}} -force_to_die_boundary")
    return "\n".join(out) + "\n", n + 2


def grp(name, pats, cx, cy, n):
    esc = []
    for p in pats:
        esc += [p, p.replace("[", "\\[").replace("]", "\\]")]
    return f"st_group {name} {{{' '.join(esc)}}} {cx} {cy} {n}\n"


def stations_tcl():
    src = STAT_T.read_text()
    head = src[src.index("set ::sr_blk"):src.index("st_group gl0_mid")]
    s = ("# HBM-NEXT-P3-SM hnx_rp3lp3x: generated by tools/hbm_next/sm4/hnx_rp3lp3x_kit.py (procs = rp4lp / hnx_rp4lp4x stations).\n"
         "# REACH (safe-design item 2): gather lanes in the W margin with FIRM stations every ~300 um; landings of the gather lanes\n"
         "# beside them; lane-1 BF16 XREL stations between the store W face and row B.\n" + head)
    x0, x1 = 14, 30
    for k in range(2):
        s += grp(f"gl{k}_n", [f"u_gn.g_gl[{k}].u_v/", f"u_gn.g_gl[{k}].u_d/"], x0 + 8 * k, 2185, 50)
        s += grp(f"gl{k}_r0", [f"u_gn.g_gl[{k}].g_rl[0].u_rv/", f"u_gn.g_gl[{k}].g_rl[0].u_rd/"], x0 + 8 * k, 1880, 50)
        s += grp(f"gl{k}_r1", [f"u_gn.g_gl[{k}].g_rl[1].u_rv/", f"u_gn.g_gl[{k}].g_rl[1].u_rd/"], x0 + 8 * k, 1580, 50)
        s += grp(f"gl{k}_mid", [f"u_gn.g_gl[{k}].u_v2/", f"u_gn.g_gl[{k}].u_d2/"], x0 + 8 * k, 1280, 50)
        s += grp(f"gs{k}_r0", [f"u_gs.g_gl[{k}].g_rl[0].u_rv/", f"u_gs.g_gl[{k}].g_rl[0].u_rd/"], x0 + 8 * k, 670, 50)
        s += grp(f"gs{k}_r1", [f"u_gs.g_gl[{k}].g_rl[1].u_rv/", f"u_gs.g_gl[{k}].g_rl[1].u_rd/"], x0 + 8 * k, 340, 50)
        s += grp(f"gs{k}_s", [f"u_gs.g_gl[{k}].u_v3/", f"u_gs.g_gl[{k}].u_d3/"], x0 + 8 * k, 15, 50)
    s += grp("lf0_r0", ["u_gn.g_ro[0].u_rv/", "u_gn.g_ro[0].u_rd/"], x1, 1640, 50)
    s += grp("lf0_r1", ["u_gn.g_ro[1].u_rv/", "u_gn.g_ro[1].u_rd/"], x1, 1460, 50)
    s += grp("lf0_mid", ["u_gn.u_grv2/", "u_gn.u_grd2/"], x1, 1290, 50)
    s += grp("lf0_s_r0", ["u_gs.g_ro[0].u_rv/", "u_gs.g_ro[0].u_rd/"], x1, 690, 50)
    s += grp("lf0_s_r1", ["u_gs.g_ro[1].u_rv/", "u_gs.g_ro[1].u_rd/"], x1, 360, 50)
    s += grp("lf0_s", ["u_gs.u_gov0/", "u_gs.u_god0/"], x1, 20, 50)
    for i in (1, 2):                      # gather landings (lp.py): ring in n beside the mid stage, read in s
        s += grp(f"land{i}_w", [f"u_lpl_{i}_w/"], 22, 1300, 0)
        s += grp(f"land{i}_r", [f"u_lpl_{i}_r/"], 22, 1000, 0)
    # lane-1 BF16 XREL stations (531 flops each) between the store W face and row B
    s += grp("x1_n", ["u_lf0.g_ln[1].xf_", "u_lf0/g_ln[1].xf_"], 100, 1756, 531)
    s += grp("x1_s", ["u_lf1.g_ln[1].xf_", "u_lf1/g_ln[1].xf_"], 100, 449, 531)
    return s + 'puts "RP4_STATION fixed $::sr_fixed"\n'


def main():
    s = json.loads(TEMPLATE.read_text())
    src = json.loads((ROOT / "rtl/hbm_next/sm/sources.json").read_text())
    ch = children()
    bad = check(ch)
    assert not bad, bad
    s["name"] = NAME
    s["top"] = "hnx_rp3lp3x_flat_lp"
    s["sources"] = [f for f in src["kit_sources"] if not f.endswith("hnx_rp4lp4.sv")] + ["rtl/hbm_next/sm/lp/hnx_rp3lp3x_flat_lp.sv"]
    s["defines"] = src["defines"]
    s["hard_define"] = "SYNTHESIS"
    s["outline"] = {"w": W, "h": H}
    s["child_lattice_um"] = G
    s["children"] = [dict(view=V[k], count=1, at=[r3(x), r3(y)], orient=o, inst=inst, region=reg) for k, inst, x, y, o, reg in ch]
    s["landed_record"] = "results/arch/hbm_next_1019/sm4/p3/hnx_rp3lp3x_flat_lp_record.json"
    pt, npins = pins_tcl()
    (OUTD / f"{NAME}_pins.tcl").write_text(pt)
    (OUTD / f"{NAME}_stations.tcl").write_text(stations_tcl())
    s["io_tcl"] = f"physical/hbm_next/sm4/{NAME}_pins.tcl"
    s["orfs_vars"] = dict(s.get("orfs_vars", {}), POST_TAPCELL_TCL=f"physical/hbm_next/sm4/{NAME}_stations.tcl")
    s["route"] = dict(s["route"], peak_ram_gb=160, threads=16, hold_margin_ns=0.03, io_hold_margin_ns=0.03)
    s["reset_landing"] = {"enable": True, "clock": "ck_n"}
    s["pin_regs"] = dict(s["pin_regs"], reason=s["pin_regs"]["reason"].replace("hnx_rp4lp4", "hnx_rp4lp4 / hnx_rp4lp4x"))
    s["job"] = {
        "owner": "Claude HBM-NEXT-P3-SM", "branch": "claude/hbm-next-p3sm-1019", "tag": NAME,
        "purpose": "NEXT-release HBM die (OWNER 10-19 P3+(a), not a release gate): SM P = 3 matrix tile on the shared 3-lane x store "
                   "hnx_xs3; CRITICAL tile hnx_rp3*: coordinator PNG review before any submit (report only).",
        "structural_change": (
            f"{NAME} (HBM-NEXT-P3-SM 10-19) = hnx_rp4lp4x at P = 3 (RTL hnx_rp3lp3x_flat_lp, lp.py landed regions n / s): per leaf "
            "one hnx_xs3 at the band + 3 bdc on its N face + 3 BF16 lane stacks (lanes 0 / 2 beside each other, lane 1 flat in row B "
            "nearest the store's W face) = 2 x 13 leaf hard children + the 8 rp4lp transport children, ALL on the 43.2 lattice; "
            f"outline {W} x {H} = the DIE P3 SM slot (aspect 3.5:1: two landed regional halves 630.72 x ~1,100 each, <= 1.8:1); "
            "NREL = 2 gather relays per half (+4 edges on the pass / leaf-0 gather lanes, compiler record) with FIRM stations "
            "every ~300 um; publish lane delays as ring buffers."),
        "extra_paths": ["physical/common_flow/anchor_row_packing.tcl", "tools/hbm_next", "results/arch/hbm_next_1019/sm4",
                        "rtl/hbm_next"],
        "benches": [
            {"name": "lp_lockstep", "expect": "pass", "pass_regex": "BENCH_EXIT 0", "threads": 8, "peak_ram_gb": 96,
             "cmd": "LP_ROOT=$PWD SIM=verilator bash rtl/hbm_next/sm/lp/hnx_rp3lp3x_flat_lp_bench.sh {RUN}/lp"},
            {"name": "leaf_lanes_p3_xs3", "expect": "pass", "pass_regex": "BENCH PASS p3_m0_t0", "threads": 8, "peak_ram_gb": 24,
             "cmd": "bash rtl/hbm_next/sm/tb/run_leaf_bench.sh {RUN}/leaf 3 0 0 -DHNX_XS4"}]}
    (OUTD / f"{NAME}_spec.json").write_text(json.dumps(s, indent=1) + "\n")
    hard = sum(SZ[k][0] * SZ[k][1] for k, *_ in ch)
    geo = {"outline_um": [W, H], "area_mm2": round(W * H / 1e6, 4), "aspect": round(H / W, 2), "hard_um2": round(hard),
           "hard_fill": round(hard / (W * H), 3), "children": len(ch), "pins": npins, "all_children_on_43p2": True}
    print(json.dumps(geo))
    return geo


if __name__ == "__main__":
    main()
