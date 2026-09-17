#!/usr/bin/env python3
"""The collector assembles the shipped programs' records, under both simulators.

``ot_a3_semantic_record_collector`` is the module that was missing between a
qualified HC_PRE engine and the first DeepSeek token.  The engines take the
128-word semantic record as one bundle and nothing in the device produced it: the
issue bridge holds the operator, numeric payload and resolved views but never sees
the SCHEDULE descriptor, the microsequencer decodes that in a state of its own, and
the views arrive later from the resolver bank.

What this establishes: driven with the REAL raw descriptors of both shipped
programs' HC_PRE dispatches -- ROM program counter 15 and HBM program counter 14 --
the collector produces exactly the 128 words ``config_words`` produces from decoded
descriptors, on both stores, under Icarus and Verilator.

Three things make that a claim rather than a coincidence:

* the expected record comes from the DECODED path, and
  ``tests/abi3/test_semantic_record.py`` separately proves the decoded and raw
  readings equal, so this cannot pass by both sides sharing a mistake about where a
  field lives;
* the field slices are GENERATED from ``runtime/abi3/descriptors.py``'s offset
  tables, so the RTL and the Python reference read one source;
* the ten non-operator descriptors are presented in a shuffled order, so a
  collector that counted arrivals or assumed the operator's field order would fail.

What it does NOT establish: that the collector is connected to anything.  It is
driven here by a bench, not by ``ot_a3_microsequencer``'s port, and no token is
produced.  Connecting it, and routing the engine's two result bundles, is the next
step and is not claimed here.
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
VECTORS = ROOT / "testdata/rtl/a3_semantic_record"
COLLECTOR = ROOT / "rtl/abi3/ot_a3_semantic_record_collector.sv"
SLICES = ROOT / "rtl/abi3/ot_a3_semantic_record_slices.svh"
BENCH = ROOT / "rtl/test/tb_a3_semantic_record_collector.sv"
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse(output: str) -> dict[str, int | bool]:
    match = re.search(
        r"A3_SEMANTIC_RECORD_SUMMARY stores=(\d+) words_checked=(\d+) errors=(\d+)",
        output,
    )
    if match is None:
        raise SystemExit(f"bench printed no summary:\n{output[-900:]}")
    return {
        "stores": int(match.group(1)),
        "words_checked": int(match.group(2)),
        "errors": int(match.group(3)),
        "pass": "PASS" in output,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "results/rtl/a3_semantic_record_collector_campaign.json",
    )
    args = parser.parse_args()

    # The generated slices must be what the ABI currently produces, or the RTL and
    # the Python reference are no longer reading one source.
    check = subprocess.run(
        [sys.executable, str(ROOT / "tools/generate_a3_semantic_record_collector.py"),
         "--check"],
        capture_output=True, text=True,
    )
    if check.returncode != 0:
        raise SystemExit(f"generated slices have drifted: {check.stderr.strip()}")

    work = Path(tempfile.mkdtemp(prefix="a3-record-collector-"))
    try:
        for source in (COLLECTOR, SLICES, BENCH):
            shutil.copy(source, work / source.name)
        for vector in sorted(VECTORS.glob("*.hex")):
            shutil.copy(vector, work / vector.name)
        sources = [str(work / COLLECTOR.name), str(work / BENCH.name)]

        subprocess.run(
            ["iverilog", "-g2012", "-I", ".", "-o", "collector.vvp", *sources],
            cwd=work, check=True, capture_output=True,
        )
        icarus = parse(
            subprocess.run(["vvp", "collector.vvp"], cwd=work, check=True,
                           capture_output=True).stdout.decode()
        )
        env = dict(os.environ)
        env["PATH"] = f"{VERILATOR}:{env.get('PATH','')}"
        subprocess.run(
            ["verilator", "--binary", "-Wno-fatal", "--timing", "-I.", "-o", "vcoll",
             *sources, "--top-module", BENCH.stem],
            cwd=work, check=True, capture_output=True, env=env,
        )
        verilator = parse(
            subprocess.run([str(work / "obj_dir" / "vcoll")], cwd=work, check=True,
                           capture_output=True, env=env).stdout.decode()
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)

    index = json.loads((VECTORS / "index.json").read_text())
    agree = icarus == verilator
    report = {
        "schema": "opentallas.a3_semantic_record_collector.v1",
        "status": "pass" if icarus["pass"] and verilator["pass"] and agree else "fail",
        "simulators_agree": agree,
        "results": {"icarus": icarus, "verilator": verilator},
        "stores": index["stores"],
        "presentation_order": index["presentation_order"],
        "establishes": [
            "the collector produces, from raw descriptor bytes, exactly the 128-word "
            "record config_words produces from decoded descriptors -- on both shipped "
            "stores and under both simulators",
            "roles are matched by descriptor identity: the ten non-operator "
            "descriptors are presented in an order that is neither role order nor "
            "the sequencer's",
            "the field slices are generated from the ABI's own offset tables, so the "
            "RTL and the Python reference cannot disagree about where a field lives",
        ],
        "does_not_establish": [
            "that the collector is connected to ot_a3_microsequencer's descriptor "
            "port: it is driven by a bench here",
            "any token, any engine execution, and any timing or area claim",
            "that a descriptor arriving before the operator is handled -- it is not, "
            "by design: the record simply never completes, because nothing can "
            "recognise a view by id before reading the descriptor that names it",
        ],
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (COLLECTOR, SLICES, BENCH, Path(__file__))
        },
        "vector_sha256": {
            path.name: sha256(path) for path in sorted(VECTORS.glob("*"))
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        f"{report['status']}: {icarus['words_checked']} words over "
        f"{icarus['stores']} stores, {icarus['errors']} errors; "
        f"simulators agree: {agree}"
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
