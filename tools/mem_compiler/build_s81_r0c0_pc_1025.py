#!/usr/bin/env python3
"""Generate ot_sram_1r1w_512x128_m4_r0c0_pc: the true no-repair r0c0 SRAM (COORD 2026-10-25 21:21 ruling:
0 spare rows, 0 spare IO columns, no repair ports, no spare array cells) in the r2c2 FOOTPRINT with every
functional pin at its r2c2 location (PATH-S81 2325).

Why a second r0c0 master: the plain r0c0 (build_s81_vp_norepair_1025.py) is 169.368 x 29.160 um and its
default half/half pin split moves 202 functional pins (all right-edge pins, plus 16 left->right) relative to
r2c2.  A tile already placed around r2c2 (e.g. dsdv_eng_rr_e via ot_s81eng_win_n32) can drop this master in
place: same SIZE, same functional pin rects, repair pin slots simply empty.  Array/periphery/timing are the
r0c0 compile; only the outline is held at the r2c2 size (area and Liberty area reported at that outline, no
credit taken).  Existing r2c2 / r2c2_nr / r0c0 views are untouched.

PATH-S81/ENG-R0C0 2026-10-26: generalised to every SRAM shape dsdv_eng_rr_e holds with tied repair pins (COORD
2026-10-26 00:50 approval of D-S81-B2 item F): 512x128 m4 (u_win.u_h), 64x512 m1 (u_xq.u_wl/u_b0/u_b1) and
128x256 m1 (u_lkp.u_e.u_row_e/o/a).  usage: build_s81_r0c0_pc_1025.py [512x128_m4|64x512_m1|128x256_m1 ...]
(default: all three).  The 512x128 output is byte-identical to the 2325 single-shape build.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sram_gen  # noqa: E402
import views  # noqa: E402
import build_aligned_v2 as aligned  # noqa: E402

SHAPES = {"512x128_m4": (512, 128, 4), "64x512_m1": (64, 512, 1), "128x256_m1": (128, 256, 1)}


def ref_geometry(out: Path, REF, words, bits, mux):
    text = (out / REF / f"{REF}.lef").read_text()
    w, h = map(float, re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", text).groups())
    ref_spec = sram_gen.SramSpec(REF, words, bits, mux, 1, "1r1w", 2, 2)
    n_ref = sum(p.width for p in sram_gen.pins_for(ref_spec))
    return w, h, -(-n_ref // 2)          # r2c2 default split: first ceil(n/2) bits on the left edge


def build(root, shape="512x128_m4"):
    words, bits, mux = SHAPES[shape]
    REF = f"ot_sram_1r1w_{shape}_r2c2"
    NAME = f"ot_sram_1r1w_{shape}_r0c0_pc"
    root = Path(root)
    out = root / "physical/asap7_memory_macros_v2"
    W, H, left_n = ref_geometry(out, REF, words, bits, mux)
    spec = sram_gen.SramSpec(NAME, words, bits, mux, 1, "1r1w", 0, 0)
    info = {}

    def outline(core_w, core_h, pins):
        w, h, inf = aligned.aligned_outline(core_w, core_h, pins)
        if w > W + 1e-9 or h > H + 1e-9:
            raise SystemExit(f"{NAME}: r0c0 aligned outline {w}x{h} exceeds r2c2 {W}x{H}")
        inf = dict(inf)
        inf["r2c2_footprint_hold"] = {"r0c0_aligned_um": [w, h], "held_um": [W, H], "reference": REF,
                                      "note": "outline held at r2c2 SIZE for in-place swap; no area credit"}
        info.update(inf)
        return W, H, inf

    def write_lef(name, w, h, pins, props):
        bits = [(p, b) for p in pins for b in p.bits()]
        faces = (bits[:left_n], bits[left_n:])     # same edge index k as r2c2 for every functional bit
        text = views.write_lef(name, w, h, pins, props, faces=faces)
        text = text.replace("# OpenTallas memory compiler (tools/mem_compiler), ASAP7 abstract view",
                            "# OpenTallas memory compiler (tools/mem_compiler), ASAP7 abstract view, "
                            "track-aligned v2, r2c2 footprint + functional pin geometry (build_s81_r0c0_pc_1025.py)", 1)
        return aligned.drop_r90(text)

    with aligned.patched(sram_gen, macro_outline=outline, write_lef=write_lef,
                         GENERATOR_VERSION=sram_gen.GENERATOR_VERSION + "+aligned-v2+r2c2pc"):
        sheet = sram_gen.compile_macro(spec, out)
    a = sheet["area"]
    aligned.finish(out, NAME, None, (a["macro_width_um"], a["macro_height_um"]),
                   {"kind": "sram", "spec": sheet["spec"], "r2c2_footprint_hold": info.get("r2c2_footprint_hold")})
    return out / NAME


if __name__ == "__main__":
    for shape in (sys.argv[1:] or list(SHAPES)):
        print(build(Path(__file__).resolve().parents[2], shape))
