#!/usr/bin/env python3
"""STEWARD-HBMe/SMH r9 (10-23): smh_attn halves rebuilt top-down from the frame slot + content.

Coordinator tile review 10-23 = BAD for smh_rp4ahn_r4sp / smh_rp6n_m / smh_rp8s_f (2.3-2.7x oversized, beat band 400 um
above the x store, 1.4 mm n->s beat crossing, empty W channel).  r9 keeps the r4 RTL (ot_hbm_smh_rp4ah_n/_s, the already
priced rp4ah record: GN 2 / GS 2 / XB 2 / LR 2, zero edge change) and changes placement only:
  * outline 777.6 x 864.0 (18 x 20 on the 43.2 child lattice) from content (0.383 mm2 hard+halo + glue) and the frame
    slot (half W-E = die-Y column pitch 869.4 - 43.2 ft row; n + s = 1728 of the 1939.68 die-X frame width);
  * children in two rows, pins toward their producer / consumer; beat band at the n|s seam;
  * pin-register face fences (beat W/E strips, beat band, rin/rout strips, N strap band) as INCLUSIVE regions at
    PRE_GLOBAL_PLACE, dissolved before DPL (r6/r7 fence mechanism).
MAIN (_m) = balanced clock spine (r4sp OT_SPINE_SYM insertion-aware settings); FB (_f) = same geometry, TritonCTS.
Writes physical/ref_tile_specs/smh/smh_rp9{n,s}_{m,f}.json + physical/hbm_smh_r9/fence_smh_rp9{n,s}.tcl.
"""
import copy, json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
W, H = 777.6, 864.0
VIEWS = {
    "merge": "physical/ref_tile/smh_pvm_ref_s4a/views/ot_hbm_sm_pv_merge_s3",
    "qk": "physical/ref_tile/smh_tct_ref_p45/views/ot_hbm_accel_smh_tct",
    "bdc": "physical/ref_tile/smh_bdc_ref_p50/views/ot_hbm_accel_smh_bdc",
    "tcl": "physical/ref_tile/smh_tcl_gu_ref/views/ot_hbm_accel_smh_tcl_gu",
    "xs": "physical/ref_tile/smh_xs_p192d_bay/views/ot_hbm_accel_smh_xs",
    "row": "physical/ref_tile/smh_tr_group_row_w_ref/views/ot_smh_tr_group_row_w",
    "rowe": "physical/ref_tile/smh_tr_group_row_e_ref/views/ot_smh_tr_group_row_e",
}
SIZE = {"merge": (345.6, 302.4), "qk": (194.4, 71.28), "bdc": (112.32, 142.56), "tcl": (86.4, 120.96),
        "xs": (475.2, 388.8), "row": (86.4, 90.72), "rowe": (43.2, 90.72)}
# (kind, inst suffix, at, orient) in half coordinates.  n: beat band at the S seam; s: mirrored (band at its N seam).
PLAN = {
    "n": [("merge", "u_lf0.g_lr.u_c.u_merge", (43.2, 518.4), "MX"),     # pins (N) down onto the operand glue band
          ("tcl", "u_lf0.g_lr.u_c.u_h0", (432.0, 518.4), "MX"),          # i_w/i_x down to xs, sum_o up to tct
          ("tcl", "u_lf0.g_lr.u_c.u_h1", (518.4, 518.4), "MX"),          # abutted (bare W/E faces)
          ("bdc", "u_lf0.g_lr.u_c.u_bdc", (604.8, 518.4), "R0"),         # i_w/i_x (S) down to xs; abutted to h1
          ("qk", "u_lf0.g_lr.u_c.u_qk", (432.0, 691.2), "R0"),           # R0 only (MX/R180 put 18 LEF pins off the tracks): sum_i on top, tcl sums wrap ~70 um
          ("xs", "u_lf0.g_lr.u_c.u_xs", (172.8, 86.4), "R0"),            # bk1 (S) onto the beat band, o_i* (N) up
          ("row", "u_row0", (43.2, 388.8), "R0"),                        # beside the rin pins / pinrow strip
          ("rowe", "u_rowe0", (691.2, 388.8), "R0")],                    # beside the rout pins
    "s": [("merge", "u_lf1.g_lr.u_c.u_merge", (43.2, 43.2), "R0"),       # pins (N) up onto the glue band
          ("tcl", "u_lf1.g_lr.u_c.u_h0", (432.0, 216.0), "R0"),          # i_w/i_x (N) up to xs, sum_o down to tct
          ("tcl", "u_lf1.g_lr.u_c.u_h1", (518.4, 216.0), "R0"),
          ("bdc", "u_lf1.g_lr.u_c.u_bdc", (604.8, 216.0), "MX"),         # i_w/i_x up to xs
          ("qk", "u_lf1.g_lr.u_c.u_qk", (432.0, 86.4), "R0"),            # sum_i (N) up onto the tcl sums
          ("xs", "u_lf1.g_lr.u_c.u_xs", (172.8, 388.8), "MX"),           # bk1 up onto the beat band at the N seam
          ("row", "u_row1", (43.2, 388.8), "R0"),
          ("rowe", "u_rowe1", (691.2, 388.8), "R0")],
}
PIN_RANGES = {
    "n": {"bin": [4.32, 388.8], "clk": [399.06, 400.14], "rin_n": [410.4, 626.4],
          "bout": [4.32, 388.8], "rout_n": [410.4, 626.4],
          "gin": [216.0, 248.4], "xs_a1": [250.56, 254.88], "xs_g1": [257.04, 259.2], "xs_a2": [261.36, 264.6],
          "xs_g2": [266.76, 268.92], "attn": [271.08, 273.24],
          "xo_b": [4.32, 410.4], "rst_n": [412.56, 413.64], "xo_g0": [604.8, 617.76], "xo_gp": [619.92, 650.16]},
    "s": {"clk": [334.26, 335.34], "rin_s": [345.6, 561.6], "rout_s": [345.6, 561.6],
          "gout": [604.8, 669.6], "xss_a1": [285.12, 289.44], "xss_g1": [291.6, 293.76], "xss_a2": [295.92, 299.16],
          "xss_g2": [301.32, 303.48], "attn": [305.64, 307.8],
          "xi_b": [4.32, 410.4], "rst_n": [412.56, 413.64], "xi_g0": [604.8, 617.76], "xi_gp": [619.92, 650.16]},
}
# face fences: (name, x0, y0, x1, y1, [top-level instances]); every other movable cell votes by netlist neighbours,
# leftovers -> "core" (the whole outline).
FENCES = {
    "n": [("wbeat", 0.0, 0.0, 43.2, 388.8, ["u_pb"]),
          ("ebeat", W - 43.2, 0.0, W, 388.8, ["g_sbeat.u_be2", "g_hbeat.u_beate"]),
          ("band", 0.0, 0.0, W, 86.4, ["g_sbeat.u_bt1", "g_sbeat.u_bt2", "g_sbeat.u_be1", "g_hbeat.u_beat_t", "u_landn", "u_xb1",
                                       "g_xb2.u_xb2", "g_xb3.u_xb3", "u_xbo", "u_xgo", "u_xpo", "u_rst"]),
          ("wrow", 0.0, 388.8, 43.2, 648.0, ["u_pr_n"]),
          ("nstrap", 0.0, H - 43.2, W, H, ["u_sr_n", "u_as_n", "u_gip"]),
          ("core", 0.0, 0.0, W, H, [])],
    "s": [("band", 0.0, H - 86.4, W, H, ["u_lands", "u_xgi", "u_xg2", "u_xpi", "u_xp2", "u_rst", "u_rp_land"]),
          ("wrow", 0.0, 302.4, 43.2, 604.8, ["u_pr_s"]),
          ("sgate", 561.6, 0.0, 734.4, 43.2, ["u_gs"]),
          ("sstrap", 0.0, 0.0, 432.0, 43.2, ["u_sr_s", "u_as_s"]),
          ("core", 0.0, 0.0, W, H, [])],
}

def check(half):
    boxes = []
    for kind, inst, (x, y), o in PLAN[half]:
        w, h = SIZE[kind]
        assert abs(x / 43.2 - round(x / 43.2)) < 1e-6 and abs(y / 43.2 - round(y / 43.2)) < 1e-6, (inst, x, y)
        boxes.append((inst, kind, x, y, x + w, y + h))
        assert x >= 21.6 and y >= 21.6 - 1e-6 or kind in ("merge",), inst
        assert x + w <= W - 21.6 + 1e-6 and y + h <= H - 21.6 + 1e-6, (inst, x + w, y + h)
    bare = {"tcl", "bdc"}                             # W/E faces carry no pins (LEF): abutted rows legal
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            dx = max(b[2] - a[4], a[2] - b[4]); dy = max(b[3] - a[5], a[3] - b[5])
            gap = max(dx, dy)
            assert gap >= 0, ("overlap", a[0], b[0])
            if gap < 20 - 1e-6:
                assert gap == 0 and dy < 0 and a[1] in bare and b[1] in bare, ("channel", a[0], b[0], gap)
    hard = sum(SIZE[k][0] * SIZE[k][1] for k, *_ in PLAN[half])
    return hard

def fence_tcl(half):
    src = open(os.path.join(ROOT, "physical/hbm_smh_r7/fence_smh_rp7s_m.tcl")).read()
    body = src[src.index("set ot_r6_blk [ord::get_db_block]"):]
    old = """  set top [lindex [split $n "./"] 0]
  if {[dict exists $ot_r6_map $top]} {
    dict set ot_r6_reg $i [dict get $ot_r6_map $top]; incr ot_r6_named"""
    new = """  set parts [split $n "./"]
  set top [lindex $parts 0]
  set top2 "$top.[lindex $parts 1]"
  if {[dict exists $ot_r6_map $top2]} {
    dict set ot_r6_reg $i [dict get $ot_r6_map $top2]; incr ot_r6_named
  } elseif {[dict exists $ot_r6_map $top]} {
    dict set ot_r6_reg $i [dict get $ot_r6_map $top]; incr ot_r6_named"""
    assert old in body
    body = body.replace(old, new)
    bands = " ".join("{%s %.2f %.2f %.2f %.2f}" % (n, x0, y0, x1, y1) for n, x0, y0, x1, y1, _ in FENCES[half])
    m = []
    for n, *_r, insts in FENCES[half]:
        for i in insts:
            m += [i, n]
    hdr = ("# GENERATED by tools/hbm_smh_r9/make_r9.py (STEWARD-HBMe/SMH r9 %s half): pin-register face fences.\n"
           "# PRE_GLOBAL_PLACE (pin_hook_before_flops): one INCLUSIVE region + group per face band; named top-level\n"
           "# instances join their band, other cells by neighbour vote, leftovers -> core.  Dissolved before DPL by\n"
           "# physical/hbm_smh_r7/fence_dissolve.tcl (r6_* names kept so the dissolver finds them).  Placement only.\n" % half)
    return hdr + "set ot_r6_bands {%s}\nset ot_r6_default core\nset ot_r6_map [dict create %s]\n" % (bands, " ".join(m)) + body

def main():
    base = {"n": json.load(open(os.path.join(ROOT, "physical/ref_tile_specs/smh/r9_base_n.json"))),
            "s": json.load(open(os.path.join(ROOT, "physical/ref_tile_specs/smh/r9_base_s.json")))}
    for half in ("n", "s"):
        hard = check(half)
        fence = "physical/hbm_smh_r9/fence_smh_rp9%s.tcl" % half
        open(os.path.join(ROOT, fence), "w").write(fence_tcl(half))
        for var in ("m", "f"):
            s = copy.deepcopy(base[half])
            name = "smh_rp9%s_%s" % (half, var)
            s["name"] = name
            s["outline"] = {"w": W, "h": H}
            s["children"] = [{"view": VIEWS[k], "count": 1, "at": list(at), "orient": o, "inst": inst}
                             for k, inst, at, o in PLAN[half]]
            pins = copy.deepcopy(s["pins"])
            if half == "n":
                s["pins"] = {"W": ["bin", "clk", "rin_n"], "E": ["bout", "rout_n"],
                             "N": ["gin", "xs_a1", "xs_g1", "xs_a2", "xs_g2", "attn"],
                             "S": ["xo_b", "rst_n", "xo_g0", "xo_gp"]}
            else:
                s["pins"] = {"W": ["clk", "rin_s"], "E": ["rout_s"],
                             "S": ["xss_a1", "xss_g1", "xss_a2", "xss_g2", "attn", "gout"],
                             "N": ["xi_b", "rst_n", "xi_g0", "xi_gp"]}
            assert sorted(sum(pins.values(), [])) == sorted(sum(s["pins"].values(), [])), (name, pins, s["pins"])
            s["pin_ranges"] = PIN_RANGES[half]
            ov = dict(s.get("orfs_vars") or {})
            ov.pop("POST_TAPCELL_TCL", None)          # r3a FIRM relay stations belong to the 1.5-mm geometry
            if var == "f":
                for k in [k for k in ov if k.startswith("OT_SPINE")]:
                    ov.pop(k)
                s["clock"] = "cts"
            s["orfs_vars"] = ov
            s["pin_hook_before_flops"] = [fence]
            s["pre_dpl_extra"] = ["physical/hbm_smh_r7/fence_dissolve.tcl"]
            s["low_fill_reason"] = ("macro-bound parent: 8 hard children 0.352 mm2 (0.383 with halos) set the outline; "
                                    "xs 475x389 + merge 346x302 cannot stack below 864 um inside the 826-um frame "
                                    "column pitch; soft glue is ~31k (n) / 18.5k (s) um2 incl. buffers")
            s["job"] = {"owner": "Claude:STEWARD-HBMe/SMH", "branch": "claude/hbme-smh-1023", "tag": name,
                        "purpose": "r9 %s: smh_attn %s half rebuilt top-down (coordinator BAD 10-23), r4 RTL, 0 edges"
                                   % ("MAIN (spine)" if var == "m" else "FB (TritonCTS)", half),
                        "extra_paths": ["tools/hbm_sm_repack_1015", "rtl/hbm_accel/sm/repack/h2",
                                        "rtl/hbm_accel/sm/repack/h2a", "results/arch/hbm_smatt10_1020/bench",
                                        "physical/ref_tile/smh_xs_p192d_bay/views", "physical/hbm_smh_r9",
                                        "physical/hbm_smh_r7", "tools/hbm_smh_r9"]}
            s["structural_change"] = ("r9 (STEWARD-HBMe/SMH 10-23): outline %.1fx%.1f from content+frame slot (was %sx%s), "
                                      "children in two rows oriented pins->consumer, beat band at the n|s seam, pin-register "
                                      "face fences; r4 RTL + params unchanged (0 edges); r3a relay stations dropped."
                                      % (W, H, base[half]["outline"]["w"], base[half]["outline"]["h"]))
            s["safe_design_checklist"] = {
                "1_pins": "every data pin lands in an RTL register (pinbeat / pinrow / straps / xreg) fenced at its face band",
                "2_reach": "beat n->s crossing ~100 um (was 1.4 mm); merge -> gather S pins ~700 um over GN relays",
                "3_fanout": "r4 RTL kept copies; native census <= 32 must pass before layout",
                "4_depth": "RTL unchanged",
                "5_storage": "hard SRAM children unchanged",
                "6_floorplan": "outline %.0f%% of r4, two child rows, 21.6/43.2 margins, abutted bare-face tcl/bdc" %
                               (100 * W * H / (base[half]["outline"]["w"] * base[half]["outline"]["h"])),
                "7_clock": "one clk root over 0.67 mm2; child refs 113-485 TT need insertion-aware leaves (MAIN spine / FB CTS)",
                "8_schedule": "static; zero edge change vs the rp4ah record"}
            s.pop("gate_result", None)
            out = os.path.join(ROOT, "physical/ref_tile_specs/smh/%s.json" % name)
            json.dump(s, open(out, "w"), indent=1)
            print(name, "hard %.0f um2 = %.1f%% of outline" % (hard, 100 * hard / (W * H)), out)

if __name__ == "__main__":
    main()
