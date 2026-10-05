#!/usr/bin/env python3
"""Gate independent INT8 code/scale ISA bases at reduced shape."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / p for p in (
    "rtl/test/tb_hdc_qwen_int8_matvec.sv",
    "rtl/hdc/ot_hdc_matvec.sv",
    "rtl/hdc/ot_hdc_fpu.sv",
    "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
    "rtl/hdc/ot_hdc_fastfp.sv",
    "rtl/hdc/ot_hdc_delay.sv",
    "rtl/hdc/ot_hdc_sfu.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv",
    "rtl/hdc/ot_hdc_core_vector_weight.sv",
    "rtl/hdc/hbm/ot_hdc_qwen_int8_pc_window.sv",
    "rtl/test/tb_hdc_qwen_int8_pc_window.sv",
    "tools/rtl_hdc_qwen_int8_scale_base.py",
)]
OUT = ROOT / "results/rtl/qwen_int8_scale_base.json"


def main():
    gates = {}
    with tempfile.TemporaryDirectory(prefix="qwen_int8_scale_base_") as tmp:
        for split in (0, 1):
            for separate in (0, 1):
                binary = Path(tmp) / f"s{split}_b{separate}.vvp"
                subprocess.run([
                    "iverilog", "-g2012", "-s", "tb_hdc_qwen_int8_matvec",
                    f"-Ptb_hdc_qwen_int8_matvec.SPLIT={split}",
                    f"-Ptb_hdc_qwen_int8_matvec.SCALE_SEPARATE={separate}",
                    "-o", str(binary), *map(str, SOURCES[0:8]),
                ], cwd=ROOT, check=True, capture_output=True, text=True)
                run = subprocess.run(["vvp", str(binary)], cwd=ROOT, check=True,
                                     capture_output=True, text=True)
                if f"PASS Qwen INT8 matvec split={split}" not in run.stdout:
                    raise RuntimeError(run.stdout)
                gates[f"split{split}_separate{separate}"] = run.stdout.strip()
    record = {
        "schema": "opentallas.qwen-int8-scale-base.v1",
        "status": "pass",
        "gates": gates,
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in SOURCES},
        "claim_boundary": "Reduced G2 INT8 matrix op, two K-split modes and two ISA scale-base modes. Separate ME_WCS code/scale addressing is proven bit-exact against shared-base arithmetic at this shape; full G6144 token, HBM controller, and P&R remain unverified.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"{OUT}: pass")


if __name__ == "__main__":
    main()
