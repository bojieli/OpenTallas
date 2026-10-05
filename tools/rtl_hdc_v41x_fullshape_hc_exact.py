#!/usr/bin/env python3
"""Checkpoint-backed layer-0 HC attention projection through full-depth HE RTL."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import tempfile
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RTL = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_delay.sv",
    "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/v41/ot_hdc_fdiv.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_hcp.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_he_adapt.sv",
    "rtl/test/tb_hdc_v41x_fullshape_hc_exact.sv")]
PAT = re.compile(r"HC_PASS exact_rows=(\d+) bank_read_cycles=(\d+) cycles=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cap_memory() -> None:
    limit = 16 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def run(x: Path, y: Path, image: Path, golden_manifest: Path,
        layout_manifest: Path, output: Path) -> dict:
    golden = json.loads(golden_manifest.read_text())
    layout = json.loads(layout_manifest.read_text())
    if (golden.get("schema") != "opentallas.rtl.v41_fullshape_hc_attn_vectors.v1"
            or golden.get("context") != 200000 or golden.get("layer") != 0
            or golden.get("rank") != 0 or golden.get("operation") != "hc_attn_fn"):
        raise ValueError("wrong checkpoint HC golden manifest")
    if sha(x) != golden["x"]["sha256"] or sha(y) != golden["y_raw"]["sha256"]:
        raise ValueError("checkpoint HC x/y binary hash mismatch")
    matrix = layout["matrices"]["hc_attn_fn"]
    if (matrix["source_weight_sha256"] != golden["weight_image_sha256"]
            or matrix["output_image_sha256"] != sha(image)
            or matrix["base_word"] != 0 or matrix["word_count"] != 7680
            or image.stat().st_size != 1_966_080):
        raise ValueError("packed HE image does not bind to checkpoint HC weight")
    xb = np.fromfile(x, dtype="<u4")
    yb = np.fromfile(y, dtype="<u4")
    if xb.size != 20480 or yb.size != 24 or np.any(xb & np.uint32(0xffff)):
        raise ValueError("HC x/y shape or BF16 input contract mismatch")
    with tempfile.TemporaryDirectory(prefix="v41_hc_exact_") as tmp:
        tmp = Path(tmp)
        (tmp / "x.hex").write_text("".join(f"{int(v):08x}\n" for v in xb))
        (tmp / "y.hex").write_text("".join(f"{int(v):08x}\n" for v in yb))
        os.symlink(image.resolve(), tmp / "hc_attn_fn.he.bin")
        obj = tmp / "obj"
        verilator = str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator")
        command = [verilator, "--binary", "--timing", "-O0", "-Wno-fatal", "-Wno-WIDTH",
                   "-Wno-UNUSED", "-Wno-TIMESCALEMOD", "--top-module",
                   "tb_hdc_v41x_fullshape_hc_exact", "-Mdir", str(obj),
                   *map(str, RTL), "-CFLAGS", "-O0", "-j", "4"]
        t0 = time.monotonic()
        build = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                               timeout=600, preexec_fn=cap_memory)
        if build.returncode:
            raise RuntimeError("HE bench build failed:\n" + build.stderr[-3000:])
        build_sec = round(time.monotonic() - t0, 2)
        t1 = time.monotonic()
        sim = subprocess.run([str(obj / "Vtb_hdc_v41x_fullshape_hc_exact"), f"+DIR={tmp}"],
                             cwd=ROOT, capture_output=True, text=True,
                             timeout=600, preexec_fn=cap_memory)
        match = PAT.search(sim.stdout)
        if sim.returncode or not match:
            raise RuntimeError("HE bench failed:\n" + sim.stdout[-3000:] + sim.stderr[-2000:])
        rows, reads, cycles = map(int, match.groups())
        if rows != 24 or reads < 24 * 320:
            raise RuntimeError("HE bench coverage mismatch: " + match.group(0))
        sim_sec = round(time.monotonic() - t1, 2)
        record = {
            "schema": "opentallas.rtl.v41x_fullshape_hc_attn_exact.v1",
            "status": "pass",
            "claim_scope": "200K context, layer-0 rank-0 HC attention projection: all 24 raw "
                           "FP32 rows bit-exact against checkpoint golden through the full-depth "
                           "HE adapter and packed ROM image. No full-layer, token or chip-rate claim.",
            "input_elements": 20480, "exact_rows": rows, "he_k_chunks": 2560,
            "bank_read_cycles": reads, "simulation_cycles": cycles,
            "build_seconds": build_sec, "simulation_seconds": sim_sec,
            "memory_cap_bytes": 16 * 1024**3,
            "fixture_sha256": {str(p): sha(p) for p in
                               (x, y, image, golden_manifest, layout_manifest)},
            "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (*RTL, Path(__file__))},
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n")
    return record


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--x", type=Path, required=True)
    ap.add_argument("--y", type=Path, required=True)
    ap.add_argument("--image", type=Path, required=True)
    ap.add_argument("--golden-manifest", type=Path, required=True)
    ap.add_argument("--layout-manifest", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=ROOT / "results/rtl/hdc_v41x_fullshape_hc_attn_exact.json")
    args = ap.parse_args()
    print(json.dumps(run(args.x, args.y, args.image, args.golden_manifest,
                         args.layout_manifest, args.output), indent=2))


if __name__ == "__main__":
    main()
