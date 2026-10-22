#!/usr/bin/env python3
"""STW-S81c-HEAD-LANE 10-22: s81hd_lane_p2m (MAIN, 518.4 x 1123.2 = the H10 die reserve) and s81hd_lane_p2f (FALLBACK,
604.8 x 1123.2, enlarged one 86.4-um column) specs.  Two CTS roots (multiple_cts_roots, related same-frequency):
ck = core/adapter region (N band, N-face pin flops), ck_l = lane-body region (W-face SerDes pin flops).
Lower block = the CLOSED s8ng lane map (gearbox x 43.2, replay x 129.6-302.4, unchanged coordinates); RX FIFO block
above it (rows from 626.4); core landing (u_ski) column on the E side straddling the RB/FIFO seam; adapter band under
the N face.  Run from the repo root: python3 results/rtl/s81_head_lane_p2_1021/gen_p2_specs.py"""
import json, copy
from pathlib import Path
base = json.load(open("physical/ref_tile/s81hd_lane_m/spec.json"))
S32 = "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1"
S256 = "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1"
def m(view, inst, x, y, o):
    return {"view": view, "count": 1, "inst": inst, "at": [round(x, 2), round(y, 2)], "orient": o, "at_exact": True}
def macros(fifo_cols, fifo_rows, ski_x):
    out = []
    gy = [43.2, 86.4, 129.6, 172.8, 216.0, 345.6, 388.8, 432.0, 475.2, 518.4]           # s8ng gearbox column
    for b, y in enumerate(gy):
        out.append(m(S32, f"*u_gb.u_sf.g_bank?{b}?.u_m", 43.2, y, "MX" if y < 300 else "R0"))
    rb = [(129.6, 43.2), (129.6, 129.6), (129.6, 216.0), (216.0, 43.2), (216.0, 129.6), (216.0, 216.0),
          (302.4, 43.2), (302.4, 129.6), (302.4, 216.0), (129.6, 345.6), (129.6, 432.0), (129.6, 518.4),
          (216.0, 345.6), (216.0, 432.0), (216.0, 518.4), (302.4, 345.6), (302.4, 432.0), (302.4, 518.4)]  # s8ng RB
    for k, (x, y) in enumerate(rb):
        out.append(m(S256, f"*u_ep.g_rb_safe.u_m.g_bank?{k // 2}?.g_depth?{k % 2}?.g_256.u_m", x, y, "MX" if y < 300 else "R0"))
    slots = [(x, y) for y in fifo_rows for x in fifo_cols]
    if len(slots) > 18:   # a partial top row: keep the centre slots
        full, top = slots[:-len(fifo_cols)], slots[-len(fifo_cols):]
        need = 18 - len(full); c = (len(top) - need) // 2
        slots = full + top[c:c + need]
    assert len(slots) == 18, len(slots)
    for k, (x, y) in enumerate(slots):
        out.append(m(S256, f"*u_ep.g_fifo_safe.u_m.g_bank?{k // 2}?.g_depth?{k % 2}?.g_256.u_m", x, y,
                     "MX" if y < fifo_rows[len(fifo_rows) // 2] else "R0"))
    for b in range(9):
        out.append(m(S32, f"*u_ski.u_head.g_bank?{b}?.u_m", ski_x, 388.8 + 43.2 * b, "MX" if b < 4 else "R0"))
    return out
def spec(name, w, fifo_cols, fifo_rows, ski_x, main):
    s = copy.deepcopy(base)
    s["name"] = name
    s["outline"] = {"w": w, "h": 1123.2, "exact": True}
    s["clock"] = "multiple_cts_roots"
    s["clock_port"] = "ck"
    s["clock_ports"] = ["ck", "ck_l"]
    s["clock_data_paths"] = "related_same_frequency"
    s["clock_relationship"] = {"kind": "same_pll_fixed_phase", "ratio": [1, 1], "phase_ps": 0}
    s["clock_entry_domains"] = {
        "core": {"ratio": [1, 1], "ports": ["ck"], "inputs": ["tx_v", "tx_d", "rst_n"], "outputs": ["rx_v", "rx_d", "flt"]},
        "lane": {"ratio": [1, 1], "ports": ["ck_l"], "inputs": ["rx", "chb"], "outputs": ["tx"]}}
    for k in ("pre_cts_extra", "boundary_tcl", "sdc_extra", "orfs_vars"):
        s.pop(k, None)
    s["recipe"] = 2
    s["inhold"] = False
    s["outhold"] = False
    s["io_flop_at_pins"] = {"cols": 4, "allow_none": True}
    s["keep_pin_regs"] = True
    s["macros"] = macros(fifo_cols, fifo_rows, ski_x)
    s["pins"] = {"W": ["rx", "tx", "ck_l", "chb"], "N": ["tx_d", "tx_v", "ck", "rst_n", "rx_v", "flt", "rx_d"]}
    e = w - 2.16
    mid = round(w / 2, 2)
    s["pin_ranges"] = {"rx": [2.16, 288.36], "tx": [290.52, 576.72], "ck_l": [579.6, 581.76], "chb": [583.92, 586.08],
                       "tx_d": [2.16, round(mid - 8.64, 2)], "tx_v": [round(mid - 7.56, 2), round(mid - 6.48, 2)],
                       "ck": [round(mid - 5.4, 2), round(mid - 3.24, 2)], "rst_n": [round(mid - 2.16, 2), mid],
                       "rx_v": [round(mid + 1.08, 2), round(mid + 2.16, 2)], "flt": [round(mid + 3.24, 2), round(mid + 8.64, 2)],
                       "rx_d": [round(mid + 9.72, 2), round(e, 2)]}
    s["pin_regs"] = {"enable": False, "reason": "Source-registered (unchanged RTL registers): tx_d lands in txd_p, tx_v in 2 kept ot_s81hd_kf pin flops, rx_v / rx_d / flt leave flops (rv_q / rd_q / flt_q); rx enters the lane rx landing flops (lr_f / lr_d) and tx is the gearbox registered beat (dscoll_lane_w_s8ng closed structure). A recipe pin stage would add an unpriced edge."}
    s["reset_landing"] = {"enable": True, "stages": 2, "clock": "ck", "reason": "rst_n lands in 2 ck flops at the N core face, then ot_rst_relay_tree3 (35 slice leaves + lane + rx + misc, every leaf <= ~32 reset pins); the lane keeps its own tree3 below its leaf (ck_l region: the leaf r_lane -> lane rs is a register -> register crossing)"}
    s["slot_change_request"] = ({"reason": "none: MAIN outline = the H10 die reserve ln_* 518.4 x 1123.2 R0 (results/arch/s81_head_1021/h10m/plan_unrouted_h10.json). PORT CHANGE: +ck_l (lane-body region clock, W face y 579.6-581.76 beside the SerDes pins; the die drives it from the lane/SerDes region root, ck from the ctl-link side, same PLL phase 0). Faces: SerDes rx/tx/chb/ck_l on W (MY for the E-SerDes lanes), core tx_d/rx_d/v/flt/ck/rst_n on N (the H10 core_i/core_o face)."}
                                if main else
                                {"reason": "FALLBACK enlarges the reserve 518.4 -> 604.8 x 1123.2 (+86.4 um W-E; H10 mesh/draft-E lanes have >= 302 um to the west neighbour, host/draft-W lanes need the die owner to shift x by 86.4). Same PORT CHANGE (+ck_l) and faces as MAIN."})
    s["fill_reason"] = {"pin_bound": "lattice/channel-bound: the 55 bank64 SRAMs (62,002 um2) on the 43.2 lattice with >= 20-um channels (s8ng lane map below, RX FIFO block above, core landing column E); the die reserve fixes the outline (MAIN) / one extra column (FB). Fill is channel area, not a squeezed util target; never shrink."}
    s["structural_change"] = (
        "STW-S81c-HEAD-LANE 10-22 (successor of s81hd_lane_m/f: clock_rule FAIL boundary spread TT 81.5/FF 83.0 (m), TT 112.9 (f) "
        "on ONE ck root over an 812-um tile with pin flops on both opposite faces; and 812.16 x 583.2 did not fit the H10 reserve "
        "518.4 x 1123.2): TWO REGIONAL CTS ROOTS -- ck = core/adapter region (N face pin flops, reset landing), ck_l = lane-body "
        "region (W face SerDes landing / gearbox beat flops). RTL: +1 port ck_l (u_ln and the rx-enable flop on ck_l); every "
        "ck <-> ck_l crossing is register -> register (fixed-latency landed seam, 0 added cycles; bench ck_l = ck cycle-identical). "
        "Portrait floorplan: lower block = the CLOSED dscoll_lane_w_s8ng map (gearbox + replay unchanged coordinates, SerDes pins "
        "W 2.16-576.72 as s8ng), RX FIFO block above (rows from 626.4), core landing u_ski column E straddling the seam, adapter "
        "band under the N face; ck_l entry on W beside the SerDes pins, ck entry N centre. Recipe 2 macro-edge guard (s8ng DRC "
        "lesson) + pin flops anchored at the faces. " + ("MAIN (= die reserve)." if main else "FALLBACK (enlarged +86.4: 5-column FIFO block, 196-um adapter band)."))
    j = s["job"]
    j["owner"] = "Claude:STW-S81c-HEAD-LANE"
    j["branch"] = "claude/s81-head-lane-p2-1021"
    j["tag"] = name
    j["purpose"] = ("S81.HEAD.LANE: head-die lane block (safe8_ntf lane + static core adapter), two regional CTS roots ck/ck_l, "
                    "portrait at the H10 reserve, to closure (TT setup / FF hold / DRC 0). SAFE review in kit README. " + ("MAIN" if main else "FALLBACK"))
    j["views_to"] = f"physical/ref_tile/{name}/views"
    j["record_to"] = f"results/rtl/ref_tile/{name}"
    j["extra_paths"] = [p for p in j["extra_paths"] if "clock_split_km" not in p] + ["results/rtl/s81_head_lane_p2_1021"]
    for b in j["benches"]:
        for k in ("pass_witness", "fail_witness"):
            if k in b:
                b[k] = b[k].replace("results/rtl/s81_head_ctlgate_1021/lane/", "results/rtl/s81_head_lane_p2_1021/lane/")
    d = Path(f"physical/ref_tile/{name}"); d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print(name, w, len(s["macros"]))
spec("s81hd_lane_p2m", 518.4, [43.2, 129.6, 216.0, 302.4], [626.4, 712.8, 799.2, 885.6, 972.0], 432.0, True)
spec("s81hd_lane_p2f", 604.8, [43.2, 129.6, 216.0, 302.4, 388.8], [626.4, 712.8, 799.2, 885.6], 518.4, False)
