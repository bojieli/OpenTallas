#!/usr/bin/env python3
"""Fail-closed comparison of full-shape V4.1 layer RTL artifacts with golden shards.

The golden side is produced by ``rtl_v41_fullshape_layer_campaign.py``.  An RTL
runner writes ``ctx{context}_L{layer:02d}.npz`` with the same named arrays and
a JSON file with context, layer, position, cycles, golden_input_sha256, and
source_sha256 (repo-relative source path -> SHA256).  The RTL file may contain
extra diagnostic arrays.  Float arrays are compared as bytes, including NaN
payloads and signed zero.  This tool does not simulate RTL or infer throughput.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def _digest(*arrs: np.ndarray) -> str:
    """Match the full-shape golden campaign's FP32 digest contract."""
    h = hashlib.sha256()
    for arr in arrs:
        h.update(np.ascontiguousarray(np.asarray(arr, dtype=np.float32)).tobytes())
    return h.hexdigest()


def _read_pair(directory: Path, context: int, layer: int):
    stem = f"ctx{context}_L{layer:02d}"
    meta = json.loads((directory / f"{stem}.json").read_text())
    with np.load(directory / f"{stem}.npz", allow_pickle=False) as archive:
        arrays = {key: archive[key].copy() for key in archive.files}
    return meta, arrays


def compare_layer(golden_dir: Path, rtl_dir: Path, context: int, layer: int,
                  source_root: Path) -> dict:
    golden, ga = _read_pair(golden_dir, context, layer)
    rtl, ra = _read_pair(rtl_dir, context, layer)
    _validate_golden(golden, ga, context, layer, source_root)
    for name, record in (("golden", golden), ("rtl", rtl)):
        if (record.get("context"), record.get("layer"), record.get("position")) != (
                context, layer, context - 1):
            raise ValueError(f"{name} shard identity/position mismatch")
    required = {"h_in", "pre_in", "h_out", "pre_out"}
    if not required <= ga.keys():
        raise ValueError(f"golden lacks required arrays: {sorted(required - ga.keys())}")
    if rtl.get("golden_input_sha256") != golden["input_sha256"]:
        raise ValueError("RTL did not consume this golden input")
    cycles = rtl.get("cycles")
    if type(cycles) is not int or cycles <= 0:
        raise ValueError("RTL shard needs a positive integer simulated cycle count")
    pins = rtl.get("source_sha256")
    if not isinstance(pins, dict) or not pins:
        raise ValueError("RTL shard needs nonempty source_sha256 pins")
    for rel, digest in pins.items():
        path = Path(rel)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError(f"unsafe source path: {rel}")
        if hashlib.sha256((source_root / path).read_bytes()).hexdigest() != digest:
            raise ValueError(f"RTL source pin stale: {rel}")
    missing = ga.keys() - ra.keys()
    if missing:
        raise ValueError(f"RTL omitted golden arrays: {sorted(missing)}")
    for key, expected in ga.items():
        actual = ra[key]
        if expected.dtype != actual.dtype or expected.shape != actual.shape:
            raise ValueError(f"{key}: dtype/shape mismatch: {actual.dtype}/{actual.shape} vs "
                             f"{expected.dtype}/{expected.shape}")
        if expected.tobytes(order="C") != actual.tobytes(order="C"):
            raise ValueError(f"{key}: bit mismatch")
    return {"context": context, "layer": layer, "cycles": cycles,
            "golden_input_sha256": golden["input_sha256"],
            "golden_output_sha256": golden["output_sha256"],
            "matched_arrays": sorted(ga), "source_sha256": pins, "status": "bit_exact"}


def _validate_golden(golden: dict, arrays: dict, context: int, layer: int,
                     source_root: Path) -> None:
    if (golden.get("context"), golden.get("layer"), golden.get("position")) != (
            context, layer, context - 1):
        raise ValueError("golden shard identity/position mismatch")
    required = {"h_in", "pre_in", "h_out", "pre_out"}
    if not required <= arrays.keys():
        raise ValueError(f"golden lacks required arrays: {sorted(required - arrays.keys())}")
    if golden.get("input_sha256") != _digest(arrays["h_in"], arrays["pre_in"]):
        raise ValueError("golden input digest disagrees with its arrays")
    if golden.get("output_sha256") != _digest(arrays["h_out"], arrays["pre_out"]):
        raise ValueError("golden output digest disagrees with its arrays")
    pins = golden.get("golden")
    if pins is not None:
        for rel, pin in pins.items():
            path = Path(rel)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise ValueError(f"unsafe golden source path: {rel}")
            if hashlib.sha256((source_root / path).read_bytes()).hexdigest() != pin["sha256"]:
                raise ValueError(f"golden source pin stale: {rel}")


def validate_golden_chain(golden_dir: Path, context: int, layers: list[int],
                          source_root: Path) -> dict:
    if not layers or len(layers) != len(set(layers)) or layers != sorted(layers):
        raise ValueError("layers must be nonempty, unique and sorted")
    rows = []
    previous_output = None
    for layer in layers:
        meta, arrays = _read_pair(golden_dir, context, layer)
        _validate_golden(meta, arrays, context, layer, source_root)
        if previous_output is not None and layer == layers[len(rows) - 1] + 1:
            if meta["input_sha256"] != previous_output:
                raise ValueError(f"layer {layer} does not consume the preceding layer output")
        rows.append({"layer": layer, "input_sha256": meta["input_sha256"],
                     "output_sha256": meta["output_sha256"], "arrays": sorted(arrays)})
        previous_output = meta["output_sha256"]
    return {"status": "golden_valid", "context": context, "layers": rows}


def compare_chain(golden_dir: Path, rtl_dir: Path, context: int, layers: list[int],
                  source_root: Path) -> dict:
    if not layers or len(layers) != len(set(layers)) or layers != sorted(layers):
        raise ValueError("layers must be nonempty, unique and sorted")
    rows = []
    previous_output = None
    for layer in layers:
        row = compare_layer(golden_dir, rtl_dir, context, layer, source_root)
        if previous_output is not None and layer == layers[len(rows) - 1] + 1:
            if row["golden_input_sha256"] != previous_output:
                raise ValueError(f"layer {layer} does not consume the preceding layer output")
        rows.append(row)
        previous_output = row["golden_output_sha256"]
    return {"status": "bit_exact", "context": context, "layers": rows,
            "rtl_cycles_sum": sum(row["cycles"] for row in rows),
            "cycle_scope": "layer simulated cycles only; collective/hop/head excluded"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--golden-dir", type=Path, required=True)
    ap.add_argument("--rtl-dir", type=Path)
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--context", type=int, required=True)
    ap.add_argument("--layers", required=True, help="comma-separated layer numbers")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    layers = [int(x) for x in args.layers.split(",")]
    result = (compare_chain(args.golden_dir, args.rtl_dir, args.context, layers, args.source_root)
              if args.rtl_dir else validate_golden_chain(args.golden_dir, args.context, layers, args.source_root))
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "layers": len(result["layers"]),
                      "rtl_cycles_sum": result.get("rtl_cycles_sum")}))


if __name__ == "__main__":
    main()
