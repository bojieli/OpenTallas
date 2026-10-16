#!/usr/bin/env python3
"""ot_s81_cfg7_seq PINREG 1 pin plan (S-ELEM-PQ/COLL 2026-10-16, VIS-ROM finding S81F-04, owner order 01:00 "crowding /
pin positioning must be fixed").  Writes the explicit io tcl + a face report for the 17.28 x 41.04 tile.

Measured die geometry (die c21h a_real, EPYC4 s81-die-iter/c21h/a_real: floorplan_placed.def + elements/cfg/q_elem LEF),
every pair in the cfg7 local frame (FN pairs unmirrored):
  * the 7 cfg ROMs ot_rom_4096x72_m8 sit W of the tile in one row at local y 0 (ROM j at local x -322+46.6 j .. ; N pairs:
    j = 6 nearest, j = 0 farthest); their rd_out[47:0] pins lie at ROM y 0.78 .. 4.81 (rd 0..28 on the face toward
    the tile, 29..47 on the far face), addr_in / ce_in at 0.88 .. 2.03 on the far face.
  * dsfd_qbank_S.i_cfg / i_go are 78..135 um W of the tile at y +64.9, the q element's bank_free / go_tag / sh_free
    at 90..118 um W, y +74.
Plan:
  W  (M4, 0.012 + 0.048 k, 2.2 tracks/pin = 9.5 b/um, cut 0.45): bottom -> top q6 q5 q4 q3 | clk | q2 q1 q0, then
     ce6..ce0 and a[0..11] on top.  Bundles stack nearest-ROM lowest (the ROM band is local y 0.8 .. 4.8), and the bits
     of each q bundle follow the ROM rd_out pin order bottom -> top (sorted by rd_out y: 29..42, 0, 43, 1, 44, .., 4,
     47, 5..28) so a straight hop keeps its order (was: bit-index order = 'interleaved' on all 13,286 rd bundles).
     clk at the W-face point nearest the flop centroid (the q capture pin flops, PINREG 1), between q3 and q2.
  N  (M5, 3 tracks = 0.144 um): at the W end (targets lie W): ef[1] go_tag[0] go_tag[1] ef[0] cfg[0..53] go_e
     = the W->E order of their die targets (preserved on N pairs).
  E  (M4): lc[0..14], st[0..1] as the closed l1pd plan (2.16 um pitch).
  S  (M5): rst_n at the face centre.
Mirrored (FN) pairs reverse any ordered bundle that turns toward an unmirrored qbank_S / q element (chirality: no single
pin order preserves both); the die request asks for the pair to be mirrored as a unit (qbank_S + element FN on FN pairs,
ROM index j -> 6 - j) instead of a second master.
  cfg7_pr_pins.py OUT.tcl OUT_report.json
"""
import json, sys

W, H = 17.28, 41.04
TRK0, TRK = 0.012, 0.048
ROM_RD_Y = {i: 2.124 + 0.096 * i for i in range(29)}
ROM_RD_Y.update({i: 0.78 + 0.096 * (i - 29) for i in range(29, 48)})
QORD = [b for _, b in sorted((ROM_RD_Y[b], b) for b in range(48))]


def trk(v):
    return round(TRK0 + TRK * round((v - TRK0) / TRK), 3)


def main(out_tcl, out_rep):
    lines = ["# ot_s81_cfg7_seq PINREG 1 (s81coll_cfg7_seq_pr): pin plan of tools/s81/cfg7_pr_pins.py (see its header); "
             f"outline {W} x {H}"]
    # W face
    wl = []
    for j in (6, 5, 4, 3):
        wl += [f"q{j}[{b}]" for b in QORD]
    wl += [None, None, "clk", None, None]
    for j in (2, 1, 0):
        wl += [f"q{j}[{b}]" for b in QORD]
    wl += [f"ce{j}" for j in (6, 5, 4, 3, 2, 1, 0)] + [f"a[{b}]" for b in range(12)]
    y0, step = 1.0, 2.2 * TRK
    ys, used = {}, set()
    for i, p in enumerate(wl):
        if p is None:
            continue
        k = round((y0 + i * step - TRK0) / TRK)
        while k in used:
            k += 1
        used.add(k)
        ys[p] = round(TRK0 + TRK * k, 3)
    assert max(ys.values()) < H - 1.0, max(ys.values())
    for p, y in ys.items():
        lines.append(f"place_pin -pin_name {{{p}}} -layer M4 -location {{0.000 {y:.3f}}} -force_to_die_boundary")
    # N face
    nl = ["ef[1]", "go_tag[0]", "go_tag[1]", "ef[0]"] + [f"cfg[{b}]" for b in range(54)] + ["go_e"]
    xs = {}
    for i, p in enumerate(nl):
        xs[p] = trk(1.008 + i * 3 * TRK)
        lines.append(f"place_pin -pin_name {{{p}}} -layer M5 -location {{{xs[p]:.3f} {H:.3f}}} -force_to_die_boundary")
    # E face (closed l1pd plan)
    el = [f"lc[{b}]" for b in range(15)] + ["st[0]", "st[1]"]
    for i, p in enumerate(el):
        y = round(3.228 + 2.16 * i, 3)
        lines.append(f"place_pin -pin_name {{{p}}} -layer M4 -location {{{W:.3f} {y:.3f}}} -force_to_die_boundary")
    # S face
    lines.append(f"place_pin -pin_name {{rst_n}} -layer M5 -location {{{trk(W / 2):.3f} 0.000}} -force_to_die_boundary")
    open(out_tcl, "w").write("\n".join(lines) + "\n")
    wy = sorted(ys.values())
    rep = {"outline": [W, H],
           "W": {"pins": len(ys), "span_um": [wy[0], wy[-1]], "b_per_um": round(len(ys) / (wy[-1] - wy[0]), 2),
                 "cut": round(len(ys) / ((wy[-1] - wy[0]) / TRK), 3), "clk_y": ys["clk"],
                 "bundle_order_bottom_up": "q6 q5 q4 q3 clk q2 q1 q0 ce6..ce0 a[0..11]",
                 "q_bit_order_bottom_up": QORD},
           "N": {"pins": len(nl), "span_um": [xs[nl[0]], xs[nl[-1]]], "order_w_to_e": "ef[1] go_tag[0] go_tag[1] ef[0] cfg[0..53] go_e"},
           "E": {"pins": len(el)}, "S": {"pins": 1}}
    json.dump(rep, open(out_rep, "w"), indent=1)
    print(json.dumps({k: (v if k != "W" else {kk: vv for kk, vv in v.items() if kk != "q_bit_order_bottom_up"}) for k, v in rep.items()}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
