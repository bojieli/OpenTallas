#!/usr/bin/env python3
"""Reduced exact embedding path: INT8 code ROM, BF16 row scale, FP32 VM."""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_isa as I  # noqa: E402
import hdc_program as P  # noqa: E402
import rtl_hdc_decode_campaign as C  # noqa: E402
from hdc_qwen_int8_image import Int8Layout, write_images  # noqa: E402


def main():
    model = G.Model(P.GR, 2)
    layout = Int8Layout(model, 2, 0)
    program = P.build_program(layout)
    assert program[0]["unit"] == I.UNIT_SU and program[0]["a_src"] == I.SRC_ALT
    with tempfile.TemporaryDirectory(prefix="qwen_embed_core_") as dirname:
        out = Path(dirname)
        write_images(layout, out)
        instructions = [program[0], {"unit": I.UNIT_END, "barrier": 1}]
        (out / "prog_embed.hex").write_text(P.hexwords(
            (I.encode(**{k: v for k, v in inst.items() if not k.startswith("_")}) for inst in instructions),
            I.INSTR_BITS))
        scale = G.from_bits(np.uint32(layout.embed_scales[0]) << np.uint32(16))
        actual = layout.embed_codes[0].view(np.int8).astype(np.float32) * np.float32(scale)
        (out / "expect_embed.hex").write_text(P.hexwords(G.bits(actual), 32))
        tb = ROOT / "rtl/test/tb_hdc_qwen_int8_embed_core.sv"
        decoder = ROOT / "rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv"
        core = ROOT / "rtl/hdc/ot_hdc_core_vector_weight.sv"
        binary = out / "sim.vvp"
        sources = [*C.HDC, *C.PIPES, decoder, core, tb]
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_int8_embed_core",
                        f"-Ptb_hdc_qwen_int8_embed_core.EMB_BASE={layout.emb_word * P.W * P.GR}",
                        "-Irtl/hdc", "-o", str(binary), *map(str, sources)], cwd=ROOT, check=True)
        result = subprocess.run(["vvp", str(binary), f"+DIR={out}"], capture_output=True, text=True)
        print(result.stdout.strip())
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "INT8 embedding core gate failed")


if __name__ == "__main__":
    main()
