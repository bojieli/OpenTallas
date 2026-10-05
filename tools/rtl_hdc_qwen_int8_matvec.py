"""Run the reduced Qwen INT8 matrix engine's scale and argmax gates."""
from __future__ import annotations

import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCES = [
    "rtl/test/tb_hdc_qwen_int8_matvec.sv",
    "rtl/hdc/ot_hdc_matvec.sv",
    "rtl/hdc/ot_hdc_fpu.sv",
    "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
    "rtl/hdc/ot_hdc_fastfp.sv",
    "rtl/hdc/ot_hdc_delay.sv",
    "rtl/hdc/ot_hdc_sfu.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv",
]


def main():
    with tempfile.TemporaryDirectory(prefix="qwen-int8-matvec-") as scratch:
        for split in (0, 1):
            executable = pathlib.Path(scratch) / f"split{split}.vvp"
            subprocess.run(
                ["iverilog", "-g2012", "-s", "tb_hdc_qwen_int8_matvec",
                 f"-Ptb_hdc_qwen_int8_matvec.SPLIT={split}", "-o", str(executable),
                 *[str(ROOT / source) for source in SOURCES]],
                check=True,
            )
            result = subprocess.run(["vvp", str(executable)], capture_output=True, text=True, check=True)
            assert f"PASS Qwen INT8 matvec split={split}" in result.stdout, result.stdout
            print(result.stdout.strip())


if __name__ == "__main__":
    main()
