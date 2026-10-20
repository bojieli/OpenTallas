#!/usr/bin/env python3
"""HNX-SM4/SM4P (10-20): ref_tile specs for the SM P = 3 tile as TWO HARDENED HALVES (SAFE-DESIGN item 6: the one-piece
hnx_rp3lp3x is 630.72 x 2,203.2 = 3.49:1).  RTL rtl/hbm_next/sm/hnx_rp3lp3h.sv:
  hnx_rp3lp3h_n  630.72 x 1,209.6 (1.92:1), ONE root ck_n: leaf 0 + row 0 + bin beat path (beat_t / beat_e slabs, land_n)
                 + N gather relays + the seam landing RING (150 b).
  hnx_rp3lp3h_s  630.72 x 1,036.8 (1.64:1), ONE root ck_s: leaf 1 + row 1 + land_s on its OWN bin capture + seam landing
                 READ + S gather relays.  No SRAM macros (the flat lp's 4 dual-clock + 7 pad SRAMs are gone).
DIE slot = the two halves abutted, N above S: 630.72 x 2,246.4 (+43.2 um over the 2,203.2 stand-in; see main() 'why').

Every hard-child origin on the 43.2 lattice (half origins on the die lattice too: 1,036.8 = 24 x 43.2), >= 10.8-um halos.
Leaf rows are the matched pad-return plan's (results/arch/hbm_next_1019/sm4/p3/pad_return_plan/candidate.json); leaf 0 is
shifted by -993.6 um into the N half, leaf 1 keeps its coordinates in the S half.

  python3 tools/hbm_next/sm4/hnx_rp3lp3h_kit.py   -> physical/hbm_next/sm4/hnx_rp3lp3h_{n,s}_spec.json (+ pins / stations tcl)
                                                   + results/arch/hbm_next_1019/sm4/p3/halves/{floorplan.png, geometry.json}
  python3 tools/ref_tile/ref_tile.py gen physical/hbm_next/sm4/hnx_rp3lp3h_n_spec.json   (needs the hnx_xs3 (xs3n) view)
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTD = ROOT / "physical/hbm_next/sm4"
RESD = ROOT / "results/arch/hbm_next_1019/sm4/p3/halves"
TEMPLATE = OUTD / "hnx_rp3lp3x_spec.json"
STAT_T = OUTD / "hnx_rp4lp4x_stations.tcl"
CAND = ROOT / "results/arch/hbm_next_1019/sm4/p3/pad_return_plan/candidate.json"
G = 43.2
W = 630.72
H = {"n": 1209.6, "s": 1036.8}
SHIFT = {"n": -993.6, "s": 0.0}          # flat (candidate) y -> half-local y for the leaf rows
HALO = 10.8
TRK, TRK_OFF = 0.048, 0.012
V = {"xs3": "physical/ref_tile/hnx_rp3lp3_xs3n/views/hnx_xs3",
     "bdc": "physical/ref_tile/smh_bdc_ref_p50/views/ot_hbm_accel_smh_bdc",
     "tcl": "physical/ref_tile/smh_tcl_ref_p45/views/ot_hbm_accel_smh_tcl",
     "tct": "physical/ref_tile/smh_tct_ref_p45/views/ot_hbm_accel_smh_tct",
     "land": "physical/ref_tile/smh_tr_group_land_ref/views/ot_smh_tr_group_land",
     "row_w": "physical/ref_tile/smh_tr_group_row_w_ref/views/ot_smh_tr_group_row_w",
     "beat": "physical/ref_tile/smh_tr_group_beat_e_ref/views/ot_smh_tr_group_beat_e",
     "row_e": "physical/ref_tile/smh_tr_group_row_e_ref/views/ot_smh_tr_group_row_e"}
SZ = {"xs3": (561.6, 289.44), "bdc": (112.32, 142.56), "tcl": (86.4, 120.96), "tct": (194.4, 71.28),
      "land": (216.0, 43.2), "row_w": (86.4, 90.72), "beat": (43.2, 216.0), "row_e": (43.2, 90.72)}
KIND = {"g_xs3.u_xs": "xs3", "u_bdc": "bdc", "u_tcc.u_tr": "tct", "u_tcc.u_h0": "tcl", "u_tcc.u_h1": "tcl"}
# transport children that are NOT at their plan positions (the band is split by the seam)
OWN = {"n": [("beat", "u_beat_t", 43.2, 43.2, "R0"), ("beat", "u_beate", 561.6, 43.2, "R0"),
             ("land", "u_land_n", 129.6, 216.0, "R0"),
             ("row_w", "u_row0", 432.0, 604.8, "R0"), ("row_e", "u_rowe0", 561.6, 604.8, "R0")],
       "s": [("land", "u_land_s", 43.2, 950.4, "MX"),
             ("row_w", "u_row1", 432.0, 475.2, "MX"), ("row_e", "u_rowe1", 561.6, 475.2, "MX")]}
NAME = {"n": "hnx_rp3lp3h_n", "s": "hnx_rp3lp3h_s"}


def r3(x):
    return round(x + 1e-9, 3)


def kind_of(inst):
    for k, v in KIND.items():
        if inst.endswith(k):
            return v
    raise KeyError(inst)


def children(half):
    leaf = "u_lf0." if half == "n" else "u_lf1."
    out = []
    for r in json.loads(CAND.read_text())["rects"]:
        if r["name"].startswith(leaf):
            k = kind_of(r["name"])
            assert (r["w"], r["h"]) == SZ[k], r
            out.append((k, r["name"], r["x"], r3(r["y"] + SHIFT[half]), r["orient"]))
    assert len(out) == 13, out
    return out + OWN[half]


def check(half, ch):
    bad, box = [], []
    for k, inst, x, y, o in ch:
        w, h = SZ[k]
        for a in (x, y):
            if abs(a / G - round(a / G)) > 1e-6:
                bad.append(("off-lattice", inst, a))
        if x < 0 or y < 0 or x + w > W + 1e-6 or y + h > H[half] + 1e-6:
            bad.append(("outside", inst))
        if min(x, y, W - x - w, H[half] - y - h) < HALO - 1e-6:
            bad.append(("edge<halo", inst))
        box.append((inst, x, y, x + w, y + h))
    for i, a in enumerate(box):
        for b in box[i + 1:]:
            if a[1] < b[3] + HALO - 1e-6 and b[1] < a[3] + HALO - 1e-6 and a[2] < b[4] + HALO - 1e-6 and b[2] < a[4] + HALO - 1e-6:
                bad.append(("halo/overlap", a[0], b[0]))
    return bad


def snap(v):
    return r3(TRK_OFF + round((v - TRK_OFF) / TRK) * TRK)


def pin(name, face, pos, h):
    if face in ("W", "E"):
        x, y, lay, size = (0.0 if face == "W" else W), snap(pos), "M4", "0.192 0.024"
    else:
        x, y, lay, size = snap(pos), (0.0 if face == "S" else h), "M5", "0.024 0.192"
    return (f"place_pin -pin_name {{{name}}} -layer {lay} -location {{{x:.3f} {y:.3f}}} -pin_size {{{size}}} "
            f"-force_to_die_boundary"), (x if face in "NS" else y)


def pin_plan(half):
    """W / E runs placed beside the hard child they feed (reach), <= 5.3 pins/um; abutted faces mirror each other (bin[i]
    / bout[i], rin[i] / rout[i] at the same y; the seam sb_* at the same x on N.S and S.N; gin[j] at the x of gout[100+j])."""
    h = H[half]
    P = []
    seam = [(f"sb_bank[{i}]", 43.212 + 0.432 * i) for i in range(600)] + [(f"sb_vld[{i}]", 43.212 + 0.432 * (600 + i)) for i in range(4)]
    if half == "n":
        for i in range(2069):
            P += [("bin[%d]" % i, "W", 10.812 + 0.24 * i), ("bout[%d]" % i, "E", 10.812 + 0.24 * i)]
        for i in range(818):
            P += [("rin_n[%d]" % i, "W", 552.012 + 0.24 * i), ("rout_n[%d]" % i, "E", 552.012 + 0.24 * i)]
        P += [(n, "S", x) for n, x in seam]
        P += [("gin[%d]" % j, "N", 2.412 + 0.192 * (100 + j)) for j in range(100)]
        x = 240.012
        for nm, wd in (("xs_a1", 9), ("xs_g1", 5), ("xs_a2", 7), ("xs_g2", 5)):
            for i in range(wd):
                P.append((f"{nm}[{i}]", "N", x)); x += 0.96
        P += [("rst_n", "N", 280.032), ("ck_n", "N", W / 2)]
    else:
        for i in range(818):
            P += [("rin_s[%d]" % i, "W", 420.012 + 0.24 * i), ("rout_s[%d]" % i, "E", 420.012 + 0.24 * i)]
        for i in range(2069):
            P += [("bin[%d]" % i, "W", 628.812 + 0.192 * i)]
        P += [(n, "N", x) for n, x in seam]
        P += [("gout[%d]" % j, "S", 2.412 + 0.192 * j) for j in range(200)]
        x = 166.908
        for nm, wd in (("xss_a1", 9), ("xss_g1", 5), ("xss_a2", 7), ("xss_g2", 5)):
            for i in range(wd):
                P.append((f"{nm}[{i}]", "S", x)); x += 0.96
        P += [("rst_n", "S", 200.016), ("ck_s", "S", W / 2)]
    lines, seen, dens = [], set(), {}
    for name, face, pos in P:
        ln, key = pin(name, face, pos, h)
        assert (face, key) not in seen, (name, face, key)
        seen.add((face, key))
        lines.append(ln)
        dens.setdefault(face, []).append(key)
    peak = {}
    for f, ks in dens.items():         # worst pins in any 10-um window
        ks.sort()
        j, best = 0, 0
        for i, k in enumerate(ks):
            while ks[j] < k - 10.0:
                j += 1
            best = max(best, i - j + 1)
        peak[f] = round(best / 10.0, 2)
    assert max(peak.values()) <= 6.0, peak
    hdr = (f"# generated by tools/hbm_next/sm4/hnx_rp3lp3h_kit.py: {NAME[half]} {W} x {h}; peak pins/um (10-um window) {peak}")
    return hdr + "\n" + "\n".join(lines) + "\n", len(lines), peak


def grp(name, pats, cx, cy, n):
    esc = []
    for p in pats:
        esc += [p, p.replace("[", "\\[").replace("]", "\\]")]
    return f"st_group {name} {{{' '.join(esc)}}} {cx} {cy} {n}\n"


def stations(half):
    src = STAT_T.read_text()
    head = src[src.index("set ::sr_blk"):src.index("st_group gl0_mid")]
    s = (f"# HNX-SM4/SM4P {NAME[half]}: generated by tools/hbm_next/sm4/hnx_rp3lp3h_kit.py (procs = rp4lp / hnx_rp4lp4x stations).\n"
         "# REACH (item 2): gather lanes in the W margin with FIRM 50-flop stations every <= ~305 um (flat hnx_rp3lp3x stations\n"
         "# moved into the half); the seam landing ring / read are left to the placer beside their seam pins (x 43-305).\n" + head)
    x0, x1 = 14, 30
    if half == "n":
        for k in range(2):
            s += grp(f"gl{k}_n", [f"u_gn.g_gl[{k}].u_v/", f"u_gn.g_gl[{k}].u_d/"], x0 + 8 * k, 1190, 50)
            s += grp(f"gl{k}_r0", [f"u_gn.g_gl[{k}].g_rl[0].u_rv/", f"u_gn.g_gl[{k}].g_rl[0].u_rd/"], x0 + 8 * k, 886, 50)
            s += grp(f"gl{k}_r1", [f"u_gn.g_gl[{k}].g_rl[1].u_rv/", f"u_gn.g_gl[{k}].g_rl[1].u_rd/"], x0 + 8 * k, 586, 50)
            s += grp(f"gl{k}_mid", [f"u_gn.g_gl[{k}].u_v2/", f"u_gn.g_gl[{k}].u_d2/"], x0 + 8 * k, 286, 50)
        s += grp("lf0_r0", ["u_gn.g_ro[0].u_rv/", "u_gn.g_ro[0].u_rd/"], x1, 646, 50)
        s += grp("lf0_r1", ["u_gn.g_ro[1].u_rv/", "u_gn.g_ro[1].u_rd/"], x1, 466, 50)
        s += grp("lf0_mid", ["u_gn.u_grv2/", "u_gn.u_grd2/"], x1, 296, 50)
        s += grp("x1_n", ["u_lf0.g_ln[1].xf_", "u_lf0/g_ln[1].xf_"], 100, 762, 531)
    else:
        for k in range(2):
            s += grp(f"gs{k}_r0", [f"u_gs.g_gl[{k}].g_rl[0].u_rv/", f"u_gs.g_gl[{k}].g_rl[0].u_rd/"], x0 + 8 * k, 670, 50)
            s += grp(f"gs{k}_r1", [f"u_gs.g_gl[{k}].g_rl[1].u_rv/", f"u_gs.g_gl[{k}].g_rl[1].u_rd/"], x0 + 8 * k, 340, 50)
            s += grp(f"gs{k}_s", [f"u_gs.g_gl[{k}].u_v3/", f"u_gs.g_gl[{k}].u_d3/"], x0 + 8 * k, 15, 50)
        s += grp("lf0_s_r0", ["u_gs.g_ro[0].u_rv/", "u_gs.g_ro[0].u_rd/"], x1, 690, 50)
        s += grp("lf0_s_r1", ["u_gs.g_ro[1].u_rv/", "u_gs.g_ro[1].u_rd/"], x1, 360, 50)
        s += grp("lf0_s", ["u_gs.u_gov0/", "u_gs.u_god0/"], x1, 20, 50)
        s += grp("x1_s", ["u_lf1.g_ln[1].xf_", "u_lf1/g_ln[1].xf_"], 100, 449, 531)
    return s + 'puts "RP4_STATION fixed $::sr_fixed"\n'


def draw(geo_ch):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    col = {"xs3": "#7aa6d6", "bdc": "#e3a35b", "tcl": "#8cc084", "tct": "#5f9e58", "land": "#c47ac0", "row_w": "#d6c35a",
           "beat": "#d65a5a", "row_e": "#b0a040"}
    fig, axs = plt.subplots(1, 2, figsize=(10, 15), gridspec_kw={"width_ratios": [1, 1]})
    ax = axs[0]
    base = {"s": 0.0, "n": H["s"]}
    for half in ("s", "n"):
        y0 = base[half]
        ax.add_patch(Rectangle((0, y0), W, H[half], fill=False, lw=2, ec="k"))
        for k, inst, x, y, o in geo_ch[half]:
            w, h = SZ[k]
            ax.add_patch(Rectangle((x, y0 + y), w, h, fc=col[k], ec="k", lw=0.5))
            ax.text(x + w / 2, y0 + y + h / 2, inst.replace("g_ln", "").replace("u_tcc.", "").replace(".u_", " ").replace("u_", "")
                    + (" " + o if o != "R0" else ""), ha="center", va="center", fontsize=5.5)
        ax.text(W + 8, y0 + H[half] / 2, f"{NAME[half]}\n{W} x {H[half]}\n{H[half] / W:.2f}:1\nroot ck_{half}", fontsize=8, va="center")
    ax.plot([0, W], [H["s"], H["s"]], "m-", lw=3)
    ax.text(W / 2, H["s"] + 8, "SEAM: 600 bank + 4 vld pins (x 43-305), gather landing D4 E2 (+3)", color="m", ha="center", fontsize=7)
    ax.add_patch(Rectangle((-6, 10.8 + H["n"] * 0 + H["s"]), 6, 496.6, fc="r"))
    ax.text(-10, H["s"] + 250, "bin", color="r", ha="right", fontsize=7)
    ax.add_patch(Rectangle((-6, 628.8), 6, 397.2, fc="r"))
    ax.text(-10, 830, "bin (die fan-out)", color="r", ha="right", fontsize=7)
    ax.add_patch(Rectangle((-6, H["s"] + 552), 6, 196.3, fc="g"))
    ax.text(-10, H["s"] + 650, "rin_n", color="g", ha="right", fontsize=7)
    ax.add_patch(Rectangle((-6, 420), 6, 196.3, fc="g"))
    ax.text(-10, 520, "rin_s", color="g", ha="right", fontsize=7)
    ax.add_patch(Rectangle((W, H["s"] + 10.8), 6, 496.6, fc="r"))
    ax.add_patch(Rectangle((W, H["s"] + 552), 6, 196.3, fc="g"))
    ax.add_patch(Rectangle((W, 420), 6, 196.3, fc="g"))
    for (x, y) in [(18, H["s"] + 1190), (18, H["s"] + 886), (18, H["s"] + 586), (18, H["s"] + 286), (18, 670), (18, 340), (18, 15)]:
        ax.plot(x, y, "ks", ms=3)
    ax.set_xlim(-160, W + 170)
    ax.set_ylim(-20, H["s"] + H["n"] + 20)
    ax.set_aspect("equal")
    ax.set_title(f"SM P=3 tile as two hardened halves (slot {W} x {r3(H['s'] + H['n'])})", fontsize=9)
    # reference: the one-piece flat tile (plan positions)
    ax = axs[1]
    ax.add_patch(Rectangle((0, 0), W, 2203.2, fill=False, lw=2, ec="k"))
    for r in json.loads(CAND.read_text())["rects"]:
        k = "pad" if r["name"].startswith("new_") else None
        if k is None:
            try:
                k = kind_of(r["name"])
            except KeyError:
                k = {"u_beat_t": "beat", "u_beate": "beat", "u_land_s": "land", "u_land_n": "land", "u_row1": "row_w",
                     "u_row0": "row_w", "u_rowe1": "row_e", "u_rowe0": "row_e"}[r["name"]]
        ax.add_patch(Rectangle((r["x"], r["y"]), r["w"], r["h"], fc=col.get(k, "#999999"), ec="k", lw=0.5))
    ax.set_xlim(-160, W + 170)
    ax.set_ylim(-20, H["s"] + H["n"] + 20)
    ax.set_aspect("equal")
    ax.set_title("before: one-piece hnx_rp3lp3x 630.72 x 2203.2 (3.49:1)\n(grey = 4 dual-clock + 7 pad SRAMs, removed)", fontsize=9)
    RESD.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(RESD / "floorplan.png", dpi=110)


def spec(half, ch, tmpl):
    s = copy.deepcopy(tmpl)
    for k in ("clock", "clock_ports", "clock_data_paths", "clock_relationship", "clock_entry_domains", "landed_record"):
        s.pop(k, None)
    src = json.loads((ROOT / "rtl/hbm_next/sm/sources.json").read_text())
    s["name"] = NAME[half]
    s["top"] = NAME[half]
    s["sources"] = [f for f in src["kit_sources"] if not f.endswith(("hnx_rp4lp4.sv", "hnx_rp3lp3.sv"))] + \
        ["rtl/hbm_next/common/hnx_pl_pad_sram.sv", "rtl/hbm_next/sm/hnx_rp3lp3h.sv"]
    s["defines"] = src["defines"]
    s["hard_define"] = "SYNTHESIS"
    s["clock_port"] = f"ck_{half}"
    s["outline"] = {"w": W, "h": H[half]}
    s["child_lattice_um"] = G
    s["children"] = [dict(view=V[k], count=1, at=[r3(x), r3(y)], orient=o, inst=inst) for k, inst, x, y, o in ch]
    s["macros"] = []
    if half == "n":
        s["pins"] = {"W": ["rin_n", "bin"], "E": ["rout_n", "bout"], "S": ["sb_bank", "sb_vld"],
                     "N": ["gin", "xs_a1", "xs_g1", "xs_a2", "xs_g2", "rst_n", "ck_n"]}
    else:
        s["pins"] = {"W": ["rin_s", "bin"], "E": ["rout_s"], "N": ["sb_bank", "sb_vld"],
                     "S": ["gout", "xss_a1", "xss_g1", "xss_a2", "xss_g2", "rst_n", "ck_s"]}
    s["io_tcl"] = f"physical/hbm_next/sm4/{NAME[half]}_pins.tcl"
    s["orfs_vars"] = dict(s.get("orfs_vars", {}), POST_TAPCELL_TCL=f"physical/hbm_next/sm4/{NAME[half]}_stations.tcl")
    s["route"] = dict(s["route"], peak_ram_gb=96, threads=16, hold_margin_ns=0.03, io_hold_margin_ns=0.03)
    s["reset_landing"] = {"enable": True, "clock": f"ck_{half}"}
    s["pin_regs"] = dict(s["pin_regs"], reason=(
        "HNX-SM4P halves: actual RTL pin capture / launch registers (rin / bin pin flops in hnx_rp4l_pinrow / pinbeat -- the S half "
        "has its OWN bin pinbeat u_pbs --, rout / bout launched by the hard row_e / beat_e cells, gin / gout by the gather "
        "registers, xs_* / xss_* through the five-stage straps); seam: sb_bank / sb_vld are the ring flops of ot_pl_land_w "
        "(N, flop -> pin) and land on the AND-OR -> flop of ot_pl_land_r (S, pin -> 1 mux level -> flop).  ONE root per half."))
    s["job"] = {
        "owner": "Claude HNX-SM4/SM4P", "branch": "claude/hnx-sm4p-1020", "tag": NAME[half],
        "purpose": "NEXT-release HBM die (OWNER 10-19 P3+(a), not a release gate): SM P = 3 tile hardened as two <= 2:1 halves "
                   "(safe-design item 6); CRITICAL prefix hnx_rp3*: coordinator PNG review before any submit (report only).",
        "structural_change": (
            "HNX-SM4P 10-20: hnx_rp3lp3x (630.72 x 2203.2, 3.49:1) split into two hardened halves along its lp regions: "
            f"{NAME['n']} 630.72 x 1209.6 (ck_n: leaf 0, row 0, bin beat path, N gather, seam ring) above {NAME['s']} 630.72 x "
            "1036.8 (ck_s: leaf 1, row 1, land_s on its own bin capture, seam read, S gather); the n->s seam is the 150-b gather "
            "landing only (D 4, E = K = 2, +3, as the lp record); the 2,069-b bin_l landing (4 dual-clock SRAMs) and the rl1_s / "
            "st_s pads (7 SRAMs) are removed (die fans bin out to both halves); compiler offsets identical to the flat lp record."),
        "extra_paths": ["physical/common_flow/anchor_row_packing.tcl", "tools/hbm_next", "results/arch/hbm_next_1019/sm4",
                        "rtl/hbm_next"],
        "benches": [
            {"name": "halves_lockstep", "expect": "pass", "pass_regex": "BENCH_EXIT 0", "threads": 8, "peak_ram_gb": 96,
             "pass_witness": "results/arch/hbm_next_1019/sm4/p3/halves/bench/bench.log",
             "cmd": "LP_ROOT=$PWD MUTS=0 bash rtl/hbm_next/sm/halves/hnx_rp3lp3x_halves_bench.sh {RUN}/hv0"}] + [
            {"name": f"halves_mut{m}", "expect": "fail", "fail_regex": f"HV_LOCKSTEP FAIL MUT={m}", "threads": 8, "peak_ram_gb": 96,
             "fail_witness": f"results/arch/hbm_next_1019/sm4/p3/halves/bench/mut{m}.log",
             "cmd": (f"LP_ROOT=$PWD MUTS={m} bash rtl/hbm_next/sm/halves/hnx_rp3lp3x_halves_bench.sh {{RUN}}/hv{m}; "
                     f"cat {{RUN}}/hv{m}/mut{m}.log; grep -q 'HV_LOCKSTEP PASS' {{RUN}}/hv{m}/mut{m}.log")} for m in (1, 2, 3, 4)] + [
            {"name": "leaf_lanes_p3_xs3", "expect": "pass", "pass_regex": "BENCH PASS p3_m0_t0", "threads": 8, "peak_ram_gb": 24,
             "cmd": "bash rtl/hbm_next/sm/tb/run_leaf_bench.sh {RUN}/leaf 3 0 0 -DHNX_XS4"}]}
    return s


def main():
    tmpl = json.loads(TEMPLATE.read_text())
    geo, chs = {}, {}
    for half in ("n", "s"):
        ch = children(half)
        bad = check(half, ch)
        assert not bad, bad
        chs[half] = ch
        s = spec(half, ch, tmpl)
        pt, npins, peak = pin_plan(half)
        (OUTD / f"{NAME[half]}_pins.tcl").write_text(pt)
        (OUTD / f"{NAME[half]}_stations.tcl").write_text(stations(half))
        (OUTD / f"{NAME[half]}_spec.json").write_text(json.dumps(s, indent=1) + "\n")
        hard = sum(SZ[k][0] * SZ[k][1] for k, *_ in ch)
        area = W * H[half]
        geo[NAME[half]] = {"outline_um": [W, H[half]], "area_mm2": round(area / 1e6, 4), "aspect": round(H[half] / W, 2),
                           "hard_um2": round(hard), "hard_fill": round(hard / area, 3), "children": len(ch), "macros": 0,
                           "pins": npins, "peak_pins_per_um_10um": peak, "all_children_on_43p2": True, "min_halo_um": HALO}
    geo["slot"] = {"outline_um": [W, r3(H["n"] + H["s"])], "vs_flat_um": round(H["n"] + H["s"] - 2203.2, 2),
                   "die_cost_mm2": round(8 * (H["n"] + H["s"] - 2203.2) * 23891.84 / 1e6, 3),
                   "why": ("lattice-quantised minimum: leaf rows are already at their 43.2 minimum (S: rowB 43.2 .. xs1 top 937.44, "
                           "land_s 950.4-993.6, 43.2 seam margin; N: beat_t / beat_e slabs 43.2-259.2 with land_n between, xs0 at "
                           "302.4, rowB top 1157.76, 51.84 top margin).  The flat tile saved this 43.2 um by putting land_n and "
                           "land_s side by side in ONE shared band row -- impossible once the band belongs to two tiles.  "
                           "die cost = 8 SM rows x 43.2 um x die width 23,891.84 um (safe_sm_pack README: 8.257 mm2 per 43.2)")}
    geo["reshape_alternative"] = {
        "slot_at_2to1": [864.0, 1641.6], "area_mm2": round(864.0 * 1641.6 / 1e6, 4),
        "die_width_um": round(23891.84 + 32 * (864.0 - W), 1), "reticle_width_um": 26000,
        "verdict": "REJECTED: a <= 2:1 one-piece slot of the same area widens the 32-column SM array by 32 x 233.28 = 7,465 um "
                   "-> die 31.36 mm wide > 26 mm reticle (and re-packs every SM column); the halves cost +8.26 mm2 (+1.08%)."}
    RESD.mkdir(parents=True, exist_ok=True)
    (RESD / "geometry.json").write_text(json.dumps(geo, indent=1) + "\n")
    draw(chs)
    print(json.dumps(geo, indent=1))
    return geo


if __name__ == "__main__":
    main()
