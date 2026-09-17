#!/usr/bin/env python3
"""HC_PRE executing on a record the collector assembled, under both simulators.

``tb_a3_hc_pre_t1`` drives ``ot_a3_hc_pre_t1_descriptor_rne`` from ``config_words``
read out of a vector file.  That proves the engine's arithmetic and says nothing
about where such a record comes from in a device -- and nothing in the device
produced one, which is why the engine sat off the token path.

This runs the chain:

    raw descriptors -> ot_a3_semantic_record_collector -> 128-word record
                    -> ot_a3_hc_pre_t1_descriptor_rne -> coefficients

with the raw descriptors of the shipped ROM program's HC_PRE dispatch (program
counter 15, operator 381) and the coefficients compared against the same expected
vector the engine's own campaign uses.  Nothing between the descriptor bytes and the
result is hand-assembled.

What it establishes: the collector's record is one the engine accepts and computes
the right answer from, on both simulators.  The two were previously checked against
a golden separately, which does not rule out their disagreeing with each other.

What it does NOT establish: any token.  The microsequencer is not in this bench, so
the collector is fed a descriptor stream rather than tapping a live fetch port; the
engine's two result bundles are compared here rather than emitted into a result bank;
and one operator of one layer is not a model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "rtl/test/tb_a3_hc_pre_collected.sv"
SLICES = ROOT / "rtl/abi3/ot_a3_semantic_record_slices.svh"
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin"

SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/ot_fp32_rsqrt_rne.sv",
    "rtl/abi3/ot_a3_hc_projection_pkg.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_hc_stable_softmax_rne.sv",
    "rtl/abi3/ot_a3_hc_sinkhorn20_rne.sv",
    "rtl/abi3/ot_a3_hc_stable_softmax_sinkhorn20_rne.sv",
    "rtl/abi3/ot_a3_vector_mhc_pre_tile_scheduler.sv",
    "rtl/abi3/ot_a3_hc_projection_rms_rne.sv",
    "rtl/abi3/ot_a3_hc_coefficients_rne.sv",
    "rtl/abi3/ot_a3_hc_pre_t1_descriptor_rne.sv",
    "rtl/abi3/ot_a3_semantic_record_collector.sv",
    "rtl/test/tb_a3_hc_pre_collected.sv",
)
VECTORS = {
    "HIDDEN": "testdata/rtl/a3_hc_pre_t1_checkpoint/hidden.hex",
    "PROJECTION": "testdata/rtl/a3_hc_pre_t1_checkpoint/projection.hex",
    "BASE": "testdata/rtl/a3_hc_pre_t1_checkpoint/base.hex",
    "SCALE": "testdata/rtl/a3_hc_pre_t1_checkpoint/scale.hex",
    "EXPECTED": "testdata/rtl/a3_hc_pre_t1/expected.hex",
    "ROM_META": "testdata/rtl/a3_semantic_record/rom_meta.hex",
    "ROM_DESC": "testdata/rtl/a3_semantic_record/rom_descriptors.hex",
}
SUMMARY = re.compile(r"A3_HC_PRE_COLLECTED_SUMMARY checks=(\d+) errors=(\d+)")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse(output: str) -> dict[str, int | bool]:
    match = SUMMARY.search(output)
    if match is None:
        raise SystemExit(f"bench printed no summary:\n{output[-900:]}")
    return {
        "checks": int(match.group(1)),
        "errors": int(match.group(2)),
        "pass": "PASS" in output,
    }


def plusargs() -> list[str]:
    return [f"+{name}={ROOT / path}" for name, path in sorted(VECTORS.items())]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "results/rtl/a3_hc_pre_collected_campaign.json",
    )
    args = parser.parse_args()

    drift = subprocess.run(
        [sys.executable, str(ROOT / "tools/generate_a3_semantic_record_collector.py"),
         "--check"], capture_output=True, text=True,
    )
    if drift.returncode != 0:
        raise SystemExit(f"generated slices have drifted: {drift.stderr.strip()}")

    work = Path(tempfile.mkdtemp(prefix="a3-hc-pre-collected-"))
    try:
        shutil.copy(SLICES, work / SLICES.name)
        sources = [str(ROOT / name) for name in SOURCES]
        subprocess.run(
            ["iverilog", "-g2012", "-I", ".", "-o", "collected.vvp", *sources],
            cwd=work, check=True, capture_output=True,
        )
        icarus = parse(
            subprocess.run(["vvp", "collected.vvp", *plusargs()], cwd=work,
                           check=True, capture_output=True).stdout.decode()
        )
        env = dict(os.environ)
        env["PATH"] = f"{VERILATOR}:{env.get('PATH','')}"
        subprocess.run(
            ["verilator", "--binary", "-Wno-fatal", "--timing", "-I.", "-o", "vcollected",
             *sources, "--top-module", BENCH.stem],
            cwd=work, check=True, capture_output=True, env=env,
        )
        verilator = parse(
            subprocess.run([str(work / "obj_dir" / "vcollected"), *plusargs()],
                           cwd=work, check=True, capture_output=True,
                           env=env).stdout.decode()
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)

    agree = icarus == verilator
    report = {
        "schema": "opentallas.a3_hc_pre_collected.v1",
        "status": "pass" if icarus["pass"] and verilator["pass"] and agree else "fail",
        "simulators_agree": agree,
        "results": {"icarus": icarus, "verilator": verilator},
        "chain": (
            "raw descriptors -> ot_a3_semantic_record_collector -> 128-word record "
            "-> ot_a3_hc_pre_t1_descriptor_rne -> 8 weight and 16 combination "
            "coefficients"
        ),
        "establishes": [
            "the engine accepts the record the collector assembles and computes the "
            "expected coefficients from it, on the shipped ROM program's HC_PRE "
            "dispatch (program counter 15, operator 381)",
            "the arithmetic counters hold on a collected record: 393,216 fused "
            "accumulations and 16,383 balanced reduction adds",
            "both simulators agree",
        ],
        "does_not_establish": [
            "any token: one operator of one layer is not a model",
            "that the collector taps a live fetch port -- ot_a3_microsequencer is "
            "not in this bench and the descriptor stream is driven by it",
            "that the engine's results reach a result bank: they are compared here, "
            "not emitted",
            "any timing, area or throughput claim",
        ],
        "source_sha256": {
            name: sha256(ROOT / name) for name in (*SOURCES, "tools/run_a3_hc_pre_collected_campaign.py")
        },
        "vector_sha256": {
            name: sha256(ROOT / path) for name, path in sorted(VECTORS.items())
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        f"{report['status']}: {icarus['checks']} checks, {icarus['errors']} errors; "
        f"simulators agree: {agree}"
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
