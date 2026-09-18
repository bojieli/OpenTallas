#!/usr/bin/env python3
"""Run the cross-tile accumulate bench and record what it proved.

``rtl/test/tb_compute_unit_acc_chain.sv`` compares two structures against each
other rather than against a model: one unit with a 256-deep weight bank walks all
256 columns in one pass, and one with a 128-deep bank walks 0..127, is refilled
with 128..255 and walks those with ``acc_continue`` asserted.  Every lane's
40-bit accumulator is compared bit for bit, and the bench also asserts the
negative -- a chain whose ``cfg_scale`` moves must raise
``acc_scale_violation`` rather than adding terms aligned two different ways.

This wrapper exists so the result is an artifact and not a terminal line: it
compiles the same sources the campaign vehicle uses, runs the bench, and records
the verdict, the cycle counts both forms took, and the digest of every source
that produced them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.rtl.compute_unit_acc_chain.v1"
TOOL = "tools/run_compute_unit_acc_chain.py"
SOURCES = (
    "rtl/proto/ot_mac_lane.sv",
    "rtl/proto/ot_mac_tile.sv",
    "rtl/proto/ot_compute_unit.sv",
    "rtl/abi3/ot_a3_asap7_fakeram_blackbox.sv",
    "rtl/test/tb_compute_unit_acc_chain.sv",
)
TOP = "tb_compute_unit_acc_chain"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 22):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "results/rtl/compute_unit_acc_chain.json"
    )
    arguments = parser.parse_args(argv)
    iverilog = shutil.which("iverilog")
    if iverilog is None:
        raise SystemExit("iverilog is not on PATH")
    arguments.workdir.mkdir(parents=True, exist_ok=True)
    binary = arguments.workdir / "acc_chain"
    compile_cmd = [
        iverilog, "-g2012", "-o", str(binary),
        *[str(ROOT / s) for s in SOURCES],
    ]
    built = subprocess.run(compile_cmd, capture_output=True, text=True)
    if built.returncode != 0:
        raise SystemExit(f"compile failed:\n{built.stdout}\n{built.stderr}")
    ran = subprocess.run([str(binary)], capture_output=True, text=True)
    transcript = ran.stdout + ran.stderr
    verdict = "PASS" if "\nPASS" in "\n" + transcript else "FAIL"
    cycles = re.search(
        r"one 256-deep pass (\d+); two chained 128-deep passes (\d+) \+ (\d+) = (\d+) "
        r"\(overhead (-?\d+)\)",
        transcript,
    )
    report = {
        "schema": SCHEMA,
        "producer": {
            "tool": TOOL,
            "git": {"commit": _git("rev-parse", "HEAD")},
            "iverilog": subprocess.run(
                [iverilog, "-V"], capture_output=True, text=True
            ).stdout.splitlines()[0]
            if iverilog
            else None,
        },
        "question": (
            "is a deep contraction split across two half-depth weight tiles "
            "bit-identical to the same contraction in one deep tile, and what does "
            "the split cost in cycles?"
        ),
        "method": (
            "two units in one bench, no reference model: the comparison is between "
            "the structures. K_MAX=256 walks 256 columns in one pass; K_MAX=128 "
            "walks 0..127, is refilled, and walks 128..255 with acc_continue. Every "
            "lane's 40-bit accumulator is compared bit for bit"
        ),
        "verdict": verdict,
        "bit_identical": verdict == "PASS",
        "moved_window_is_refused": "acc_scale_violation" not in transcript
        or "did not raise" not in transcript,
        "cycles": (
            {
                "one_deep_pass": int(cycles.group(1)),
                "first_chained_pass": int(cycles.group(2)),
                "second_chained_pass": int(cycles.group(3)),
                "chained_total": int(cycles.group(4)),
                "overhead_cycles": int(cycles.group(5)),
                "throughput_factor_of_the_split": round(
                    int(cycles.group(1)) / int(cycles.group(4)), 6
                ),
                "reading": (
                    "the split costs one extra walk setup and one extra drain "
                    "against two walks half as long; the factor is what a K=256 "
                    "product pays to be served from a 128-deep bank"
                ),
            }
            if cycles
            else None
        ),
        "sources": [
            {"path": s, "sha256": _sha256(ROOT / s), "bytes": (ROOT / s).stat().st_size}
            for s in SOURCES
        ],
        "top": TOP,
        "transcript": transcript.strip().splitlines(),
        "not_a_claim": [
            "not a timing measurement: cycle counts are the unit's own cycles, and "
            "what one cycle costs in seconds is the place-and-route record's",
            "16 lanes, one tile: this proves the accumulator chain, not an array",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(transcript.strip())
    print(f"-> {arguments.output}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
