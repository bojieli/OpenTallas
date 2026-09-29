#!/usr/bin/env python3
"""Bind actual L0/rank-0 checkpoint files to the full-shape RTL image map.

This prepares inputs for the all-unit layer gate. It does not execute RTL or
interpret a blocked program-binder record as a token verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "results/rtl/hdc_v41x_fullshape_token_selected_rom_layout.json"
SHARD = ROOT / "results/rtl/hdc_v41x_fullshape_200k_l0_rank0_image.json"
QE = ROOT / "results/rtl/hdc_v41x_fullshape_qe_stream_200k_l0_rank0.json"
RECORD = ROOT / "results/rtl/hdc_v41x_fullshape_l0_allunit_inputs.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bind(image_dir: Path, shard_dir: Path) -> dict:
    layout, shard, qe = (json.loads(p.read_text()) for p in (LAYOUT, SHARD, QE))
    if (layout["layer"], layout["rank"], shard["context"], shard["layer"], shard["rank"]) != (0, 0, 200000, 0, 0):
        raise ValueError("expected the 200K L0/rank-0 checkpoint shard")
    if layout["source_image_manifest_sha256"] != digest(SHARD):
        raise ValueError("layout is not bound to the checkpoint shard")
    if qe["other_engine_layout_sha256"] != digest(LAYOUT) or qe["source_image_manifest_sha256"] != digest(SHARD):
        raise ValueError("QE logical stream is not bound to the physical layout")
    if tuple(shard["golden_shard"]["experts"]) != tuple(layout["selected_expert_ids"]):
        raise ValueError("expert selection differs between image and golden")

    regions: dict[str, list[dict]] = {name: [] for name in ("qe", "me", "he", "crom")}
    for family, entries in (("matrix", layout["matrices"]), ("constant", layout["constants"])):
        for name, item in entries.items():
            engine = item["engine"]
            if engine not in regions or (family == "constant") != (engine == "crom"):
                raise ValueError(f"unexpected image engine for {name}: {engine}")
            path = image_dir / f"{name}.{engine}.bin"
            if not path.is_file() or path.stat().st_size != item["output_image_bytes"] or digest(path) != item["output_image_sha256"]:
                raise ValueError(f"missing or stale packed image: {path}")
            first, count = int(item["base_word"]), int(item["word_count"])
            if first < 0 or count <= 0 or first + count > (1 << 30):
                raise ValueError(f"invalid 30-bit ROM word range for {name}")
            regions[engine].append({"name": name, "first_word": first,
                                    "end_word_exclusive": first + count,
                                    "bytes": path.stat().st_size, "sha256": digest(path),
                                    "file": path.name})
    for engine, items in regions.items():
        for left, right in zip(sorted(items, key=lambda x: x["first_word"]),
                               sorted(items, key=lambda x: x["first_word"])[1:]):
            if left["end_word_exclusive"] > right["first_word"]:
                raise ValueError(f"overlapping {engine} images: {left['name']} and {right['name']}")

    source_files = {}
    for name, item in shard["files"].items():
        path = shard_dir / f"{name}.bin"
        if not path.is_file() or digest(path) != item["sha256"]:
            raise ValueError(f"missing or stale checkpoint image: {path}")
        source_files[name] = {"bytes": path.stat().st_size, "sha256": item["sha256"], "file": path.name}
    if (len(regions["qe"]), len(regions["me"]), len(regions["he"]), len(regions["crom"]), len(source_files)) != (25, 2, 2, 11, 71):
        raise ValueError("incomplete L0 selected-token image families")
    return {
        "schema": "opentallas.rtl.v41x_fullshape_l0_allunit_inputs.v1",
        "status": "input_only",
        "claim_boundary": "All physical selected-token ROM/CROM images and checkpoint shard inputs match the manifests; no RTL arithmetic, capacity, timing, or full-token verdict.",
        "context": 200000, "layer": 0, "rank": 0,
        "selected_experts": layout["selected_expert_ids"],
        "regions": regions, "checkpoint_files": source_files,
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in
                          (LAYOUT, SHARD, QE, Path(__file__))},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packed-images", type=Path, required=True)
    parser.add_argument("--shard-images", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=RECORD)
    args = parser.parse_args()
    record = bind(args.packed_images, args.shard_images)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print("PASS: 29 packed matrices, 11 constants, 71 checkpoint files; input-only")


if __name__ == "__main__":
    main()
