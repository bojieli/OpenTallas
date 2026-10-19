#!/usr/bin/env python3
"""S81-COLL bank64 safe3 lane kits dscoll_lane_w_s3 / dscoll_lane_e_s3 (LEAD2-S81/LINK-COLL 10-19).
Geometry (one structural design, from the closed 10-13 idea: SRAMs in edge strips, logic in ONE full-width band):
  * N strip (TX path)  : gearbox slot store 10 x 32x64 (2 abutted 5-stacks at the link face) + replay 18 x 256x64
                         (5 columns, abutted 4-stacks = 2 banks x 2 depths per column), orient R0 (pins face down)
  * full-width std-cell band y 189.24..233.28 (44 um) between the strips: every bus runs W<->E in the band, macros
                         reach it through the 30.2 um column channels (no bus crosses an SRAM array)
  * S strip (RX path)  : receive FIFO 18 x 256x64 (5 columns) + credit-rx landing 9 x 32x64 (5+4 stacks at the core
                         face), orient MX (pins face up, at the band)
  Columns at x = 28.08 + 64.8 k (34.584 macro + 30.216 channel: <= 4 x 2 x 106 contacts per channel), stacks abutted
  N-S at macro height + 0.024 (pins only on the W / E macro faces).  E tile = exact mirror of W (x -> W - x - w,
  R0 -> MY, MX -> R180; pin faces W <-> E; same pin ranges incl. ck)."""
import json, copy, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
LTR = json.loads((ROOT / "physical/ref_tile/dscoll_lane_w_ltr/spec.json").read_text())
STD = float(sys.argv[1]) if len(sys.argv) > 1 else 9387.0
COMMIT = sys.argv[2] if len(sys.argv) > 2 else "COMMIT"
W, H = 475.2, 421.2
BIG, SML = "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1", "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1"
BW, BH, SW, SH = 34.584, 41.352, 31.992, 17.304
X0, PX = 28.08, 64.8
S_BOT, S_TOP, N_BOT = 23.76, 23.76 + 3 * (BH + 0.024) + BH, 233.28   # S strip 23.76..189.24, band ..233.28
def r(v): return round(v, 4)
def big_stack(col, banks, pat, strip):
    out = []
    n = 2 * len(banks)
    for j, (b, d) in enumerate([(b, d) for b in banks for d in (0, 1)]):
        if strip == "N": y = N_BOT + j * (BH + 0.024); o = "R0"
        else: y = S_TOP - BH - (n - 1 - j) * (BH + 0.024); o = "MX"     # top-aligned at the band
        out.append({"view": BIG, "count": 1, "inst": pat.format(b=b, d=d), "at": [r(X0 + col * PX), r(y)], "orient": o, "at_exact": True})
    return out
def sml_stack(col, banks, pat, strip):
    out = []; n = len(banks)
    for j, b in enumerate(banks):
        if strip == "N": y = N_BOT + j * (SH + 0.024); o = "R0"
        else: y = S_TOP - SH - (n - 1 - j) * (SH + 0.024); o = "MX"
        out.append({"view": SML, "count": 1, "inst": pat.format(b=b), "at": [r(X0 + col * PX), r(y)], "orient": o, "at_exact": True})
    return out
RB, FF = "*u_ep.g_rb_safe.u_m.g_bank?{b}?.g_depth?{d}?.g_256.u_m", "*u_ep.g_fifo_safe.u_m.g_bank?{b}?.g_depth?{d}?.g_256.u_m"
GB, CR = "*u_gb.u_sf.g_bank?{b}?.u_m", "*u_ski.u_head.g_bank?{b}?.u_m"
macros = sml_stack(0, range(0, 5), GB, "N") + sml_stack(1, range(5, 10), GB, "N")
for c, bk in enumerate([(0, 1), (2, 3), (4, 5), (6, 7), (8,)]):
    macros += big_stack(2 + c, bk, RB, "N") + big_stack(c, bk, FF, "S")
macros += sml_stack(5, range(0, 5), CR, "S") + sml_stack(6, range(5, 9), CR, "S")
assert len(macros) == 55
SRCS = ["rtl/link/ot_link_crc32.sv", "rtl/lib/ot_rst_relay_tree3.sv", "rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv",
        "rtl/lib/ot_sram_oldread_b64.sv", "rtl/lib/ot_sram_showahead_b64.sv", "rtl/common/ot_link_credit_rx_b64.sv",
        "rtl/common/ot_link_credit_tx_rc.sv", "rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe3.sv",
        "rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv", "rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe3.sv"]
PR = {"rx": [2.16, 207.36], "tx": [209.52, 415.8], "tf": [416.88, 419.04],
      "lo_d": [2.16, 199.8], "lo_v": [200.88, 201.96], "lo_r": [203.04, 204.12], "chb": [205.2, 207.36],
      "ck": [209.52, 211.68], "rs": [213.84, 216.0], "li_d": [218.16, 410.4], "li_v": [411.48, 412.56],
      "li_r": [413.64, 414.72], "flt": [415.8, 419.04]}
BENCH_W = "results/rtl/s81_coll_bank64_safe3_1019/bench"
def benches():
    vb = []
    for name, mode, exp in (("xdie_switched_pass", "pass", "pass"), ("xdie_mut_board400", "board400", "fail"), ("xdie_mut_chb0", "chb0", "fail")):
        b = {"name": name, "cmd": f"J=6 bash tools/xdie_s81/kit_bench_b64.sh {{RUN}}/{mode} {mode}", "expect": exp, "threads": 6,
             "peak_ram_gb": 30, "needs": ["verilator"], "pass_regex": r"^PASS xdie_s81: \d+ beats of the TP4 calendar landed bit-exact"}
        if exp == "pass":
            b.update(min_count_regex=r"^PASS xdie_s81: (\d+) beats", pass_witness=f"{BENCH_W}/xdie_{mode}.log")
        else:
            b.update(fail_regex=r"^FAIL xdie_s81: landed \d+/\d+ mismatches \d+ late [1-9]", fail_witness=f"{BENCH_W}/xdie_{mode}.log")
        vb.append(b)
    for m, exp, rx in ((0, "pass", None), (1, "fail", r"^COLL_SAFE3_BOUNDARY FAIL errors=[1-9]"),
                       (2, "fail", r"COLL_COLLISION_UNSAFE"), (3, "fail", r"^COLL_SAFE3_BOUNDARY FAIL errors=[1-9]"),
                       (4, "fail", r"^COLL_SAFE3_BOUNDARY FAIL errors=[1-9]")):
        b = {"name": f"lane_miter_m{m}", "cmd": f"bash tools/xdie_s81/coll_safe3_boundary.sh {{RUN}}/miter{m} {m}", "expect": exp,
             "threads": 4, "peak_ram_gb": 8, "needs": ["verilator"], "pass_regex": r"^COLL_SAFE3_BOUNDARY PASS checks=\d+"}
        if exp == "pass": b["pass_witness"] = f"{BENCH_W}/lane_miter_m0.log"
        else: b.update(fail_regex=rx, fail_witness=f"{BENCH_W}/lane_miter_m{m}.log")
        vb.append(b)
    return vb
CHECK = ("SAFE checklist (README): 1 pins RTL-registered + reset_landing 2; 2 reach <= 405 (tile 475x421, registered "
         "stages); 3 kept copies (kff1/kff10/kp20 kept hierarchy, census 0 >32 target); 4 depth <= 600 ps (census); "
         "5 all storage in 55 bank64 SRAMs; 6 strips + one 44 um full-width band, 2.56 / 5.95 pins/um macro faces; "
         "7 spine clock, io_hold 0.03; 8 static, 0 added cycles vs P1")
def spec(side):
    s = copy.deepcopy(LTR)
    name = f"dscoll_lane_{side}_s3"
    s.update(name=name, top=f"dsfd_coll_lane_{side}_safe3", sources=SRCS, params={"CH_BOARD": 700}, outline={"w": W, "h": H},
             std_area_um2=STD, pin_ranges=PR, boundary_tcl=[], recipe=1)
    link, core = ["rx", "tx", "tf"], ["lo_v", "lo_r", "lo_d", "li_v", "li_r", "li_d", "flt", "ck", "rs", "chb"]
    s["pins"] = {"W": link, "E": core} if side == "w" else {"E": link, "W": core}
    ms = copy.deepcopy(macros)
    if side == "e":
        for m in ms:
            w = BW if m["view"] == BIG else SW
            m["at"][0] = r(W - m["at"][0] - w); m["orient"] = {"R0": "MY", "MX": "R180"}[m["orient"]]
    s["macros"] = ms
    s["route"].update(io_hold_margin_ns=0.03, hold_margin_ns=0.03, macro_halo_um=5.4)
    s.pop("orfs_vars", None)
    s["route"]["synth_keep_modules"] = ["ot_sram_showahead_b64_hit5", "ot_s81ph_kp20", "ot_s81ph_kff1", "ot_s81ph_kff10"]
    s.pop("fill_reason", None)
    s["fill_reason"] = {"pin_bound": ("SRAM-dominated: 55 bank64 macros 62,002 um2 (36 x 256x64 + 19 x 32x64, the <=6 pins/um "
        "family) on abutted stacks with 30.2 um pin channels; std %.0f um2 sits in one full-width 44 um band at ~45%% density; "
        "the W/E faces carry 1,028 / 1,110 bus pins (2.4 / 2.6 per um over 421 um)" % STD)}
    s["slot_change_request"] = {"reason": "S81-COLL safe3 475.2x421.2 (P1 candidate 561.6 square, safe 475.2x561.6): the die parent "
        "must re-slot the lane tiles to this outline; tf kept (no parent port change)"}
    s["reset_landing"] = {"enable": True, "stages": 2, "clock": "ck", "reason": "rs lands on the core face in two ck flops, then "
        "ot_rst_relay_tree3 (3 balanced edges, every leaf <= ~32 reset pins); same release depth as safe2"}
    s["pin_regs"] = {"enable": False, "reason": "safe3 RTL registers every data pin (rx -> lr_f/lr_d pin flops; tx = gearbox "
        "registered beat; lo_v/lo_d -> ot_link_credit_rx_b64 landing flops, lo_r registered credit; li_v/li_d ot_link_credit_tx_rc "
        "sender flops, li_r captured; flt flops; chb registered in the endpoint). An extra pin stage would add +1 edge to the "
        "measured xdie landing cycles (cycle-identical to P1 by the lane miter)."}
    j = s["job"]
    j.update(owner="Claude:LEAD2-S81/LINK-COLL", branch="claude/s81-coll-s3-1019", tag="s3",
             purpose="S81-COLL bank64 safe3: all storage on 55 bank64 SRAMs, kept-hierarchy fanout copies, strip+band geometry. " + CHECK,
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}", benches=benches(),
             extra_paths=["rtl", "tools/xdie_s81", BIG + "/ot_sram_1r1w2c_256x64_m1.v", SML + "/ot_sram_1r1w2c_32x64_m1.v",
                          "physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v",
                          "physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v",
                          "physical/ref_tile/dscoll_lane_w_ltr/kit.env", "results/rtl/xdie_s81_1018/gate_g5"])
    return name, s
for side in ("w", "e"):
    name, s = spec(side)
    d = ROOT / "physical/ref_tile" / name; d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print("wrote", d / "spec.json")
