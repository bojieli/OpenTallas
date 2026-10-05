#!/usr/bin/env python3
"""Gate the shared-issue, MAC-only-copy five-slot Qwen arithmetic path."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_qwen_m5_mac_reduce.sv",
    "rtl/hdc/ot_hdc_qwen_m5_mac_array.sv",
    "rtl/hdc/ot_hdc_qwen_m5_reduce_scale.sv",
    "rtl/hdc/ot_hdc_lane_copy.sv",
    "rtl/hdc/ot_hdc_fpu.sv",
    "rtl/hdc/ot_hdc_fastfp.sv",
    "rtl/hdc/ot_hdc_delay.sv",
    "rtl/hdc/ot_hdc_sfu.sv",
    "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv",
)]
TB = [ROOT / f"rtl/test/tb_hdc_qwen_m5_{name}.sv" for name in
      ("mac_array", "reduce_scale", "mac_reduce")]
OUT = ROOT / "results/rtl/hdc_qwen_m5_mac_reduce.json"


def main():
    outputs = {}
    with tempfile.TemporaryDirectory(prefix="qwen-m5-arith-") as tmp:
        for name, tb in zip(("mac_array", "reduce_scale", "mac_reduce"), TB):
            top = f"tb_hdc_qwen_m5_{name}"
            binary = Path(tmp) / f"{name}.vvp"
            subprocess.run(["iverilog", "-g2012", "-s", top, "-o", str(binary),
                            str(tb), *map(str, RTL)], cwd=ROOT, check=True)
            cp = subprocess.run(["vvp", str(binary)], cwd=ROOT, capture_output=True, text=True, check=True)
            if "PASS Qwen m5" not in cp.stdout:
                raise RuntimeError(cp.stdout)
            outputs[name] = cp.stdout.strip().splitlines()[-1]
        subprocess.run(["verilator", "--lint-only", "-Wno-fatal", "-Wno-WIDTH", "-Wno-TIMESCALEMOD",
                        "--top-module", "ot_hdc_qwen_m5_mac_reduce", *map(str, RTL)],
                       cwd=ROOT, capture_output=True, text=True, check=True)
    record = {"status": "pass", "gates": outputs,
              "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in [*RTL, *TB, Path(__file__)]},
              "claim_boundary": "One shared issue/weight stream, five MAC-only accumulations, "
                                "five parallel K-split trees and post-sum scale paths exact in reduced gates. "
                                "Input is a decoded BF16 weight; not connected to package controller, "
                                "drafter, acceptance, KV speculation, or full O4 P&R."}
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    for value in outputs.values():
        print(value)


if __name__ == "__main__":
    main()
