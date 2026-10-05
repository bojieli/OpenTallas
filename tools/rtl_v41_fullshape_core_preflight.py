#!/usr/bin/env python3
"""Source-pinned, bounded full-width V4.1 core lint and layer-0 ISA gate.

The full attention engine is disabled for this preflight. This checks field
widths and elaboration only; it does not claim a bit-exact full-shape token.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as isa  # noqa: E402
import hdc_replay_v41 as replay  # noqa: E402
import rtl_hdc_v41x_decode_campaign as campaign  # noqa: E402


def _cap() -> None:
    limit = 28 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def run(output: Path) -> dict:
    program = replay.build_tp_layer0()
    words = [isa.encode(full_shape=True, **fields) for fields in program]
    assert len(words) == len(program)
    collectives = [fields for fields in program if fields["unit"] == isa.UNIT_COLL]
    assert len(collectives) == 12
    assert [fields["coll_seq"] for fields in collectives] == list(range(12))
    verilator = os.environ.get("OT_VERILATOR", str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
    source_paths = list(campaign.rtl_sources(False)) + [
        ROOT / "rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv"
    ]
    cmd = [verilator, "--lint-only", "-Wno-fatal", "-Wno-TIMESCALEMOD", "--top-module",
           "ot_hdc_core_v41x", "-GFULL_SHAPE=1", "-GKV_HBM=1", "-GX_ATT=0", "-GX_IDX=0",
           "-GX_SEL=0", "-GX_EG=0", f"-I{campaign.SVH.parent}",
           *map(str, source_paths)]
    try:
        result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                                timeout=300, preexec_fn=_cap)
        status = "pass" if result.returncode == 0 else "fail"
        errors = [line for line in result.stderr.splitlines() if line.startswith("%Error")]
        warnings = [line for line in result.stderr.splitlines() if line.startswith("%Warning")]
        returncode = result.returncode
    except subprocess.TimeoutExpired:
        status, errors, warnings, returncode = "timeout", ["lint timed out after 300 s"], [], None
    pins = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(set(source_paths + [Path(__file__), ROOT / "tools/hdc_isa_v41.py",
                                                   ROOT / "tools/hdc_replay_v41.py",
                                                   ROOT / "rtl/hdc/v41/ot_hdc_isa_v41_profiles.svh"]))}
    rec = {
        "schema": "opentallas.rtl.v41_fullshape_core_preflight.v1",
        "status": status,
        "claim_scope": "Full-width ISA and core lint with KV_HBM and the packed window block "
                       "boundary enabled, X_ATT/X_IDX/X_SEL/X_EG disabled; no full-shape "
                       "bit-exact layer or chip cycle measurement",
        "full_layer_ready": False,
        "full_layer_blockers": [
            "The TP emitter now addresses attention's local rows 0..639, but die prefetch still needs "
            "128 FP8 window rows (528 bytes each), up to 512 selected CKV FP4 rows (288 bytes each), "
            "and explicit selected source IDs",
            "A checkpoint-backed rank-0 weight/KV input image exists, but the TP ISA has no placed "
            "program image or bit-exact RTL shard yet; the 192-block QE lane is separately gated",
            "Die collective and packed KV ports have no executed full-shape integration gate",
        ],
        "program": {"layer": 0, "instructions": len(program), "collectives": len(collectives),
                    "encoded_words": len(words), "tp": replay.SHIPPED["tp"]},
        "lint": {"returncode": returncode, "memory_cap_bytes": 28 * 1024**3,
                 "timeout_seconds": 300, "top": "ot_hdc_core_v41x",
                 "parameters": {"FULL_SHAPE": 1, "KV_HBM": 1, "X_ATT": 0, "X_IDX": 0, "X_SEL": 0, "X_EG": 0},
                 "errors": errors, "warning_count": len(warnings)},
        "source_sha256": pins,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rec, indent=2) + "\n")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=ROOT / "results/rtl/hdc_v41x_fullshape_core_preflight.json")
    args = ap.parse_args()
    rec = run(args.output)
    print(json.dumps({"status": rec["status"], "program": rec["program"],
                      "warning_count": rec["lint"]["warning_count"]}))
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
