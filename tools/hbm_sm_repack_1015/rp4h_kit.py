#!/usr/bin/env python3
"""L2H-SM9 (LEAD2-HBM, 10-19; RELEASE_TREE H.STA.BLK.9): ref_tile specs for the HBM SM tile rp4 as TWO HARDENED HALVES.

RTL rtl/hbm_accel/sm/repack/h2/ot_hbm_smh_rp4h.sv: ot_hbm_smh_rp4h_n (leaf 0, row 0, beat path, N gather relays) and
ot_hbm_smh_rp4h_s (leaf 1, row 1, S gather outputs), abutted in the GEN2 SM frame slot (457.92 wide), n on top.
Safe-design review (owner checklist 10-19) of the predecessor smh_tile_rp4lp: aspect 3.49, 13/18 macros off 43.2,
landing read select 8,284 loads.  These kits: every hard child on the 43.2 um lattice, aspect <= 2:1, one clock root per
half (clk pin on the abutment face beside its partner's, so the die feeds both halves from one point), no landing.

Leaf stack (both halves, bottom-up): transpose R0 y 43.2 | BF16 columns R0 (x 216 / 345.6) + block-dot MX y 172.8 |
x store MX y 345.6 | row_w / row_e MX y 561.6 (first faces the x store) -- the leaf sits at the S side of BOTH halves.
Variants (gate in parallel, bind the first pair that closes):
  n_a  457.92 x 907.2  hard beat columns MX y 648, row_e beside the x store (y 345.6)       } a: 907.2 + 691.2 = 1,598.4
  s_a  457.92 x 691.2  row 1 y 561.6, N band 38.9 um for the landing / crossing registers  }    (current SM frame row)
  n_b  457.92 x 864.0  SOFTBEAT=1: the beat transits as soft kept registers (no macro band) } b: 864 + 734.4 = 1,598.4
  s_b  457.92 x 734.4  row 1 y 604.8 (x store -> row channel 101.5 um)                       }
  python3 tools/hbm_sm_repack_1015/rp4h_kit.py   -> SAFE2 kits physical/ref_tile/smh_rp4h{n,s}_{a,b}_km{32,64}[cx]/spec.json
  (the 1019 kits came from main_1019(); see the SAFE2 note above safe2_kits)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "physical/ref_tile/smh_tile_rp4lp/spec.json"
SPECS = ROOT / "physical/ref_tile_specs/smh"
W = 457.92
V = {
    "xs": "physical/ref_tile/smh_xs_ref_p45m/views/ot_hbm_accel_smh_xs",
    "bdc": "physical/ref_tile/smh_bdc_ref_p50/views/ot_hbm_accel_smh_bdc",
    "tcl": "physical/ref_tile/smh_tcl_ref_p45/views/ot_hbm_accel_smh_tcl",
    "tct": "physical/ref_tile/smh_tct_ref_p45/views/ot_hbm_accel_smh_tct",
    "beat": "physical/ref_tile/smh_tr_group_beat_e_ref/views/ot_smh_tr_group_beat_e",
    "roww": "physical/ref_tile/smh_tr_group_row_w_ref/views/ot_smh_tr_group_row_w",
    "rowe": "physical/ref_tile/smh_tr_group_row_e_ref/views/ot_smh_tr_group_row_e",
}
RTL = "rtl/hbm_accel/sm/repack/h2/ot_hbm_smh_rp4h.sv"
BENCH_ONE = "rtl/hbm_accel/sm/repack/h2/run_rp4h2_one.sh"
WIT = "results/arch/l2h_sm9_1019/bench"


def leaf():
    """one leaf, the SAME stack in both halves (bottom-up from y 43.2): transpose R0 (its M6 / M4 side pins stay on the
    track grid only in R0 / MY: 71.28 um is not a multiple of the M6 pitch, so it cannot be mirrored in y), the two BF16
    columns R0 (sum_o face down to the transpose's sum_i; operand inputs face up) beside the block-dot MX (operand inputs
    face up), then the x store MX (o_iw / o_ix face down to the columns, bk1 / rl1 face up to row_w and the soft landing
    registers).  BF16 columns at x 216 / 345.6: >= 20 um channels to the block-dot (17.3 failed at 172.8)."""
    return [("tct", "u_tcc.u_tr", 216.0, 43.2, "R0"),
            ("tcl", "u_tcc.u_h0", 216.0, 172.8, "R0"),
            ("tcl", "u_tcc.u_h1", 345.6, 172.8, "R0"),
            ("bdc", "u_bdc", 43.2, 172.8, "MX"),
            ("xs", "u_xs", 43.2, 345.6, "MX")]


def L(j):
    return [(v, f"u_lf{j}.u_lh.{i}", x, y, o) for v, i, x, y, o in leaf()]


KITS = {
    # n half, hard beat columns MX on top (y 648: 43.2 um below the N pin face), row_e beside the x store in the free E
    # column (y 345.6) so the beat columns do not stack on it; 907.2
    "smh_rp4hn_a1019": dict(half="n", h=907.2, params={}, kids=L(0) + [
        ("roww", "u_row0", 129.6, 561.6, "MX"), ("rowe", "u_rowe0", 388.8, 345.6, "MX"),
        ("beat", "g_hbeat.u_beat_t", 43.2, 648.0, "MX"), ("beat", "g_hbeat.u_beate", 388.8, 648.0, "MX")],
        ranges={"W": {"rin_n": (302.4, 552.96), "bin": (557.28, 902.88)}, "E": {"rout_n": (302.4, 552.96), "bout": (557.28, 902.88)}},
        desc="hard beat columns, 907.2 um (frame row unchanged with s_a)"),
    # n half, SOFTBEAT=1: beat transits as soft kept registers, no 216-um macro band, 864
    "smh_rp4hn_b1019": dict(half="n", h=864.0, params={"SOFTBEAT": 1}, kids=L(0) + [
        ("roww", "u_row0", 129.6, 561.6, "MX"), ("rowe", "u_rowe0", 388.8, 561.6, "MX")],
        ranges={"W": {"rin_n": (302.4, 470.88), "bin": (475.2, 861.84)}, "E": {"rout_n": (302.4, 470.88), "bout": (475.2, 861.84)}},
        desc="soft beat transits, 864 um (frame row unchanged with s_b)"),
    "smh_rp4hs_a1019": dict(half="s", h=691.2, params={}, kids=L(1) + [
        ("roww", "u_row1", 129.6, 561.6, "MX"), ("rowe", "u_rowe1", 388.8, 561.6, "MX")],
        ranges={"W": {"rin_s": (500.4, 686.88)}, "E": {"rout_s": (500.4, 686.88)}}, desc="691.2 um (pairs with n_a)"),
    "smh_rp4hs_b1019": dict(half="s", h=734.4, params={}, kids=L(1) + [
        ("roww", "u_row1", 129.6, 604.8, "MX"), ("rowe", "u_rowe1", 388.8, 604.8, "MX")],
        ranges={"W": {"rin_s": (543.6, 730.08)}, "E": {"rout_s": (543.6, 730.08)}},
        desc="734.4 um, x store -> row channel 101.5 um (pairs with n_b)"),
}
# abutment face (n S / s N): same x ranges so bit i meets bit i; clk / rst_n side by side so the die feeds both halves
# from one point between them
CROSS = {"n": {"face": "S", "b": "xo_b", "g0": "xo_g0", "gp": "xo_gp"},
         "s": {"face": "N", "b": "xi_b", "g0": "xi_g0", "gp": "xi_gp"}}
XR = {"b": (4.32, 397.44), "rst_n": (399.6, 400.68), "clk": (403.92, 405.0), "g0": (408.24, 421.2), "gp": (423.36, 453.6)}


def stations(name, half, h):
    """FIRM middle stages of the long N->S gather lanes (n: gin pass lanes u_gn.g_gl[k].u_v2/u_d2 and the leaf-0 lane
    (the leaf-0 lane is short now: leaf 0 sits at n's S side); s: the crossing relays u_xg2 / u_xp2), placed E of the x store where the core is free."""
    src = (SPECS / "smh_tile_rp4lp_stations.tcl").read_text()
    head = src[:src.index("st_group gl0_mid")]
    hdr = (f"# L2H-SM9 {name}: generated by tools/hbm_sm_repack_1015/rp4h_kit.py (procs from smh_tile_rp4lp_stations.tcl).\n"
           "# Middle stage of every long N->S gather lane FIRM half-way (hops <= ~455 um in n, ~345 um in s).\n")
    body = head[head.index("set ::sr_blk"):]
    if half == "n":
        ym = round(h / 2, 1)
        groups = (f"st_group gl0_mid {{u_gn.g_gl[0].u_v2/ u_gn.g_gl[0].u_d2/ u_gn.g_gl\\[0\\].u_v2/ u_gn.g_gl\\[0\\].u_d2/}} 400 {ym} 50\n"
                  f"st_group gl1_mid {{u_gn.g_gl[1].u_v2/ u_gn.g_gl[1].u_d2/ u_gn.g_gl\\[1\\].u_v2/ u_gn.g_gl\\[1\\].u_d2/}} 425 {ym} 50\n"
                  )
    else:
        groups = ("st_group xg2_mid {u_xg2.} 400 330.0 50\n"
                  "st_group xp2_mid {u_xp2.} 425 330.0 100\n")
    return hdr + body + groups + 'puts "RP4_STATION fixed $::sr_fixed"\n'


def benches(sb):
    """lockstep vs the flat parent (+3 mutants, each with a committed fail witness); the soft-beat n kit runs SOFTBEAT=1
    for the exact run and the bin-crossing mutant (mutants 2 / 3 are s-half paths, unchanged by SOFTBEAT)"""
    t = "sb" if sb else ""
    out = [{"name": f"h2_lockstep{t}", "cmd": f"bash {BENCH_ONE} {{RUN}}/h2{t} 0 {sb}", "expect": "pass",
            "pass_regex": "^H2_LOCKSTEP PASS MUT=0 compared=", "pass_witness": f"{WIT}/mut{t}0.log", "threads": 4,
            "peak_ram_gb": 48}]
    for m in (1, 2, 3):
        ms = sb if m == 1 else 0
        tt = "sb" if ms else ""
        out.append({"name": f"h2_mut{tt}{m}", "cmd": f"bash {BENCH_ONE} {{RUN}}/h2m{tt}{m} {m} {ms}", "expect": "fail",
                    "fail_regex": f"^H2_LOCKSTEP FAIL MUT={m} mismatches=[1-9]", "fail_witness": f"{WIT}/mut{tt}{m}.log",
                    "threads": 4, "peak_ram_gb": 48})
    return out


def spec(name, k, base):
    s = json.loads(json.dumps(base))
    half, h = k["half"], k["h"]
    s["name"] = name
    s["top"] = f"ot_hbm_smh_rp4h_{half}"
    s["params"] = dict(k["params"])
    s["sources"] = [f for f in base["sources"] if not f.endswith("ot_hbm_smh_rp4_flat_lp.sv")] + [RTL]
    s["clock_port"] = "clk"
    s["reset_ports"] = ["rst_n"]
    for key in ("clock_ports", "clock", "clock_data_paths", "clock_relationship", "clock_entry_domains", "landed_record",
                "io_tcl"):
        s.pop(key, None)
    s["outline"] = {"w": W, "h": h}
    s["child_lattice_um"] = 43.2
    s["children"] = [{"view": V[v], "count": 1, "at": [x, y], "orient": o, "inst": i} for v, i, x, y, o in k["kids"]]
    c = CROSS[half]
    cf = c["face"]
    if half == "n":
        pins = {"W": ["bin", "rin_n"], "E": ["bout", "rout_n"], "N": ["gin", "xs_a1", "xs_g1", "xs_a2", "xs_g2"],
                "S": [c["b"], "rst_n", "clk", c["g0"], c["gp"]]}
        rng = {"gin": (181.44, 228.96), "xs_a1": (233.28, 237.6), "xs_g1": (239.76, 241.92), "xs_a2": (244.08, 247.32),
               "xs_g2": (249.48, 251.64)}
    else:
        pins = {"W": ["rin_s"], "E": ["rout_s"], "S": ["gout", "xss_a1", "xss_g1", "xss_a2", "xss_g2"],
                "N": [c["b"], "rst_n", "clk", c["g0"], c["gp"]]}
        rng = {"gout": (181.44, 280.8), "xss_a1": (285.12, 289.44), "xss_g1": (291.6, 293.76), "xss_a2": (295.92, 299.16),
               "xss_g2": (301.32, 303.48)}
    for f in ("W", "E"):
        rng.update(k["ranges"][f])
    rng.update({c["b"]: XR["b"], "rst_n": XR["rst_n"], "clk": XR["clk"], c["g0"]: XR["g0"], c["gp"]: XR["gp"]})
    s["pins"] = pins
    s["pin_ranges"] = {p: [lo, hi] for p, (lo, hi) in rng.items()}
    s["route"] = dict(base["route"], pin_balance={"group_max": 1, "h": "M4 M6", "v": "M5 M7"})
    st = f"physical/ref_tile_specs/smh/{name}_stations.tcl"
    (ROOT / st).write_text(stations(name, half, h))
    s["orfs_vars"] = {"OT_IO_REF_CLASS": "1", "POST_TAPCELL_TCL": st}
    s["reset_landing"] = {"enable": False, "reason": (
        "the RTL lands rst_n itself: ot_rp4h_rst u_rst = two KEPT face stages (l0, l1) then one KEPT copy per consumer "
        "(c[*], 1-12 loads each); the port net has ONE sink (u_rst.l0).  Depth 3 = the lp regional reset run, so the "
        "halves stay cycle-exact with ot_hbm_smh_rp4_flat_lp (bench H2_LOCKSTEP).")}
    s["pin_regs"] = {"enable": False, "reason": (
        "every data pin is registered in RTL: inputs rin (ot_rp4l_pinrow), bin (pinbeat), xs straps (5-stage strap), gin "
        "(u_gn u_v/u_d), xi_* (u_lands / u_xgi / u_xpi); outputs rout / bout launched by the hard row_e / beat_e flops, "
        "xo_* by u_xbo / u_xgo / u_xpo, gout by the u_gs output registers.  Recipe-3 pin registers would add cycles to "
        "the priced lp schedule.")}
    s["child_clock_ref"] = "boundary"
    other = "s" if half == "n" else "n"
    s["job"] = {
        "owner": "Claude LEAD2-HBM/L2H-SM9", "branch": "claude/l2h-sm9-1019", "tag": name.replace("smh_", ""),
        "purpose": ("HBM SM tile rp4, safe-design successor of smh_tile_rp4lp as two hardened halves (this kit = the "
                    f"{half} half, {k['desc']}); closure of the MATVEC tile body (template of the rp4a attention tile)."),
        "structural_change": (
            "smh_tile_rp4lp (457.92 x 1598.4, aspect 3.49, 13/18 macros off the 43.2 lattice, 2,069-b landing read select "
            "8,284 loads, gate1 GRT ovf 51,363, gate2 CTS rc 2) split along its lp region cut into two hardened halves "
            "(ot_hbm_smh_rp4h_n / _s) abutting in the SM frame slot: no landing (registered tile-to-tile crossing on the "
            "abutment face, judged per linked child-flop pair at die level), the two hard 216x43.2 land children replaced "
            "by soft kept landing registers (rl1 no longer crosses a macro), every macro on the 43.2 lattice, BF16 columns "
            "/ transpose re-oriented so operand inputs face the x store and sums face the transpose, one clock root per "
            f"half with clk on the abutment face beside the {other} half's.  Latency identical to the lp record (gout +3, "
            "all else 0)."),
        "extra_paths": ["tools/hbm_sm_repack_1015", "rtl/hbm_accel/sm/repack/h2", WIT],
        "benches": benches(k["params"].get("SOFTBEAT", 0))}
    return s


# SAFE2 (L2H-SM9/SAFE2 10-19 ~22:00): the four halves above FAILED the clock rule at CTS (gates 1749: one spine root, clk
# on the S/N abutment face at x 404, TT insertion ~2.1 ns, boundary pin-flop spread TT/FF n_a 209/163, n_b 236/216, s_a
# 196/174, s_b 200/179 ps > 80) and n_b GRT overflow 12,845 (M6 12,510) at the x store's W channel (x 0-43) and E end
# (x 302-345) around y 432-475: the closed xs view brings o_ix out on THREE faces (467 M4 pins on its W face 5.4/um, 146
# down, 175 up), so the W-face and the up-face o_ix wires all squeeze through the 41-um W channel beside the rin_n pin
# rows and the bin relays.  Successors (all children still on 43.2, pair heights 1,598.4, cycles unchanged):
#   clock: no spine; regional roots by k-means (physical/common_flow/clock_split_km.tcl, OT_CKKM_K = 32 / 64, each root
#     <= ~115 / 80 um across) under one CTS-balanced top tree, TritonCTS macro trees for the hard-child clock pins (lib
#     insertion), clk pin moved off the abutment corner (x 404) to the W face at the half's centre height;
#   n_b (cx): x store moved one lattice step E (x 86.4): its W channel 84 um (was 41) for the 467 W-face o_ix + rin_n
#     landing traffic, E channel 67 um; everything else as n_b;
#   hold: route.io_hold_margin_ns 0.03 (KITS 10-18 rule); the s-half landing regs stay at their pins (io_flop_at_pins)
#     and the big pre-repair FF hold (-140 ps on u_lands.q) came from the 200-ps spine spread the km roots remove.
CKKM = (32, 64)
CLK_W = {"smh_rp4hn_a1019": (553.5, 554.58), "smh_rp4hn_b1019": (471.42, 472.5),   # rin_n / bin gap (centre 453.6 / 432)
         "smh_rp4hs_a1019": (345.06, 346.14), "smh_rp4hs_b1019": (366.66, 367.74)}  # free W face below rin_s, at h / 2


def safe2_kits():
    out = {}
    for base, k in KITS.items():
        for K in CKKM:
            kk = dict(k, ckkm=K, clk_w=CLK_W[base], base=base)
            if base == "smh_rp4hn_b1019":
                kk["kids"] = [(v, i, 86.4 if i.endswith("u_xs") else x, y, o) for v, i, x, y, o in k["kids"]]
                kk["desc"] = k["desc"] + "; x store at x 86.4 (W channel 84 um)"
                tag = "cx"
            else:
                tag = ""
            out[base.replace("1019", f"_km{K}{tag}")] = kk
    return out


def safe2(s, name, k):
    """the SAFE2 clock / hold changes on top of spec()"""
    K = k["ckkm"]
    s["clock"] = "cts"
    s["pre_cts_extra"] = ["physical/common_flow/clock_split_km.tcl"]
    s["orfs_vars"]["OT_CKKM_K"] = str(K)
    s["orfs_vars"]["OT_CKKM_PORT"] = "clk"
    for f in ("N", "S"):
        if "clk" in s["pins"].get(f, []):
            s["pins"][f] = [p for p in s["pins"][f] if p != "clk"]
    s["pins"]["W"] = s["pins"]["W"] + ["clk"]
    s["pin_ranges"]["clk"] = list(k["clk_w"])
    s["route"] = dict(s["route"], io_hold_margin_ns=0.03)
    j = s["job"]
    j["tag"] = name.replace("smh_", "")
    j["structural_change"] += (
        f"  SAFE2 successor of {k['base']} (its gate failed the clock rule: one spine root from the abutment corner, TT "
        f"insertion ~2.1 ns, boundary pin-flop spread ~200 ps): regional k-means clock roots (clock_split_km.tcl K={K}, "
        "each root <= ~115 um across) under one balanced CTS top tree, hard-child clock pins on TritonCTS macro trees "
        "(lib insertion), clk entry moved to the W face at the half's centre height; io_hold_margin 0.03"
        + ("; x store moved to x 86.4 (W channel 41 -> 84 um: n_b GRT ovf 12,845 at the xs W channel / E end from its "
           "3-face o_ix pins)" if k["base"] == "smh_rp4hn_b1019" else "") + ".  Cycles unchanged.")
    return s


def main():
    base = json.loads(BASE.read_text())
    for name, k in safe2_kits().items():
        s = safe2(spec(name, k, base), name, k)
        kd = ROOT / "physical/ref_tile" / name
        kd.mkdir(parents=True, exist_ok=True)
        (kd / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        print(f"{kd / 'spec.json'}: {len(s['children'])} children, outline {W} x {k['h']}, K{k['ckkm']}")


def main_1019():
    base = json.loads(BASE.read_text())
    for name, k in KITS.items():
        s = spec(name, k, base)
        kd = ROOT / "physical/ref_tile" / name
        kd.mkdir(parents=True, exist_ok=True)
        (kd / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        print(f"{kd / 'spec.json'}: {len(s['children'])} children, outline {W} x {k['h']} (aspect {k['h'] / W:.2f})")


if __name__ == "__main__":
    main()
