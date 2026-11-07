#!/usr/bin/env python3
"""HBM-FORM-SPLIT-13-OPSB 11-06: narrow bank master for ot_hgi_sfu_opsb_output (opt-in define OT_OPSB_N32).

The core banks 16 x 2048 x 32-bit words in ot_sram_1r1w_256x256_m2_r2c2 (172.824 x 41.064, 823 M4 pins on its W/E
faces: rd_out 256, wd_in 256 = {8{wd}}, w_mask_in 256) -> GRT overflow on every placement in its 760.32 x 280.8 slot
(B11 4 columns 143,100; vA 3 columns 506).  The same 64 Kb as ONE 32-bit word per address needs 92 pins.

Same builder form as tools/mem_compiler/build_hbm_rightwidth_1103.py (DIE-HBM-61 class 4 "macro channels", which made
ot_sram_1r1w_512x32_m4_r0c0_g32 for sfustore): no repair (r0c0), one mask pin (mask_gran = bits, driven 1), pin faces
"rw" (clock + read port W, write port E), v2 track alignment, its scalar-mask behavioural model and aligned.finish();
1r1w one-cycle registered read, read-before-write, rd held while r_ce = 0 - the contract of the row form.  That
builder's own 7 masters are not rebuilt (their files stay byte-identical).

    python3 -I results/die_hbm_1106/opsb_n32/macro_gen.py [--check]
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "mem_compiler"))
import sram_gen                               # noqa: E402
import build_aligned_v2 as aligned            # noqa: E402
import build_hbm_rightwidth_1103 as RW        # noqa: E402

OUT = ROOT / "physical" / "asap7_memory_macros_v2"
NAME, WORDS, BITS, MUX, GRAN = "ot_sram_1r1w_2048x32_m8_r0c0_g32", 2048, 32, 8, 32
USE = {"ot_hgi_sfu_opsb_output (OT_OPSB_N32)": 16}


def build(out: Path) -> dict:
    spec = sram_gen.SramSpec(NAME, WORDS, BITS, MUX, 1, "1r1w", 0, 0, GRAN, "rw")
    with aligned.patched(sram_gen, GENERATOR_VERSION=sram_gen.GENERATOR_VERSION + "+aligned-v2"), \
            aligned.patched(sram_gen, macro_outline=RW._aligned_outline_faces, write_lef=RW._aligned_write_lef_faces,
                            behavioural=RW._behavioural_scalar_mask):
        sheet = sram_gen.compile_macro(spec, out)
    a = sheet["area"]
    aligned.finish(out, NAME, None, (a["macro_width_um"], a["macro_height_um"]),
                   {"kind": "sram", "spec": sheet["spec"], "builder": "results/die_hbm_1106/opsb_n32/macro_gen.py",
                    "consumers": USE})
    v = aligned.verify_lef((out / NAME / f"{NAME}.lef").read_text())[NAME]
    assert v["pass"], v
    t = sheet.get("timing", {})
    return dict(name=NAME, size_um=v["size_um"], signal_pins=a["outline"]["signal_pins"],
                pins_per_edge=a["outline"]["pins_per_edge"],
                clk_to_q_ps={c: round(t[c]["clk_to_q_ps"], 1) for c in t}, setup_ps=round(t["tt"]["setup_ps"], 1),
                min_period_ps=round(t["tt"]["min_period_ps"], 1))


if __name__ == "__main__":
    if "--check" in sys.argv:
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp))
            bad = [str(f.relative_to(tmp)) for f in sorted(Path(tmp).rglob("*")) if f.is_file()
                   and (not (OUT / f.relative_to(tmp)).exists() or (OUT / f.relative_to(tmp)).read_bytes() != f.read_bytes())]
        print("CHECK", "PASS" if not bad else f"FAIL {bad[:8]}")
        sys.exit(1 if bad else 0)
    if (OUT / NAME).exists():
        shutil.rmtree(OUT / NAME)
    print(json.dumps(build(OUT)))
