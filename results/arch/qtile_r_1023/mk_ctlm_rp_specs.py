#!/usr/bin/env python3
"""QTILE-R 10-23: re-packed HP13 cpub39 tt_ctlm kits (COORD tile review: 864x562 / 9.9% fill / logic smeared through
macro channels / 1,046 unregistered pins).  Outline from content: macros (135.5k um2) packed as TWO abutted N-S columns at
the NE (pins on the column W/E edges face the mid channel / the W core / the E strip), ONE L-shaped logic core along the
pin-dense W (1,779 pins) and S (766 pins) faces, a mid channel and E strip that open into the S core, an N band >= 20 um.
MAIN: W core 64.8, S core 43.2, mid 33.9 (466.56 x 503.28 = 234.8k um2).  ALT: W core 86.4, S core 54, mid 45 (wider
channels, 498.96 x 514.08 = 256.5k um2).  Every face pin is registered in RTL (*_pr: +1 cycle on 15 ports)."""
import copy, json, os, sys
R = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(R, "../../.."))
base = json.load(open(f"{ROOT}/physical/ref_tile/qfd_hp13_cpub39_full_main/spec.json"))
SR = "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2"; RB = "physical/asap7_memory_macros/ot_rom_4096x266_m8"
RS = "physical/asap7_memory_macros/ot_rom_4096x72_m8"; SS = "physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1"
P_SR, P_RB, P_RS, P_SS = 77.808, 62.928, 62.928, 20.832     # abutted N-S pitch on the 0.048-um y track lattice (gap 0.048 / 0.018 / 0.018 / 0.042 <= ABUT_UM)
W_SR, W_SS, W_RS = 171.288, 51.408, 38.016

def snap(v, g=2.16):
    import math
    return round(math.ceil(v / g - 1e-9) * g, 4)

def macros(xa, xb, y0):
    m = []
    def add(view, inst, x, y): m.append({"view": view, "count": 1, "inst": inst, "at": [round(x, 4), round(y, 4)], "orient": "R0", "at_exact": True})
    for k, inst in enumerate([f"u_gi.u_cal.g_fifo[{i}].u_fifo" for i in range(4)]):
        add(SR, inst, xa, y0 + k * P_SR)
    yt = y0 + 4 * P_SR
    add(RB, "u_gi.u_cal.g_calrom.u_rom.m0", xa, yt); add(RB, "u_gi.u_cal.g_calrom.u_rom.m1", xa, yt + P_RB)
    for k, inst in enumerate(["u_gi.u_cal.g_m[0].u_pm", "u_gi.u_cal.g_m[1].u_pm", "u_hr.u_24525", "u_hr.u_24526"]):
        add(SR, inst, xb, y0 + k * P_SR)
    for j in range(6):
        add(SS, f"u_hr.u_{24527 + j}", xb, yt + j * P_SS)
    xr = snap(xb + W_SS + 21.6)
    add(RS, "u_gi.g_op.u_leaf.g_op.g_banked.u_rom1", xr, yt); add(RS, "u_gi.g_op.u_leaf.g_op.g_banked.u_rom2", xr, yt + P_RS)
    add(RS, "u_gi.g_op.u_leaf.g_op.u_rom", snap(xr + W_RS + 21.6), yt)
    return m

def spec(name, wc, sb, mid, estrip, tag):
    s = copy.deepcopy(base)
    xa = wc; xb = snap(xa + W_SR + mid); w = snap(max(xb + W_SR, xb + W_SS + 21.6 + W_RS + 21.6 + W_RS + 2.0) + estrip)
    h = snap(sb + 4 * P_SR + 2 * P_RB + 22.2)
    s["name"] = name
    # r3/r4 (gate 02:28 FAIL both: ck_core boundary pin-flop spread 187.8 / 215.7 ps > 80 TT; core-domain pins sat on all four
    # faces): every ck_core-domain port joins tl / rst_n / ck_core on the W face, so the core pin flops form one face group
    core = set(s["clock_entry_domains"]["core"]["inputs"] + s["clock_entry_domains"]["core"]["outputs"])
    # r4 (STEWARD-QKd 02:40: move only toward the die partners): in the r56 die (pin_align.json) the partners of pw
    # (landh_75_NW), dh_user (sys_face_mu_dhobs), emb_start/token/position/user (landh0_*) all sit N of the tile
    # (y 22,098-22,283 vs tile N edge 22,086); tl's partner (rlyh0_1088_WE) sits S.  So the 98 small core pins plus
    # emb_token join the N face (listed first = the NW end, next to ck_core / rst_n at the W face's N end); tl stays W.
    small = sorted(p for p in core if p not in ("tl", "rst_n"))
    for fc in ("S", "E", "W"):
        s["pins"][fc] = [p for p in s["pins"][fc] if p not in small]
    s["pins"]["N"] = small + [p for p in s["pins"]["N"] if p not in small]
    s["top"] = "qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1_pr"
    srcs = [x for x in s["sources"] if "cpub39_1_physical.sv" not in x and "qfd_tt_ctlm_dv_wtn.sv" not in x]
    s["sources"] = ["rtl/qwen_dv/headprep13/physical_abi/qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1_physical_wtnbal24_pr.sv"] + srcs + [
        "rtl/qwen_dv/headprep13/wtn_balanced24/helpers.sv", "rtl/qwen_dv/headprep13/wtn_balanced24/qfd_tt_ctlm_dv_wtn_balanced24.sv"]
    s["outline"] = {"w": w, "h": h}
    s["std_area_um2"] = 43100.0   # full_main synth 42,714 + 1,144 pin-reg flops
    s["macros"] = macros(xa, xb, sb)
    s["fill_reason"] = {"macro_bound": f"19 authentic macros (135.5k um2) in two abutted N-S columns at the NE; outline from content "
                        f"{w} x {h} um (was 864 x 561.6): W core {wc}, S core {sb}, mid channel {round(xb - xa - W_SR, 2)}, E strip >= {estrip}"}
    s["pin_regs"] = {"enable": False, "reason": "RTL registers every data pin: QTILE-R *_pr top (tools/qwen_split/hp13_pinreg_top.py) adds one keep "
                     "flop per bit on the 15 ports whose bits were not flop-direct in the synthesized netlist (727 in + 417 out bits, +1 cycle "
                     "each, rtl/.../_pr.sv.pin_regs.json); the other ports were already flop-direct (census results/arch/qtile_r_1023)"}
    s["structural_change"] = ("QTILE-R re-pack (COORD tile review 10-23 BAD: 864x562, 9.9% fill, logic in macro channels, 1,046 unregistered pins): "
                              "outline from content, macros as two abutted N-S columns at the NE with their W/E pin edges facing the W core / "
                              "mid channel / E strip, one L logic core on the pin-dense W and S faces, face pin registers in RTL (+1 cycle on 15 ports); "
                              "core = Codex wtnbal24 (f160a99d3, same function, passes the native census that the cpub39_1 full kit failed)")
    c = s["safe_design_checklist"]
    c["1_pins"] = "Every data pin registered: 15 ports +1 cycle (pin_regs.json), the rest already flop-direct; io_flop_at_pins anchors them."
    c["6_floorplan"] = f"Outline from content {w} x {h}; 2 abutted macro columns NE, L core W {wc} / S {sb}; channels >= 21.6 um."
    s["job"] = {"owner": "QTILE-R", "branch": "claude/qtile-r-1023", "tag": tag,
                "purpose": "HP13 cpub39 tt_ctlm re-pack (outline from content + face pin regs); qualification candidate, not a die result",
                "extra_paths": ["results/arch/hp13_corepub39_1021", "rtl/qwen_dv/headprep13/corepub39", "results/arch/qtile_r_1023"], "benches": []}
    return s

for name, args in (("qfd_hp13_cpub39_rp_main", (75.6, 54.0, 38.88, 25.0, "rp1")), ("qfd_hp13_cpub39_rp_alt", (86.4, 54.0, 43.2, 25.0, "rp1a"))):
    s = spec(name, *args)
    d = f"{ROOT}/physical/ref_tile/{name}"; os.makedirs(d, exist_ok=True)
    json.dump(s, open(f"{d}/spec.json", "w"), indent=1)
    print(name, s["outline"], round(s["outline"]["w"] * s["outline"]["h"]))
