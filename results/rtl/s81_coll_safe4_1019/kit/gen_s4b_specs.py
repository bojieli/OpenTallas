#!/usr/bin/env python3
"""S81-COLL safe4 lane kits dscoll_lane_w_s4b / dscoll_lane_e_s4b (S81-COLL3, S81.STA.LKTO.2, 10-19): PARALLEL landscape
variant of s4 (705.6 x 540, 3 big rows per strip, 8 columns; macro->band <= ~215 um). Same rules as s4 below.

Structural successor of the s3 geometry (s3 W/E gates FAIL: trial GRT negotiation 89 iterations from ~3,600 overflow,
then the post-repair incremental re-route stalled > 4 h; 52 macro channels < 20 um, stacks off the 43.2 lattice).
Safe-design checklist item 6 built literally (same rules as tools/ref_tile/measured_band_fill.lattice_band_errors):
  * every macro origin on the 43.2 um lattice; every macro pair >= 20 um apart (pin faces W/E get 51.8 um channels,
    pinless N/S faces 45.0 um); >= 20 um from the core edge
  * ONE full-width standard-cell band y 345.6..385.2 (39.6 um) between the strips; rows outside the band are removed
    before tapcell (physical/dscoll_cx/coll_s4_cell_band.tcl), so no std cell can sit in a macro channel
  * S strip (RX FIFO 18 x 256x64 in columns 0-4, credit-rx landing 9 x 32x64 at the core face: column 5 + 2 free
    slots of column 4), orient MX;  N strip (gearbox slot store 10 x 32x64 at the link face: column 0 + 2 free slots
    of column 1, replay 18 x 256x64 in columns 1-5), orient R0.  4 big rows per strip at 86.4 um pitch.
  * outline 540.0 x 712.8 (aspect 1.32); W/E faces 708 um carry the 515/512 link and 553/553 core buses at <= 2/um.
E tile = column mirror of W (column k -> 5-k, still on the lattice; R0 -> MY, MX -> R180; pin faces W <-> E).
"""
import copy, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
S3 = json.loads((ROOT / "physical/ref_tile/dscoll_lane_w_s3/spec.json").read_text())
STD = float(sys.argv[1]) if len(sys.argv) > 1 else 9445.0
W, H = 705.6, 540.0
LAT = 43.2
BIG, SML = ("physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1",
            "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1")
BW, BH, SW, SH = 34.584, 41.352, 31.992, 17.304
BAND = (259.2, 288.0)
COLX = [round(LAT * (1 + 2 * k), 4) for k in range(8)]          # 43.2, 129.6, ..., 475.2
S_BIG = [216.0, 129.6, 43.2]                   # S strip rows, nearest the band first
N_BIG = [302.4, 388.8, 475.2]                  # N strip rows, nearest the band first
RB, FF = "*u_ep.g_rb_safe.u_m.g_bank?{b}?.g_depth?{d}?.g_256.u_m", "*u_ep.g_fifo_safe.u_m.g_bank?{b}?.g_depth?{d}?.g_256.u_m"
GB, CR = "*u_gb.u_sf.g_bank?{b}?.u_m", "*u_ski.u_head.g_bank?{b}?.u_m"


def r(v):
    return round(v, 4)


def m(view, inst, x, y, o):
    return {"view": view, "count": 1, "inst": inst, "at": [r(x), r(y)], "orient": o, "at_exact": True}


def macros_w():
    out = []
    # N strip: GB cols 0/1 (5 small slots each, 302.4 + 43.2 j); RB cols 2-7 x 3 rows
    gb_slots = [(COLX[c], 302.4 + LAT * j) for c in (0, 1) for j in range(5)]
    for b, (x, y) in enumerate(gb_slots):
        out.append(m(SML, GB.format(b=b), x, y, "R0"))
    rb_slots = sorted([(COLX[c], N_BIG[k]) for c in range(2, 8) for k in range(3)])
    for i, (x, y) in enumerate(rb_slots):
        out.append(m(BIG, RB.format(b=i // 2, d=i % 2), x, y, "R0"))
    # S strip: FF cols 0-5 x 3 rows; CR cols 6/7 (5 + 4 small slots, 43.2 j, nearest the band first)
    ff_slots = sorted([(COLX[c], S_BIG[k]) for c in range(6) for k in range(3)], key=lambda p: (p[0], -p[1]))
    for i, (x, y) in enumerate(ff_slots):
        out.append(m(BIG, FF.format(b=i // 2, d=i % 2), x, y, "MX"))
    cr_slots = [(COLX[6], LAT * (5 - j)) for j in range(5)] + [(COLX[7], LAT * (5 - j)) for j in range(4)]
    for b, (x, y) in enumerate(cr_slots):
        out.append(m(SML, CR.format(b=b), x, y, "MX"))
    assert len(out) == 55, len(out)
    return out


def mirror(ms):
    out = copy.deepcopy(ms)
    for q in out:
        k = COLX.index(q["at"][0])
        q["at"][0] = r(COLX[7 - k])
        q["orient"] = {"R0": "MY", "MX": "R180"}[q["orient"]]
    return out


SRCS = ["rtl/link/ot_link_crc32.sv", "rtl/lib/ot_rst_relay_tree3.sv", "rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv",
        "rtl/lib/ot_sram_oldread_b64.sv", "rtl/lib/ot_sram_showahead_b64.sv", "rtl/common/ot_link_credit_rx_b64.sv",
        "rtl/common/ot_link_credit_tx_rc.sv", "rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe4.sv",
        "rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv", "rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv"]
# link face: rx (515) S half next to the RX FIFO, tx (512) N half next to the gearbox; core face: lo_d (553, in) S half next
# to the credit-rx landing, li_d (553, out) N half; control + ck/rs at the band (ck at the band centre y 365.4)
PR = {"rx": [2.16, 266.76], "tx": [268.92, 533.52], "tf": [535.68, 537.84],
      "lo_d": [2.16, 252.72], "lo_v": [254.88, 255.96], "lo_r": [257.04, 258.12], "chb": [259.2, 261.36],
      "ck": [272.16, 274.32], "rs": [276.48, 278.64], "li_v": [280.8, 281.88], "li_r": [282.96, 284.04],
      "flt": [285.12, 288.36], "li_d": [290.52, 537.84]}
BENCH_W = "results/rtl/s81_coll_safe4_1019/bench"


def benches():
    vb = []
    for k, exp, rx in ((0, "pass", None), (1, "fail", r"^COLL_SAFE4_BOUNDARY FAIL errors=[1-9]"),
                       (2, "fail", r"COLL_COLLISION_UNSAFE"), (3, "fail", r"^COLL_SAFE4_BOUNDARY FAIL errors=[1-9]"),
                       (4, "fail", r"^COLL_SAFE4_BOUNDARY FAIL errors=[1-9]")):
        b = {"name": f"lane_miter_m{k}", "cmd": f"bash tools/xdie_s81/coll_safe4_boundary.sh {{RUN}}/miter{k} {k}",
             "expect": exp, "threads": 4, "peak_ram_gb": 8, "needs": ["verilator"],
             "pass_regex": r"^COLL_SAFE4_BOUNDARY PASS checks=\d+"}
        if exp == "pass":
            b["pass_witness"] = f"{BENCH_W}/lane_miter_m0.log"
        else:
            b.update(fail_regex=rx, fail_witness=f"{BENCH_W}/lane_miter_m{k}.log")
        vb.append(b)
    return vb


CHECK = ("SAFE checklist (README): 1 pins RTL-registered + reset_landing 2; 2 reach: tile 705.6x540, macro->band <= 216 um, "
         "pin->band <= 257 um; 3 safe4 UNA copies + split rewind cones (kept hierarchy); 4 depth (gate textbook); "
         "5 all storage in 55 bank64 SRAMs; 6 43.2 lattice, >= 20 um channels everywhere, one 28.8 um full-width band "
         "(rows outside removed); 7 spine clock, io_hold 0.03; 8 static, 0 added cycles (safe4 miter m0 79,994 PASS)")


def spec(side):
    s = copy.deepcopy(S3)
    name = f"dscoll_lane_{side}_s4b"
    s.update(name=name, top=f"dsfd_coll_lane_{side}_safe4", sources=SRCS, params={"CH_BOARD": 700},
             outline={"w": W, "h": H}, std_area_um2=STD, pin_ranges=PR, boundary_tcl=[], recipe=1)
    link, core = ["rx", "tx", "tf"], ["lo_v", "lo_r", "lo_d", "li_v", "li_r", "li_d", "flt", "ck", "rs", "chb"]
    s["pins"] = {"W": link, "E": core} if side == "w" else {"E": link, "W": core}
    s["macros"] = macros_w() if side == "w" else mirror(macros_w())
    s["route"].update(io_hold_margin_ns=0.03, hold_margin_ns=0.03, macro_halo_um=5.4,
                      synth_keep_modules=["ot_sram_showahead_b64_hit5", "ot_s81ph_kp4_20", "ot_s81ph_kff4_1",
                                          "ot_s81ph_kff4_10", "ot_s81ph_rewind4"])
    band = (f"one full-width std-cell band y {BAND[0]}..{BAND[1]} ({BAND[1]-BAND[0]:.1f} um, "
            f"{STD / ((W - 4.32) * (BAND[1] - BAND[0])):.1%} of the synthesis std area {STD:.0f} um2)")
    s["fill_reason"] = {"pin_bound": (
        "lattice/channel-bound (owner checklist 6; the lattice_band_errors rules of tools/ref_tile/measured_band_fill.py "
        "pass on this outline except the ROOT approval, which is requested in COORD-REVIEW-QUEUE): 55 bank64 SRAMs "
        "62,002 um2 on the 43.2 um lattice with >= 20 um channels force 86.4 um column and row pitch; " + band +
        "; rows outside the band are removed, so the low overall fill is channel area, not spare std-cell area")}
    s["slot_change_request"] = {"reason": "S81-COLL safe4 s4b 705.6x540.0 (s3 475.2x421.2 FAIL GRT): the die parent must re-slot "
                                "the 16 lane tiles per die to this outline (same ports as legacy; ck/rs/chb at y 255..289)"}
    s["reset_landing"] = {"enable": True, "stages": 2, "clock": "ck", "reason": "rs lands on the core face in two ck flops, "
                          "then ot_rst_relay_tree3 (3 balanced edges, every leaf <= ~32 reset pins); same release depth as safe3"}
    j = s["job"]
    j.update(owner="Claude:S81-COLL3", branch="claude/s81-coll-s4-1019", tag="s4b",
             purpose="S81-COLL safe4: UNA copies + split rewind cones, 55 bank64 SRAMs on the 43.2 lattice, one band. " + CHECK,
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}", benches=benches(),
             extra_paths=["rtl", "tools/xdie_s81", BIG + "/ot_sram_1r1w2c_256x64_m1.v", SML + "/ot_sram_1r1w2c_32x64_m1.v",
                          "physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v",
                          "physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v",
                          "physical/ref_tile/dscoll_lane_w_ltr/kit.env", "physical/dscoll_cx/coll_s4b_cell_band.tcl"])
    return name, s


if __name__ == "__main__":
    for side in ("w", "e"):
        name, s = spec(side)
        d = ROOT / "physical/ref_tile" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        print("wrote", d / "spec.json")
