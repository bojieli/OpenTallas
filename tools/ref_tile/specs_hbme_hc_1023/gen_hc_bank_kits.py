#!/usr/bin/env python3
"""STEWARD-HBMe/HC 10-23: HC bank-family kits from the 'pair rows' skeleton (plan lanes/STEWARD-HBM.md
[STEWARD-HBMe/HC 01:48]).  Layout only: RTL, params and die faces unchanged (r18h5 d34578d6f SYNTH-view faces).
Row r (r = 0..3, S -> N): leaf 2r | W-SRAM stack {2r+1 MY (rd_out E), 2r R0 (rd_out W -> leaf 2r)} | X-SRAM r MY (rd_out
E -> leaf 2r+1) | leaf 2r+1.  Chain W -> E per row; face bands carry the CPI / CPO / landing flops (io_flop_at_pins)."""
import copy, json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RT = ROOT / "physical/ref_tile"
LEAF = 138.24
WS_W, WS_H, WS_P = 174.744, 70.488, 70.512        # 1024x256 weight SRAM, abutted stack pitch (as the 1017 kits)
XS_W, XS_H = 94.824, 41.064                        # 128x256 x SRAM
LEAF_V = "physical/ref_tile/hc_lanes_ref/views/ot_hdc_v41x_hcp_lanes"
WS_V = "physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2"
XS_V = "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2"


def snap(v, q=2.16):
    return round(round(v / q) * q, 3)


def skeleton(ch_v, ch_row=None, band=23.76, band_s=23.76, band_n=24.84):
    """macro placement + outline for the row skeleton.  Hard leaves sit on the 43.2-um child lattice (ref_tile
    macro_grid: lcm of site, row, M1-M7 tracks and strap pitch), SRAMs between them; ch_v = leaf<->stack, stack<->X,
    X<->leaf channel (>= 20 um gate rule); rows at a 172.8-um pitch (4 lattice steps; stack 141.0 + 31.8 channel)."""
    L = 43.2
    xa = L                                         # leaf A (W band 41 um from the core edge)
    xs = round(xa + LEAF + ch_v, 3)
    xx = round(xs + WS_W + ch_v, 3)
    xb = math.ceil((xx + XS_W + ch_v) / L - 1e-9) * L
    W = round(math.ceil((xb + LEAF + band) / 10.8 - 1e-9) * 10.8, 3)
    stack = WS_P + WS_H
    pitch = 4 * L
    y0 = math.ceil(band_s / L - 1e-9) * L
    rows = [round(y0 + r * pitch, 3) for r in range(4)]
    H = round(math.ceil((rows[-1] + stack + band_n) / 10.8 - 1e-9) * 10.8, 3)
    ch, mc = [], []
    for r, y in enumerate(rows):
        ch.append({"view": LEAF_V, "count": 1, "inst": f"*g_grp?{2*r}?.u_lg", "at": [xa, y], "orient": "R0"})
        ch.append({"view": LEAF_V, "count": 1, "inst": f"*g_grp?{2*r+1}?.u_lg", "at": [round(xb, 3), y], "orient": "R0"})
        mc.append({"view": WS_V, "count": 1, "inst": f"*g_w?{2*r+1}?.u_m", "at": [xs, y], "orient": "MY", "at_exact": True})
        mc.append({"view": WS_V, "count": 1, "inst": f"*g_w?{2*r}?.u_m", "at": [xs, round(y + WS_P, 3)], "orient": "R0",
                   "at_exact": True})
        mc.append({"view": XS_V, "count": 1, "inst": f"*g_x?{r}?.u_m", "at": [xx, snap(y + (stack - XS_H) / 2)],
                   "orient": "MY", "at_exact": True})
    return W, H, rows, pitch, ch, mc


def ranges(faces, W, H, lo, hi):
    """faces: {face: [(port, [a, b]), ...]} explicit ranges"""
    pins = {f: [p for p, _ in v] for f, v in faces.items()}
    pr = {p: [round(a, 3), round(b, 3)] for v in faces.values() for p, (a, b) in v}
    return pins, pr


def pack(ports, a, b):
    """pack small ports (port, width) into [a, b] proportionally"""
    tot = sum(w for _, w in ports)
    out, x = [], a
    for p, w in ports:
        d = (b - a) * w / tot
        out.append((p, [x, x + d]))
        x += d
    return out


def mk(base, name, top_note, W, H, pins, pr, ch, mc, extra=None):
    s = json.loads((RT / base / "spec.json").read_text())
    s = copy.deepcopy(s)
    s["name"] = name
    s["outline"] = {"w": W, "h": H, "exact": True}
    s["pins"], s["pin_ranges"] = pins, pr
    s.pop("pin_order_desc", None)
    s["children"], s["macros"] = ch, mc
    s["low_fill_reason"] = ("macro-bound HC bank (STEWARD-HBMe/HC 10-23, coordinator ack requested): 8 hard leaves + 12 "
                            "SRAMs ~60% of the outline; the 2,048-b chain faces set H >= 512 um at 4 pins/um; parent std "
                            "5.3k um2 synth lives in the face bands + row channels")
    s["structural_change"] = top_note
    s.setdefault("job", {})
    s["job"] = dict(s["job"], owner="STEWARD-HBMe/HC", branch="claude/hbme-hc-1023", tag=name.split("_")[-1],
                    purpose=top_note[:400])
    s["child_lattice_um"] = 2.16
    if extra:
        s.update(extra)
    kd = RT / name
    kd.mkdir(exist_ok=True)
    (kd / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    return kd


def bankq(name, ch_v, ch_row):
    W, H, rows, pitch, ch, mc = skeleton(ch_v, ch_row)
    top = rows[-1] + WS_P + WS_H
    lo, hi = rows[0], top
    w_small = [("d_v", 1), ("d_ss", 1), ("d_nv", 7), ("d_wa", 10), ("d_xa", 10), ("f_in", 1), ("wa", 10), ("j", 1),
               ("wv", 1), ("xv", 1)]
    e_small = [("o_v", 1), ("o_ss", 1), ("o_nv", 7), ("o_wa", 10), ("o_xa", 10), ("f_out", 1), ("wfault", 1)]
    faces = {"W": [("sum_in", [lo, hi])] + pack(w_small, hi + 0.5, H - 1.0),
             "E": [("sum_out", [lo, hi])] + pack(e_small, hi + 0.5, H - 1.0),
             "N": pack([("rst_n", 1), ("xb_v", 1), ("xb_beat", 2), ("xb_d", 256)], W * 0.25, W * 0.75),
             "S": [("clk", [W / 2 - 0.5, W / 2 + 0.5])]}
    pins, pr = ranges(faces, W, H, lo, hi)
    note = (f"STEWARD-HBMe/HC 10-23 pair-rows redesign of the BAD 777.6x734.4 bank: {W} x {H}; die faces (r18h5 SYNTH view) "
            "sum_in W / sum_out E / beat N / clk S; 4 rows of (leaf 2r | W-SRAM stack MY+R0 | X-SRAM MY | leaf 2r+1), every "
            "SRAM read port facing its leaf; CPI/CPO + beat landing flops anchored in face bands (io_flop_at_pins). "
            "Layout only, params CPI=CPO=1 as the die (l3_vm_hc_coll.py:210), 0 edges changed.")
    return mk("hbm_hcq_bank_cb_1017", name, note, W, H, pins, pr, ch, mc, {"params": {"CPI": 1, "CPO": 1}})


def bankq_ft(name, ch_v, ch_row):
    # mirror of the skeleton: landing / feeds in the S band; fa feed -> W bottom, fb feed -> E bottom
    W, H, rows, pitch, ch, mc = skeleton(ch_v, ch_row, band_s=34.56)
    top = rows[-1] + WS_P + WS_H
    lo = rows[0]
    fa_o = [("fa_xb_v_o", 1), ("fa_xb_beat_o", 2), ("fa_xb_d_o", 256), ("fa_wv_o", 1), ("fa_xv_o", 1), ("fa_j_o", 1),
            ("fa_wa_o", 10), ("fa_rst_n_o", 1), ("fa_wfault", 1)]
    fb_o = [(p.replace("fa_", "fb_"), w) for p, w in fa_o]
    w_small = [("d_v", 1), ("d_ss", 1), ("d_nv", 7), ("d_wa", 10), ("d_xa", 10), ("f_in", 1)]
    e_small = [("o_v", 1), ("o_ss", 1), ("o_nv", 7), ("o_wa", 10), ("o_xa", 10), ("f_out", 1)]
    s_in = [("rst_n", 1), ("xb_v", 1), ("xb_beat", 2), ("xb_d", 256), ("wv", 1), ("xv", 1), ("j", 1), ("wa", 10),
            ("wfault", 1)]
    fa_in = [("fa_xb_v", 1), ("fa_xb_beat", 2), ("fa_xb_d", 256), ("fa_wv", 1), ("fa_xv", 1), ("fa_j", 1), ("fa_wa", 10),
             ("fa_rst_n", 1), ("fa_wfault_o", 1)]
    fb_in = [(p.replace("fa_", "fb_"), w) for p, w in fa_in]
    split = lo + 64.8
    faces = {"W": pack(fa_o, 2.0, split) + [("sum_in", [split + 1.0, top])] + pack(w_small, top + 0.5, H - 1.0),
             "E": pack(fb_o, 2.0, split) + [("sum_out", [split + 1.0, top])] + pack(e_small, top + 0.5, H - 1.0),
             "S": pack(fa_in, 21.6, W * 0.36) + pack(s_in, W * 0.36, W * 0.64) + pack(fb_in, W * 0.64, W - 21.6)
             + [("clk", [W / 2 - 0.5, W / 2 + 0.5])]}
    # clk inside the s_in pack range: move it to its own sliver
    faces["S"] = [(p, r) for p, r in faces["S"] if p != "clk"]
    faces["N"] = [("clk", [W / 2 - 0.5, W / 2 + 0.5])]
    pins, pr = ranges(faces, W, H, 0, 0)
    note = (f"STEWARD-HBMe/HC 10-23 pair-rows redesign of the BAD 734.4 sq ft bank: {W} x {H}; die faces sum W->E, beat + "
            "fa/fb feeds land S, fa_o W (bottom), fb_o E (bottom); feed registers in the SW / SE corners of the S band. "
            "Layout only; no CPI/CPO (die params), 0 edges changed.")
    return mk("hbm_hcq_bank_e2_1017", name, note, W, H, pins, pr, ch, mc)


if __name__ == "__main__":
    out = [bankq("hbme_hcbq_b1", 21.6, 0), bankq("hbme_hcbq_b2", 32.4, 0),
           bankq_ft("hbme_hcbft_b1", 21.6, 0), bankq_ft("hbme_hcbft_b2", 32.4, 0)]
    for kd in out:
        s = json.loads((kd / "spec.json").read_text())
        o = s["outline"]
        print(kd.name, o["w"], o["h"], round(o["w"] * o["h"] / 1e3, 1), "k um2",
              {f: len(v) for f, v in s["pins"].items()})
