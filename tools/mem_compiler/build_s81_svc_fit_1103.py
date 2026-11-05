#!/usr/bin/env python3
"""S81 svc memory fit (MEM v2, 2026-11-03): right-sized no-repair 1R1W masters for the svc closure children.

LAND 4 banks x 3 writers use 160 of 256 rows -> 160x256; attention staging lanes are 160 x 265 -> one 160x265
per lane instead of 2 x 256x256; PMEM banks use all 256 rows but need no 2:1 column mux -> 256x256 m1.
Same compiler and aligned-v2 outline rules as every other v2 view; no existing view is changed.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sram_gen, build_aligned_v2 as aligned

SPECS = [("ot_sram_1r1w_160x256_m1_r0c0", 160, 256, 1), ("ot_sram_1r1w_160x265_m1_r0c0", 160, 265, 1),
         ("ot_sram_1r1w_256x256_m1_r0c0", 256, 256, 1),
         # idx fit (svc_lo dsdv_idx_rg3): h0 rows < 768 by construction; iq / sq full 1024 depth at their data width;
         # mq = metadata ring read EL+KR-1 = 123 behind the write, equivalent mod 128 -> 128 x 23
         ("ot_sram_1r1w_768x256_m2_r0c0", 768, 256, 2), ("ot_sram_1r1w_1024x35_m4_r0c0", 1024, 35, 4),
         ("ot_sram_1r1w_1024x39_m4_r0c0", 1024, 39, 4), ("ot_sram_1r1w_128x23_m1_r0c0", 128, 23, 1)]


def build(root, names=None):
    out = Path(root) / "physical/asap7_memory_macros_v2"
    done = []
    for name, words, bits, mux in SPECS:
        if names and name not in names:
            continue
        spec = sram_gen.SramSpec(name, words, bits, mux, 1, "1r1w", 0, 0)
        with aligned.patched(sram_gen, macro_outline=aligned.aligned_outline, write_lef=aligned.aligned_write_lef,
                             GENERATOR_VERSION=sram_gen.GENERATOR_VERSION + "+aligned-v2"):
            sheet = sram_gen.compile_macro(spec, out)
        a = sheet["area"]
        aligned.finish(out, name, None, (a["macro_width_um"], a["macro_height_um"]), {"kind": "sram", "spec": sheet["spec"]})
        done.append((name, a["macro_width_um"], a["macro_height_um"], sheet["timing"]["tt"]["clk_to_q_ps"]))
    return done


if __name__ == "__main__":
    for r in build(Path(__file__).resolve().parents[2], sys.argv[1:]):
        print("%s %.3f x %.3f clk_q_tt %.0f" % r)
