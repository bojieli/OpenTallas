#!/usr/bin/env python3
"""Pack one full-shape V4.1 FP8 tensor for the adopted quantized tile.

The input is the source-pinned raw checkpoint slice written by
rtl_v41_fullshape_layer_campaign.py.  This tool is intentionally limited to
FP8 E4M3 with a UE8M0 scale per 32x32 block.  Other formats need separate,
explicit layout gates before an ISA emitter may bind their bases.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.v41x.fullshape.weight_layout.v1"
CAPACITY_BYTES = 2_714_287_356  # arch_budget_v41.json placement, floor to bytes


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry(nrows: int, nblocks: int, chunks: int = 8) -> dict:
    """Choose an exact row layout minimizing padded bank words.

    The tile has 8*chunks 264-bit lane banks.  A segment uses 8*2**plg
    blocks per row; chunks/2**plg rows share one bank address.
    """
    if nrows <= 0 or nblocks <= 0 or chunks <= 0 or chunks & (chunks - 1):
        raise ValueError("positive shape and power-of-two chunk count required")
    choices = []
    for plg in range(chunks.bit_length()):
        p = 1 << plg
        if p > chunks:
            break
        blocks_per_beat = 8 * p
        rows_per_group = chunks // p
        beats = (nblocks + blocks_per_beat - 1) // blocks_per_beat
        groups = (nrows + rows_per_group - 1) // rows_per_group
        choices.append((groups * beats, plg, beats, groups, rows_per_group))
    depth, plg, beats, groups, rows_per_group = min(choices)
    return dict(chunks=chunks, banks=8 * chunks, plg=plg,
                blocks_per_beat=8 << plg, rows_per_group=rows_per_group,
                nbeat=beats, nrg=groups, word_count=depth)


def bank_slot(row: int, block: int, geom: dict, base_word: int = 0) -> tuple[int, int]:
    group, slot = divmod(row, geom["rows_per_group"])
    beat, lane = divmod(block, geom["blocks_per_beat"])
    return base_word + group * geom["nbeat"] + beat, slot * geom["blocks_per_beat"] + lane


def pack_fp8(codes: np.ndarray, scales: np.ndarray, base_word: int = 0,
             chunks: int = 8) -> tuple[np.ndarray, dict]:
    if codes.dtype != np.uint8 or scales.dtype != np.uint8 or codes.ndim != 2 or scales.ndim != 2:
        raise ValueError("FP8 codes and UE8M0 scales must be two-dimensional uint8 arrays")
    nrows, cols = codes.shape
    if nrows % 32 or cols % 32 or scales.shape != (nrows // 32, cols // 32):
        raise ValueError("FP8 weight and 32x32 scale shapes do not match")
    if base_word < 0:
        raise ValueError("negative ROM base")
    if np.any((codes == 0x7f) | (codes == 0xff)):
        raise ValueError("E4M3 NaN code in checkpoint weights")
    geom = geometry(nrows, cols // 32, chunks)
    # Each bank lane word is {scale[7:0], code[31:0][7:0]}, little-endian
    # bytes 0..31 for code 0..31 and byte 32 for scale.
    image = np.zeros((geom["word_count"], geom["banks"], 33), dtype=np.uint8)
    touched = np.zeros((geom["word_count"], geom["banks"]), dtype=np.bool_)
    blocks = codes.reshape(nrows, cols // 32, 32)
    for row in range(nrows):
        for block in range(cols // 32):
            address, bank = bank_slot(row, block, geom, base_word)
            offset = address - base_word
            if touched[offset, bank]:
                raise AssertionError("weight layout collision")
            image[offset, bank, :32] = blocks[row, block]
            image[offset, bank, 32] = scales[row // 32, block]
            touched[offset, bank] = True
    if int(touched.sum()) != nrows * (cols // 32):
        raise AssertionError("incomplete weight layout")
    geom["useful_bank_words"] = int(touched.sum())
    geom["padded_bank_words"] = int(touched.size - touched.sum())
    geom["image_bytes"] = int(image.nbytes)
    geom["base_word"] = base_word
    geom["end_word_exclusive"] = base_word + geom["word_count"]
    return image, geom


def verify_fp8(image: np.ndarray, codes: np.ndarray, scales: np.ndarray, geom: dict) -> None:
    nrows, cols = codes.shape
    blocks = codes.reshape(nrows, cols // 32, 32)
    for row in range(nrows):
        for block in range(cols // 32):
            address, bank = bank_slot(row, block, geom, geom["base_word"])
            word = image[address - geom["base_word"], bank]
            if not np.array_equal(word[:32], blocks[row, block]) or word[32] != scales[row // 32, block]:
                raise AssertionError(f"readback mismatch at row={row} block={block}")


def pack_from_manifest(manifest_path: Path, image_dir: Path, name: str, output: Path,
                       base_word: int = 0, chunks: int = 8) -> dict:
    budget_path = ROOT / "results/arch/arch_budget_v41.json"
    budget = json.loads(budget_path.read_text())
    budget_capacity = int(budget["requirement"]["headline"]["placement"]["per_die_capacity_bytes"])
    if budget_capacity != CAPACITY_BYTES:
        raise ValueError("ROM capacity no longer matches the pinned V4.1 budget")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema") != "opentallas.rtl.hdc_v41x_fullshape_layers.v1.die_layer_images":
        raise ValueError("unrecognized input manifest schema")
    files = manifest["files"]
    weight_key, scale_key = f"w.{name}", f"w.{name}.scale"
    if weight_key not in files or scale_key not in files:
        raise ValueError(f"missing weight or scale for {name}")
    weight, scale = files[weight_key], files[scale_key]
    if (weight["format"], scale["format"]) != ("F8_E4M3", "F8_E8M0"):
        raise ValueError("only exact FP8 E4M3 + UE8M0 matrices are supported")
    inputs = {}
    for key, entry in ((weight_key, weight), (scale_key, scale)):
        path = image_dir / f"{key}.bin"
        if not path.is_file() or sha256(path) != entry["sha256"]:
            raise ValueError(f"missing or wrong source-pinned tensor: {key}")
        inputs[key] = path
    codes = np.fromfile(inputs[weight_key], dtype=np.uint8).reshape(weight["shape"])
    scales = np.fromfile(inputs[scale_key], dtype=np.uint8).reshape(scale["shape"])
    image, geom = pack_fp8(codes, scales, base_word, chunks)
    if geom["end_word_exclusive"] >= (1 << 30):
        raise ValueError("ROM word address exceeds full-shape ISA A30")
    if (base_word + geom["word_count"]) * geom["banks"] * 33 > CAPACITY_BYTES:
        raise ValueError("matrix placement exceeds per-die ROM capacity")
    verify_fp8(image, codes, scales, geom)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.tofile(output)
    record = {
        "schema": SCHEMA,
        "status": "one_matrix_exact_readback",
        "claim_boundary": "One FP8 matrix bank-layout gate; not a complete die ROM image, ISA execution, or bit-exact token.",
        "source_image_manifest": str(manifest_path),
        "source_image_manifest_sha256": sha256(manifest_path),
        "layout_tool_sha256": sha256(Path(__file__)),
        "capacity_budget_sha256": sha256(budget_path),
        "source_commit": manifest["source_commit"],
        "source_sha256": manifest["source_sha256"],
        "checkpoint": manifest["checkpoint"],
        "layer": manifest["layer"], "rank": manifest["rank"],
        "rom_capacity_bytes": CAPACITY_BYTES,
        "output_format": "address-major, 64 bank lanes per address, little-endian 33-byte lane words; code bytes 0..31, scale byte 32",
        "matrices": {name: {
            "engine": "qe", "base_word": base_word, "word_count": geom["word_count"],
            "nrows": int(codes.shape[0]), "ncols": int(codes.shape[1]),
            "format": "F8_E4M3_UE8M0_32x32", "source_weight_sha256": weight["sha256"],
            "source_scale_sha256": scale["sha256"], "geometry": geom,
            "expert_stride_words": None, "expert_id_base": None,
            "expert_ids_materialized": None,
            "output_image_sha256": sha256(output),
            "output_image_bytes": output.stat().st_size,
        }},
        "matrix_coverage": "one_matrix_only",
        "unplaced_note": "Every other matrix, constant, and all inactive expert rows remain unplaced; any missing ME/QE/HE or indirect expert binding must fail closed.",
        "reproduction": "python3 tools/v41_fullshape_weight_layout.py --input-manifest results/rtl/hdc_v41x_fullshape_200k_l0_rank0_image.json --image-dir SCRATCH/images/ctx200000_L00_r0 --matrix wq_a --output SCRATCH/wq_a_qebank.bin --record results/rtl/hdc_v41x_fullshape_wq_a_layout.json",
    }
    return record


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-manifest", type=Path, required=True)
    ap.add_argument("--image-dir", type=Path, required=True)
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--record", type=Path, required=True)
    ap.add_argument("--base-word", type=int, default=0)
    ap.add_argument("--chunks", type=int, default=8)
    a = ap.parse_args()
    record = pack_from_manifest(a.input_manifest, a.image_dir, a.matrix, a.output,
                                a.base_word, a.chunks)
    a.record.parent.mkdir(parents=True, exist_ok=True)
    a.record.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": record["status"], "matrix": a.matrix,
                      "geometry": record["matrices"][a.matrix]["geometry"]}))


if __name__ == "__main__":
    main()
