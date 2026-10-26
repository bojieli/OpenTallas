#!/usr/bin/env python3
"""HBM-SU 2026-10-17: kit spec + exact pin plan for hbm_su_pslice_r3_1017 (ot_hbm_su_programme_pslice_q2, RTL unchanged).

r2 gate FAIL (9272b2f43): spine CTS TT 1074 ps, 12,769 placement-STA violators (psel->command -1276, macro->pair_q -1253,
c_v->command -898, cfg->macro -418), macros off the 43.2 um lattice, command pins packed on S x 647-925.
r3 floorplan, from the producer's data flow (cfg N -> index SRAMs -> index pair regs -> indices_r -> dictionary SRAMs ->
dictionary pair regs -> command regs -> S pins):
  * 7 columns of abutted N-S SRAM stacks (pins on W/E only; abutted_stack rule), column origins x = 43.2 + 129.6 k and
    stack bases y on the 43.2 um lattice; 34.8 um channels; even columns MY / odd R0 so each column pair faces its
    rd_out pins into one shared channel (pair registers live there); column 6 R0.
  * dictionary stacks at the bottom (y 43.2, <= 7 macros), index stacks 7 x 8 above (y 388.8), 58 um channel between
    for indices_r and the dictionary address fan-out; one S std-cell band (y 0..43.2) holds the command registers.
  * dictionary columns placed so each logical column's 256 command bits sit on the S face under its banks' centroid;
    command pins spread over the whole S face (0.384 um pitch, 2.6/um), clk in the S face at x~470 (register mass
    centroid x 470, y ~285: S is the nearest face), cfg/start/status spread over the whole N face.
Usage: python3 tools/ref_tile/specs_hbm_su/make_pslice_r3.py   (from the repo root)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
R2 = ROOT / "physical/ref_tile/hbm_su_pslice_r2_1017/spec.json"
OUT_SPEC = ROOT / "tools/ref_tile/specs_hbm_su/hbm_su_pslice_r3_1017.json"
OUT_IO = "tools/ref_tile/specs_hbm_su/hbm_su_pslice_r3_1017_pins.tcl"
VIEW = "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2"
W, H = 939.6, 760.32
MH = 41.04
LAT = 43.2
XCOL = [LAT + 3 * LAT * k for k in range(7)]          # 43.2 + 129.6 k
ORIENT = ["MY", "R0", "MY", "R0", "MY", "R0", "R0"]
SB, DICT = 2422, [3, 10, 9, 13, 2, 1, 1, 1, 1, 1]     # dictionary banks per logical column (pslice_q2 DICT_BANKS)
# dictionary stacks, bottom -> top, (column, bank)
DCOL = [
    [(0, 0), (0, 1), (0, 2), (5, 0), (1, 0), (1, 1)],
    [(1, b) for b in range(2, 8)],
    [(6, 0), (1, 8), (1, 9), (2, 0), (2, 1), (2, 2), (2, 3)],
    [(7, 0)] + [(2, b) for b in range(4, 9)],
    [(3, b) for b in range(0, 6)],
    [(3, b) for b in range(6, 12)],
    [(4, 0), (4, 1), (9, 0), (8, 0), (3, 12)],
]
SEG_ORDER = [0, 5, 1, 6, 2, 7, 3, 8, 4, 9]            # logical columns along S, W -> E (by bank centroid)
D_BASE, I_BASE, I_ROWS = LAT, 9 * LAT, 8               # y 43.2 / 388.8


def macros():
    out = []
    seen = set()
    for k, stack in enumerate(DCOL):
        for j, (c, b) in enumerate(stack):
            assert (c, b) not in seen and b < DICT[c]
            seen.add((c, b))
            out.append({"view": VIEW, "count": 1, "inst": f"*u_p.dt?{c}?.mem.g?{b}?.mem",
                        "at": [round(XCOL[k], 3), round(D_BASE + MH * j, 3)], "orient": ORIENT[k], "exact": True})
    assert len(seen) == sum(DICT) == 42
    for k in range(7):
        for j in range(I_ROWS):
            b = k * I_ROWS + j
            out.append({"view": VIEW, "count": 1, "inst": f"*u_p.ix?0?.mem.g?{b}?.mem",
                        "at": [round(XCOL[k], 3), round(I_BASE + MH * j, 3)], "orient": ORIENT[k], "exact": True})
    assert len(out) == 98
    return out


PITCH = {"M3": 0.036, "M5": 0.048}
OFF = {"M3": 0.009, "M5": 0.012}
SIZE = {"M3": (0.018, 0.144), "M5": (0.024, 0.192)}


def snap(x, p, o):
    return round(round((x - o) / p) * p + o, 3)


def face_lines(bits, face, margin=4.32):
    span = W - 2 * margin
    step = span / len(bits)
    assert step >= 0.072, (face, step)
    used, lines, pos = set(), [], {}
    for i, b in enumerate(bits):
        layer = "M3" if i % 2 == 0 else "M5"
        x = snap(margin + step * (i + 0.5), PITCH[layer], OFF[layer])
        while (layer, x) in used:
            x = round(x + PITCH[layer], 3)
        used.add((layer, x))
        pos[b] = x
        y = 0.0 if face == "S" else H
        sx, sy = SIZE[layer]
        lines.append(f"place_pin -pin_name {{{b}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} "
                     f"-pin_size {{{sx} {sy}}} -force_to_die_boundary")
    return lines, pos


def main():
    s = json.loads(R2.read_text())
    s["name"] = "hbm_su_pslice_r3_1017"
    s["macros"] = macros()
    s["pins"] = {"S": ["command", "clk"], "N": ["cfg_data", "cfg_bank", "cfg_row", "cfg_we", "rst_n", "start", "length",
                                               "busy", "valid", "done", "fault", "edge_index"]}
    s.pop("pin_ranges", None)
    s["io_tcl"] = OUT_IO
    s["clock"] = "cts"
    s["orfs_vars"] = {}
    # S face: command segments in SEG_ORDER, clk at x ~ 470 (inside the dt2 segment)
    sbits = []
    for c in SEG_ORDER:
        sbits += [f"command[{i}]" for i in range(256 * c, min(256 * (c + 1), SB))]
    assert len(sbits) == SB
    sbits.insert(1024 + 190, "clk")
    nb = []
    widths = {"cfg_data": 256, "cfg_bank": 16, "cfg_row": 7, "length": 16, "edge_index": 16}
    for p in s["pins"]["N"]:
        nb += [f"{p}[{i}]" for i in range(widths[p])] if p in widths else [p]
    ls, ps = face_lines(sbits, "S")
    ln, pn = face_lines(nb, "N")
    hdr = ["# generated by tools/ref_tile/specs_hbm_su/make_pslice_r3.py: S = command (logical dictionary columns in "
           f"order {SEG_ORDER}, each under its banks) + clk at x {ps['clk']}; N = cfg/start/status spread over the face"]
    (ROOT / OUT_IO).write_text("\n".join(hdr + ls + ln) + "\n")
    s["structural_change"] = (
        "SUCCESSOR of hbm_su_pslice_r2_1017 (gate FAIL 9272b2f43: spine CTS TT 1074 ps / SS 1414; 12,769 placement-STA "
        "violators: dt psel->command -1276 (1,892), dt macro->pair_q -1253 (633), dt select_q->pair_q -1049, c_v->command "
        "-898, cfg c_bank/c_data->macro -418/-385, ix psel->indices_r -408; GRT >2 h; SRAMs off the 43.2 um lattice; "
        "2,422 command pins packed on S x 647-925). The command[816] path is distance, not depth: psel[5] -> AND5 -> "
        "~1.6 ns of buffered wire -> OA22/OA211/NOR2 -> D (6 logic cells). RTL unchanged (PIPE 1 bench PASS 8d700b8bc). "
        "r3 = placement structure only: 7 abutted SRAM column stacks on the 43.2 lattice (x 43.2 + 129.6 k, bases y "
        "43.2 / 388.8), MY/R0 column pairs facing rd_out into shared 34.8 um channels, dictionary stacks (<= 7) at the S "
        "band with every logical column's command bits on the S face under its banks (exact io_tcl, 2.6 pins/um over the "
        "whole face), index 7 x 8 above with a 58 um channel for indices_r / dictionary addresses, clk on S at x ~470 "
        "beside the register-mass centroid, local TritonCTS instead of the macro-leaf spine.")
    s["job"]["tag"] = "r3"
    s["job"]["purpose"] = ("partitioned SU programme per-quarter producer r3 (RTL = r2 PIPE 1): lattice SRAM column "
                           "stacks, S command band under the dictionary banks, exact full-face pins, local CTS")
    s["job"]["views_to"] = "physical/ref_tile/hbm_su_pslice_r3_1017/views"
    s["job"]["record_to"] = "results/rtl/ref_tile/hbm_su_pslice_r3_1017"
    OUT_SPEC.write_text(json.dumps(s, indent=1) + "\n")
    print("spec", OUT_SPEC, "io", OUT_IO, "clk_x", ps["clk"], "S pitch", round((W - 8.64) / len(sbits), 3),
          "N pitch", round((W - 8.64) / len(nb), 3))


if __name__ == "__main__":
    main()
