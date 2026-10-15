#!/usr/bin/env python3
"""Exact old registered selection + unchanged fold versus the local wrapper."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ["rtl/rom/ot_coll_local_xfold.sv", "rtl/rom/ot_coll_fold_slice.sv", "rtl/rom/ot_coll_rst_leaf.sv",
           "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fastfp.sv",
           "rtl/rom/ot_coll_tp8_static.sv", "tools/qwen_coll_local_xfold/tb.sv", "tools/qwen_coll_local_xfold/run.py"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    pins = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCES}
    original = (ROOT / SOURCES[6]).read_text()
    rep = re.search(r"(?ms)^\(\* keep_hierarchy = 1 \*\) module ot_coll_rep_reg\b.*?\bendmodule", original)
    if rep is None:
        raise ValueError("actual selector-register module changed")
    # The reference's rank law must still be the literal selected parent law.
    for token in ("2'(gq) - pkg_s + 2'd3", "gq*FW + gr*128 +: 128", ".RST(0)"):
        if token not in original:
            raise ValueError("actual parent rank-selection source changed")
    runs = []
    with tempfile.TemporaryDirectory(prefix="local-xfold-") as directory:
        directory = Path(directory)
        rep_path = directory / "actual_rep_reg.sv"
        rep_path.write_text(rep.group(0) + "\n")
        (out / "actual_rep_reg.sv").write_text(rep.group(0) + "\n")
        for mutant in (0, 1):
            name = "positive" if mutant == 0 else "wrong_rank"
            binary = directory / (name + ".vvp")
            command = ["iverilog", "-g2012", "-s", "tb", f"-Ptb.MUT={mutant}", "-o", str(binary),
                       str(ROOT / SOURCES[7]), str(rep_path), *[str(ROOT / path) for path in SOURCES[:6]]]
            result = subprocess.run(command, capture_output=True, text=True)
            (out / (name + ".compile.log")).write_text(result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError(name + " compile failed")
            binary_pin = hashlib.sha256(binary.read_bytes()).hexdigest()
            result = subprocess.run(["vvp", str(binary)], capture_output=True, text=True)
            (out / (name + ".log")).write_text(result.stdout + result.stderr)
            observed = re.search(r"LOCAL_XFOLD MUT=(\d+) samples=(\d+) data_errors=(\d+) valid_errors=(\d+) error_errors=(\d+) errors=(\d+)", result.stdout)
            if observed is None:
                raise RuntimeError(name + " missing measured result")
            fields = dict(zip(("mutant", "samples", "data_errors", "valid_errors", "error_errors", "errors"), map(int, observed.groups())))
            ok = (fields["samples"] == 448 and fields["valid_errors"] == 0 and
                  ((mutant == 0 and result.returncode == 0 and fields["errors"] == 0) or
                   (mutant == 1 and result.returncode != 0 and fields["data_errors"] > 0)))
            runs.append(dict(name=name, exit=result.returncode, binary_sha256=binary_pin, observed=fields, ok=ok))
    receipt = dict(schema="opentallas.qwen.local_xfold_component.v1", source_pins=pins,
                   inputs="4 x 128-bit raw words; pkg straps0..3, resets, bubbles, full-rate words, FP32 cancellation/special/subnormal cases",
                   scope="Old real registered selectors + real ot_coll_fold_slice versus new local wrapper, common-phase control/fold clocks; no physical qualification",
                   extra_data_edges=0, expected_red_sampling_edges=23, compared_output_words=448,
                   actual_fold_master_unchanged=True, clocks=["ctl_ck", "fold_ck"], runs=runs,
                   ok=all(run["ok"] for run in runs))
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(runs, indent=2), flush=True)
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
