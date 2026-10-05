#!/usr/bin/env python3
"""Source-pinned five-slot INT8 shared-weight matrix verify gate."""
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / p for p in (
    "rtl/test/tb_hdc_qwen_m5_verify_array.sv",
    "rtl/hdc/ot_hdc_qwen_m5_verify_array.sv",
    "rtl/hdc/ot_hdc_matvec.sv",
    "rtl/hdc/ot_hdc_fpu.sv",
    "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
    "rtl/hdc/ot_hdc_fastfp.sv",
    "rtl/hdc/ot_hdc_delay.sv",
    "rtl/hdc/ot_hdc_sfu.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv",
    "tools/rtl_hdc_qwen_m5_verify.py",
)]
OUT = ROOT / "results/rtl/hdc_qwen_m5_verify.json"


def main():
    with tempfile.TemporaryDirectory(prefix="qwen-m5-verify-") as tmp:
        binary = Path(tmp) / "m5.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_m5_verify_array",
                        "-o", str(binary), *map(str, SOURCES[:-1])], cwd=ROOT, check=True)
        cp = subprocess.run(["vvp", str(binary)], cwd=ROOT, capture_output=True, text=True, check=True)
    m = re.search(r"PASS Qwen INT8 m5 shared-weight verify: (\d+) slots, (\d+) weight reads, "
                  r"(\d+) scale reads, (\d+) result cycles", cp.stdout)
    if not m:
        raise RuntimeError(cp.stdout)
    slots, weights, scales, results = map(int, m.groups())
    assert (slots, weights, scales, results) == (5, 16, 8, 8)
    record = {"status": "pass", "slots": slots, "matrix_weight_reads": weights,
              "matrix_scale_reads": scales, "result_cycles": results,
              "separate_slot_weight_reads_if_unshared": slots * weights,
              "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in SOURCES},
              "claim_boundary": "Five synchronized INT8 matvec slots share one ROM word and scale response; "
                                "distinct activations and post-scale outputs exact in a reduced gate. "
                                "No draft, acceptance, KV speculation, commit controller, package gate or P&R."}
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(cp.stdout.strip())


if __name__ == "__main__":
    main()
