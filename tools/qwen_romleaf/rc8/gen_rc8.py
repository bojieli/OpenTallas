"""QW-A0-RC4 (10-20): rc8 / rc8b kits for the A0 ROM-leaf parents (NK, NL) = rc7 / rc7b floorplans + REGROOT 8 RTL.

REGROOT 8 (rtl/hdc/ot_qwen_w12_matvec.sv, ot_qwen_rom_tile_w12.sv): PRE-GATE NATIVE CENSUS fix (rc7 mapped census:
NK 103 / NL 104 drivers > 32 loads, max 262 / 291): 26 kept go copies, 30 descriptor load groups with kept idle copies,
21 loop-field chunk groups, twin split copies (90), per-group ts / wcs / group-index copies; rc7 gate cross-clock
fixes: raw rung-0 capture with the BF16 round + mask after rung 0, leaf fault pins landed on clk.  0 data cycles.
Kit: reset landing last stage 16 kept copies (rc7: 8 -> NL copy c6 34 loads); land_fault also claims the leaf fault
landing (FREE).  rc8b additionally boxes the engine's input register stage (go_q / go copies / ib_q / xl_q, clock ck)
in the east channel beside the tap pins (rc7 gates: tap_q ck_fa4 -> ib_q / xl_q ck crossing 177-207 endpoints
-85..-155 ps over ~385 um): the crossing becomes a short register -> register hop, ib -> hub a same-clock wire.
"""
import json, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "rc3"))
import gen_rc3 as g3                                   # noqa: E402
ROOT = g3.ROOT

LAND_IB = (784.0, 86.4, 816.0, 820.8)   # east channel (ROM1 right edge 777.6 .. outline 820.8), tap pin span


def make(nk, rev):
    base = {"rc8": "rc7", "rc8b": "rc7b"}[rev]
    kit7, s, ptcl, rtcl = g3.make(nk, base)
    kit = kit7.replace(base, rev)
    s = json.loads(json.dumps(s).replace(kit7, kit))
    s["params"]["REGROOT_MODE"] = 8
    s["reset_landing"]["copies"] = {"rst_n": 16}
    s["io_tcl"] = f"tools/qwen_romleaf/rc8/{kit}_pins.tcl"
    s["pin_hook_before_flops"] = [f"tools/qwen_romleaf/rc8/{kit}_regions.tcl"]
    rtcl = rtcl.replace(kit7, kit).replace("gen_rc3.py (QW-A0-RC3 10-19)", "rc8/gen_rc8.py via gen_rc3.py (QW-A0-RC4 10-20)")
    old_fault = "  [dict create name land_fault type FREE regex {u_me\\.fault_q\\[} boxes {} min 0 max 100] \\"
    assert old_fault in rtcl
    rtcl = rtcl.replace(old_fault, "  [dict create name land_fault type FREE regex {u_me\\.(fault_q\\[|g_hier\\.g_sl\\[[0-7]\\]\\.g_hd\\.g_fl\\.q)} boxes {} min 0 max 200] \\")
    if rev == "rc8b":
        hub = "  [dict create name hub type EXCLUSIVE"
        assert hub in rtcl
        land = ("  [dict create name land_ib type EXCLUSIVE regex {u_tile\\.u_tile\\.u_logic\\.(go_[iq]|ib_[iq]|xl_q|u_xm\\.d\\[|g_gocp\\.g_c)} "
                "boxes {{%.3f %.3f %.3f %.3f}} min 1 max 100000] \\\n" % LAND_IB)
        rtcl = rtcl.replace(hub, land + hub)
    ptcl = ptcl.replace(kit7, kit)
    sc = (f"QW-A0-RC4 {rev} (10-20): {base} floorplan + REGROOT 8 RTL (PRE-GATE NATIVE CENSUS: kept go / idle / loop-chunk / "
          "split-twin / ts-wcs / group-index copies, no driver > 32 loads; raw rung-0 capture + per-leaf round/mask after "
          "rung 0; leaf fault pins landed on clk), 0 data cycles; kit reset landing 16 last-stage copies"
          + ("; engine input registers boxed beside the E tap pins (ck_fa4 -> ck crossing a short hop)" if rev == "rc8b" else "") + ".")
    s["structural_change"] = sc
    j = s["job"]
    j["owner"] = "Claude:QW-A0-RC4"; j["branch"] = "claude/qw-a0-rc4-1020"; j["tag"] = rev
    j["purpose"] = sc
    ep = set(j.get("extra_paths", [])) | {"tools/qwen_romleaf", "tools/qwen_a0_safe", "rtl/test/tb_qwen_a0_rr8.sv"}
    j["extra_paths"] = sorted(ep)
    return kit, s, ptcl, rtcl


if __name__ == "__main__":
    out = ROOT / "tools/ref_tile/specs_qw_a0_rc4_1020"
    out.mkdir(exist_ok=True)
    for rev in sys.argv[1:] or ("rc8", "rc8b"):
        for nk in (True, False):
            kit, s, ptcl, rtcl = make(nk, rev)
            (out / f"{kit}.json").write_text(json.dumps(s, indent=1) + "\n")
            (HERE / f"{kit}_pins.tcl").write_text(ptcl)
            (HERE / f"{kit}_regions.tcl").write_text(rtcl)
            print("GEN", kit)
