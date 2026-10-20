#!/usr/bin/env python3
"""QW-A0-RC3 (10-19) rc3 / rc3b region plan for the A0 ROM-leaf parents qfd_tile_n{k,l}_romleaf.

Why rc1/rc2 failed (DPL-0033 in all four region gates; the placer-free rc1f legalized):
  the EXCLUSIVE (DEF FENCE) boxes tiled every std-cell corridor SOLID: west ROM channel = rsw|dw|rnw over its full width,
  east channel = rse|de|rne, central column = tx0-3 | hub | tx4-7 wall to wall.  Only the registers are group members;
  the combinational cones, the repair_design wire/slew buffers (e.g. g_sl[4].g_tx.g_r[1].u_tx/wire*) and, in NK, the
  n_a/n_b/n_y bus buffers on the W-pin -> node path are NOT members and may not sit inside a fence, so they had no legal
  rows near their drivers: NL 1726 / NK 8061 cells stuck (placed-in-rows / overlap with tapcells).  Fence fill was only
  3-8 % (registers 133..899 um2 in 3.8k..39k um2): area was never the problem, the missing free lane was.
rc3 (structural): every fence is a SUB-LANE on the pin side of its corridor (ROM pin face, LSL pin face, hub centre) and
  every corridor keeps >= ~50 % free rows contiguous with the fence for the non-member cells and repair buffers:
    west channel 216.0-259.2: fence 216.4-231.6 (rsw/dw/rnw), free 231.6-258.8
    east channel 575.0-604.8: fence 589.6-604.4 (rse/de/rne), free 575.4-589.6
    central 359.0-475.2:      tx0-3 359.4-373.8 | free 373.8-395 | hub 395-439 | free 439-460.8 | tx4-7 460.8-474.8
  Macros, outline (820.8 x 907.2), pins and RTL (REGROOT 7) are exactly rc2's: the reach plan (node 388.8 um from the W
  pins, hub <= 385 um from the E tap pins) forbids a wider outline.
rc3b (parallel variant, same channels): a COMPACT hub box (NL 392-442 x 216-691.2; NK 392-442 x 172.8-426) instead of
  the full-height / full-lower column: shorter ck root span (the rc1f no-region ck spread was 535.8 ps NL) and shorter
  canonical-next-state -> copy nets; more free rows above/below the hub.
  The 'hub across the bottom band' idea was rejected: hub copies feed the ROM request relays up to y 860 and the LSL
  rows up to y 788 -> 650-800 um from a bottom band (> 405 um reach), it would need relays (cycles) on the issue path.
Writes tools/ref_tile/specs_qw_cluster3_1019/<kit>.json, tools/qwen_romleaf/rc3/<kit>_{pins,regions}.tcl.
"""
import json, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "rc1"))
import gen_rc1 as g1                                   # noqa: E402  (macros, pins, base spec: identical to rc2)
ROOT = g1.ROOT
H = g1.H

# corridor x-extents (um)
ROM0_R = g1.ROM0_X + g1.ROM_W                          # 216.0
LSLA_R = g1.LSLA_X + g1.LSL_W                          # 358.992
LSLB_R = g1.LSLB_X + g1.LSL_W                          # 574.992
FENCE = dict(
    west=(ROM0_R + 0.4, 231.6),                        # rsw / dw / rnw   (ROM 0 pin face side)
    east=(589.6, g1.ROM1_X - 0.4),                     # rse / de / rne   (ROM 1 pin face side)
    txa=(LSLA_R + 0.4, 373.8),                         # tx0..3           (LSLA pin face, R0 pins E)
    txb=(460.8, g1.LSLB_X - 0.4),                      # tx4..7           (LSLB pin face, MY pins W)
)
HUB = {  # (x0, y0, x1, y1)
    ("rc3", True): (395.0, 8.0, 439.0, g1.NODE_Y - 6.0),
    ("rc3", False): (395.0, 8.0, 439.0, H - 54.0),
    ("rc3b", True): (392.0, 172.8, 442.0, g1.NODE_Y - 6.0),
    ("rc3b", False): (392.0, 216.0, 442.0, 691.2),
    # rc4 (after rc3/rc3b CTS): the ck H-tree over a tall narrow hub (NL 44x845 -> spread 193.3 ps, 50x475 -> 147.6 ps;
    # CTS sink region 39 x 350 normalized) fails the 80 ps rule -> a square-ish hub (<= 2:1) at the column centre.
    ("rc4", True): (382.0, 286.0, 452.0, 426.0),          # 70 x 140, under the node
    ("rc4", False): (382.0, 380.0, 452.0, 520.0),         # 70 x 140, tile centre
    ("rc4b", True): (377.4, 316.0, 457.4, 426.0),         # 80 x 110 (1.4:1), comb above/below
    ("rc4b", False): (377.4, 395.0, 457.4, 505.0),
    # rc5 (after rc4: 2 / 1 buffers stuck on tapcells in the 8 / 3.5 um lanes beside the wide hub): keep rc3's 21 um
    # lanes AND <= 2:1 aspect -> hub 44 x 88 (rc5) / 52 x 100 (rc5b, 17 um lanes).  Register fill 25 % / 18 %.
    ("rc5", True): (395.0, 338.0, 439.0, 426.0),
    ("rc5", False): (395.0, 406.0, 439.0, 494.0),
    ("rc5b", True): (391.0, 326.0, 443.0, 426.0),
    ("rc5b", False): (391.0, 400.0, 443.0, 500.0),
    # rc6 (after NK rc4: DPL PASS, ck 76.7 ps PASS, ck_tx0 84.2 ps FAIL): the FREE TX rung-0 landings spread ck_tx0 over
    # x 233-441 (drivers in dw + hub, 389 of 845 sinks).  Every rung-0 driver is <= ~250 um from its tx fence in this
    # floorplan, so rung 0 joins its tx fence (one reg -> wire -> reg hop from dw/hub, <= 405 um); hub boxes as rc5/rc5b.
    ("rc6", True): (395.0, 338.0, 439.0, 426.0),
    ("rc6", False): (395.0, 406.0, 439.0, 494.0),
    ("rc6b", True): (391.0, 326.0, 443.0, 426.0),
    ("rc6b", False): (391.0, 400.0, 443.0, 500.0),
    # rc7 (after rc6: every root PASS but ck_fa4: NK 241.8 / NL 282.2 ps): the kit reset landing ran on ck_fa4, so its
    # last-stage copies (placed at their loads beside the hub, 370 um from the E pins) joined the 287 compact E-face pin
    # flops on one tree.  The landing moves to ck (the hub root, whose loads it serves); ck_fa4 keeps only tap/tile_id/go.
    ("rc7", True): (395.0, 338.0, 439.0, 426.0),
    ("rc7", False): (395.0, 406.0, 439.0, 494.0),
    ("rc7b", True): (391.0, 326.0, 443.0, 426.0),
    ("rc7b", False): (391.0, 400.0, 443.0, 500.0),
}
LO = "([0-9]|[1-9][0-9]|[1-4][0-9][0-9]|50[0-9]|51[01])"


def boxes(rev, nk):
    """name -> (x0, y0, x1, y1) for every EXCLUSIVE fence"""
    b = {}
    for g in range(8):
        x0, x1 = FENCE["txa"] if g < 4 else FENCE["txb"]
        y0 = g1.LSL_Y[g % 4]
        b[f"tx{g}"] = (x0, y0, x1, y0 + g1.LSL_H)
    for side, (x0, x1) in (("w", FENCE["west"]), ("e", FENCE["east"])):
        b[f"rs{side}"] = (x0, 40.0, x1, 300.0)
        b[f"d{side}"] = (x0, 300.0, x1, 560.0)
        b[f"rn{side}"] = (x0, 560.0, x1, 860.0)
    b["hub"] = HUB[(rev, nk)]
    return b


def regions_tcl(kit, rev, nk):
    b = boxes(rev, nk)
    fmt = lambda r: "{%.3f %.3f %.3f %.3f}" % r
    rung = "[01]" if rev.rstrip("b") in ("rc6", "rc7") else "1"
    tx = [f"  [dict create name tx{g} type EXCLUSIVE regex {{g_sl\\[{g}\\]\\.g_hd\\.(g_tx\\.g_r\\[{rung}\\]\\.u_tx/|g_lrr\\.rq|g_outland\\.q)}} "
          f"boxes {{{fmt(b[f'tx{g}'])}}} min 1 max 100000] \\" for g in range(8)]
    lines = [
        *([] if rev.rstrip("b") in ("rc6", "rc7") else ["  [dict create name land_tx type FREE regex {g_hd\\.g_tx\\.g_r\\[0\\]\\.u_tx/} boxes {} min 1 max 100000] \\"]),
        "  [dict create name land_rq type FREE regex {g_rom_pipe\\.rq_(ce|ad)_[sn]\\[1\\]\\[} boxes {} min 1 max 100000] \\",
        "  [dict create name land_fault type FREE regex {u_me\\.fault_q\\[} boxes {} min 0 max 100] \\",
        *tx,
        f"  [dict create name rsw type EXCLUSIVE regex {{(g_rqr\\.(genblk[0-9]+\\.g_col_roots\\.gs|gs_q)\\[{LO}\\]|g_rph\\.g_rb\\[[0-2]\\]\\.g_single\\.g_col\\[0\\]\\.g_lrr\\.rq)}} boxes {{{fmt(b['rsw'])}}} min 1 max 100000] \\",
        f"  [dict create name rnw type EXCLUSIVE regex {{(g_rqr\\.(genblk[0-9]+\\.g_col_roots\\.gn|gn_q)\\[{LO}\\]|g_rph\\.g_rb\\[[34]\\]\\.g_single\\.g_col\\[0\\]\\.g_lrr\\.rq)}} boxes {{{fmt(b['rnw'])}}} min 1 max 100000] \\",
        f"  [dict create name rse type EXCLUSIVE regex {{(g_rqr\\.(genblk[0-9]+\\.g_col_roots\\.gs|gs_q)\\[|g_rph\\.g_rb\\[[0-2]\\]\\.g_single\\.g_col\\[1\\]\\.g_lrr\\.rq)}} boxes {{{fmt(b['rse'])}}} min 1 max 100000] \\",
        f"  [dict create name rne type EXCLUSIVE regex {{(g_rqr\\.(genblk[0-9]+\\.g_col_roots\\.gn|gn_q)\\[|g_rph\\.g_rb\\[[34]\\]\\.g_single\\.g_col\\[1\\]\\.g_lrr\\.rq)}} boxes {{{fmt(b['rne'])}}} min 1 max 100000] \\",
        f"  [dict create name dw type EXCLUSIVE regex {{(u_me\\.g_operand_rr\\.g_lsel\\.s1b_(wsrc_w|gm_w\\[)|u_me\\.g_operand_rr\\.g_csel\\.(wsrc_q|gm_q)\\[([0-9]|1[0-5])\\]|u_me\\.mq_wrom\\[{LO}\\]|g_hd\\.g_tx\\.tc\\[(12[89]|1[3-9][0-9]|2[0-4][0-9]|25[0-5])\\])}} boxes {{{fmt(b['dw'])}}} min 1 max 100000] \\",
        f"  [dict create name de type EXCLUSIVE regex {{(u_me\\.g_operand_rr\\.g_lsel\\.s1b_(wsrc_e|gm_e\\[)|u_me\\.g_operand_rr\\.g_csel\\.(wsrc_q|gm_q)\\[|u_me\\.mq_wrom\\[|g_hd\\.g_tx\\.tc\\[(25[6-9]|2[6-9][0-9]|3[0-7][0-9]|38[0-3])\\])}} boxes {{{fmt(b['de'])}}} min 1 max 100000] \\",
        *([] if rev in ("rc3", "rc3b") else [
        "  [dict create name land_top type FREE regex {^(u_ot_pr_core\\.)?u_g\\.u_tile\\.(n_va|fault_q)\\$} boxes {} min 0 max 4] \\"]),
        f"  [dict create name hub type EXCLUSIVE regex {{^(u_ot_pr_core\\.)?u_g\\.u_tile\\.}} boxes {{{fmt(b['hub'])}}} min 1 max 100000] \\",
    ]
    hdr = [f"# {kit}: generated by tools/qwen_romleaf/rc3/gen_rc3.py (QW-A0-RC3 10-19).  Same groups/regexes as rc2; every",
           "# EXCLUSIVE fence is a sub-lane on the pin side of its corridor and each corridor keeps a free lane for the",
           "# non-member combinational cells and repair buffers (rc1/rc2 tiled the corridors solid -> DPL-0033).",
           "# Area/lane check: tools/qwen_romleaf/rc3/check_region_area.py.",
           "set qrl_groups [list \\"]
    return "\n".join(hdr + lines + ["]", "source /src/tools/qwen_romleaf/parent_regions.tcl", ""])


def make(nk, rev):
    kit, s, ptcl, _ = g1.spec(nk, False, rev, 7)
    s["io_tcl"] = f"tools/qwen_romleaf/rc3/{kit}_pins.tcl"
    if rev.rstrip("b") == "rc7":
        s["reset_landing"]["clock"] = "ck"
    s["pin_hook_before_flops"] = [f"tools/qwen_romleaf/rc3/{kit}_regions.tcl"]
    hubtxt = {"rc3": "hub column 395-439", "rc3b": "compact hub box", "rc4": "square-ish 70x140 hub box (ck H-tree spread)",
              "rc4b": "80x110 hub box (ck H-tree spread)", "rc5": "44x88 hub box, 21 um lanes (ck spread + lanes)",
              "rc5b": "52x100 hub box, 17 um lanes (ck spread + lanes)",
              "rc6": "44x88 hub box + TX rung 0 inside its tx fence (ck_tx spread)",
              "rc6b": "52x100 hub box + TX rung 0 inside its tx fence (ck_tx spread)",
              "rc7": "rc6 + kit reset landing on ck instead of ck_fa4 (ck_fa4 spread)",
              "rc7b": "rc6b + kit reset landing on ck instead of ck_fa4 (ck_fa4 spread)"}[rev] + (" under the node" if nk else "") + \
             ("" if rev in ("rc3", "rc3b") else "; u_g.u_tile.n_va/fault_q pin-side flops FREE (rc3 NK DPL-0008 n_va)")
    s["structural_change"] = (f"QW-A0-RC3 {rev} (10-19, after rc1/rc2 DPL-0033): fences are pin-side sub-lanes with a "
        f"free lane in every corridor for the non-member comb/repair cells ({hubtxt}); REGROOT 7 RTL, 820.8 x 907.2 "
        "outline, macros and pins unchanged from rc2 (43.2 lattice, pins <=5.2/um); kit reset landing 2 stages ck_fa4.")
    j = s["job"]
    j["owner"] = "Claude:QW-A0-RC3"
    j["purpose"] = s["structural_change"]
    ptcl = ptcl.replace("rc1/gen_rc1.py (QW-CLUSTER3/A0 10-19 rc1", f"rc1/gen_rc1.py via rc3/gen_rc3.py ({rev}, same as rc1/rc2")
    return kit, s, ptcl, regions_tcl(kit, rev, nk)


if __name__ == "__main__":
    for rev in sys.argv[1:] or ("rc3", "rc3b"):
        for nk in (True, False):
            kit, s, ptcl, rtcl = make(nk, rev)
            (ROOT / f"tools/ref_tile/specs_qw_cluster3_1019/{kit}.json").write_text(json.dumps(s, indent=1) + "\n")
            (HERE / f"{kit}_pins.tcl").write_text(ptcl)
            (HERE / f"{kit}_regions.tcl").write_text(rtcl)
            print("GEN", kit)
