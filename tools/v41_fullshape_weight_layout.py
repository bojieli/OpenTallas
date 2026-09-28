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
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.v41x.fullshape.weight_layout.v1"
CAPACITY_BYTES = 2_714_287_356  # arch_budget_v41.json placement, floor to bytes


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry(nrows: int, nblocks: int, chunks: int = 8, min_plg: int = 0) -> dict:
    """Choose an exact row layout minimizing padded bank words.

    The tile has 8*chunks 264-bit lane banks.  A segment uses 8*2**plg
    blocks per row; chunks/2**plg rows share one bank address.
    """
    if nrows <= 0 or nblocks <= 0 or chunks <= 0 or chunks & (chunks - 1):
        raise ValueError("positive shape and power-of-two chunk count required")
    choices = []
    for plg in range(min_plg, chunks.bit_length()):
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


def pack_me_bf16(bits: np.ndarray, base_word: int = 0, chunks: int = 8) -> tuple[np.ndarray, dict]:
    """One BF16 matrix into KIND=1 bank words (BF16 shifted to FP32 bits)."""
    if bits.dtype != np.uint16 or bits.ndim != 2 or base_word < 0:
        raise ValueError("ME source must be a BF16 uint16 matrix with nonnegative base")
    nrows, ncols = bits.shape
    geom = geometry(nrows, ncols, chunks, min_plg=1)
    image = np.zeros((geom["word_count"], geom["banks"]), dtype="<u4")
    touched = np.zeros(image.shape, dtype=np.bool_)
    for row in range(nrows):
        for term in range(ncols):
            address, bank = bank_slot(row, term, geom, base_word)
            offset = address - base_word
            if touched[offset, bank]:
                raise AssertionError("ME weight layout collision")
            image[offset, bank] = np.uint32(bits[row, term]) << np.uint32(16)
            touched[offset, bank] = True
    geom.update(useful_bank_words=int(touched.sum()),
                padded_bank_words=int(touched.size - touched.sum()),
                image_bytes=int(image.nbytes), base_word=base_word,
                end_word_exclusive=base_word + geom["word_count"])
    return image, geom


def verify_me(image: np.ndarray, bits: np.ndarray, geom: dict) -> None:
    for row in range(bits.shape[0]):
        for term in range(bits.shape[1]):
            address, bank = bank_slot(row, term, geom, geom["base_word"])
            if image[address - geom["base_word"], bank] != np.uint32(bits[row, term]) << 16:
                raise AssertionError(f"ME readback mismatch row={row} term={term}")


def pack_he_fp32(bits: np.ndarray, base_word: int = 0, hhw: int = 8) -> tuple[np.ndarray, dict]:
    """HCP 8 banks; bank k/lane l reads matrix[o, 8*(r*HHW+l)+k]."""
    if bits.dtype != np.uint32 or bits.ndim != 2 or base_word < 0 or hhw <= 0:
        raise ValueError("HE source must be an FP32 uint32 matrix with nonnegative base")
    nrows, ncols = bits.shape
    if ncols % 8:
        raise ValueError("HE K must be divisible by 8 banks")
    words_per_row = (ncols + 8 * hhw - 1) // (8 * hhw)
    depth = nrows * words_per_row
    image = np.zeros((depth, 8, hhw), dtype="<u4")
    for row in range(nrows):
        for col in range(ncols):
            q, bank = divmod(col, 8)
            beat, lane = divmod(q, hhw)
            image[row * words_per_row + beat, bank, lane] = bits[row, col]
    geom = dict(banks=8, hhw=hhw, words_per_row=words_per_row,
                word_count=depth, image_bytes=int(image.nbytes),
                base_word=base_word, end_word_exclusive=base_word + depth)
    return image, geom


def verify_he(image: np.ndarray, bits: np.ndarray, geom: dict) -> None:
    for row in range(bits.shape[0]):
        for col in range(bits.shape[1]):
            q, bank = divmod(col, 8)
            beat, lane = divmod(q, geom["hhw"])
            if image[row * geom["words_per_row"] + beat, bank, lane] != bits[row, col]:
                raise AssertionError(f"HE readback mismatch row={row} col={col}")


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


def pack_fp4(packed_codes: np.ndarray, scales: np.ndarray, base_word: int = 0,
             chunks: int = 8) -> tuple[np.ndarray, dict]:
    """Preserve the checkpoint's low-nibble-first E2M1 codes and per-32 scale."""
    if (packed_codes.dtype != np.uint8 or scales.dtype != np.uint8 or
            packed_codes.ndim != 2 or scales.ndim != 2):
        raise ValueError("FP4 packed codes and UE8M0 scales must be two-dimensional uint8 arrays")
    nrows, packed_cols = packed_codes.shape
    if nrows % 32 or packed_cols % 16 or scales.shape != (nrows, packed_cols // 16):
        raise ValueError("FP4 packed weight and per-row 32-column scale shapes do not match")
    if base_word < 0:
        raise ValueError("negative ROM base")
    geom = geometry(nrows, packed_cols // 16, chunks)
    image = np.zeros((geom["word_count"], geom["banks"], 17), dtype=np.uint8)
    touched = np.zeros((geom["word_count"], geom["banks"]), dtype=np.bool_)
    blocks = packed_codes.reshape(nrows, packed_cols // 16, 16)
    for row in range(nrows):
        for block in range(packed_cols // 16):
            address, bank = bank_slot(row, block, geom, base_word)
            offset = address - base_word
            if touched[offset, bank]:
                raise AssertionError("weight layout collision")
            image[offset, bank, :16] = blocks[row, block]
            image[offset, bank, 16] = scales[row, block]
            touched[offset, bank] = True
    geom["useful_bank_words"] = int(touched.sum())
    geom["padded_bank_words"] = int(touched.size - touched.sum())
    geom["image_bytes"] = int(image.nbytes)
    geom["base_word"] = base_word
    geom["end_word_exclusive"] = base_word + geom["word_count"]
    return image, geom


def verify_fp4(image: np.ndarray, packed_codes: np.ndarray, scales: np.ndarray, geom: dict) -> None:
    nrows, packed_cols = packed_codes.shape
    blocks = packed_codes.reshape(nrows, packed_cols // 16, 16)
    for row in range(nrows):
        for block in range(packed_cols // 16):
            address, bank = bank_slot(row, block, geom, geom["base_word"])
            word = image[address - geom["base_word"], bank]
            if not np.array_equal(word[:16], blocks[row, block]) or word[16] != scales[row, block]:
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
    fmt = (weight["format"], scale["format"])
    if fmt not in (("F8_E4M3", "F8_E8M0"), ("I8", "F8_E8M0")):
        raise ValueError("only exact FP8 E4M3 or packed FP4 E2M1 with UE8M0 scales are supported")
    expert_match = re.fullmatch(r"exp(\d+)\.w[123]", name)
    if fmt[0] == "I8" and expert_match is None:
        raise ValueError("packed FP4 is supported only for routed expert weights")
    inputs = {}
    for key, entry in ((weight_key, weight), (scale_key, scale)):
        path = image_dir / f"{key}.bin"
        if not path.is_file() or sha256(path) != entry["sha256"]:
            raise ValueError(f"missing or wrong source-pinned tensor: {key}")
        inputs[key] = path
    codes = np.fromfile(inputs[weight_key], dtype=np.uint8).reshape(weight["shape"])
    scales = np.fromfile(inputs[scale_key], dtype=np.uint8).reshape(scale["shape"])
    expert_id = int(expert_match.group(1)) if expert_match else None
    if expert_id is not None and not 0 <= expert_id < 384:
        raise ValueError("routed expert ID outside shipped shape")
    if fmt[0] == "I8":
        # The emitted image contains just this expert's bytes.  Its physical
        # address reserves all 384 expert IDs at uniform stride; missing
        # experts remain unmaterialized and may not be read by a token gate.
        stride = geometry(codes.shape[0], codes.shape[1] // 16, chunks)["word_count"]
        matrix_base = base_word + expert_id * stride
        image, geom = pack_fp4(codes, scales, matrix_base, chunks)
        reserved_end_word = base_word + 384 * stride
        lane_bytes = 17
        format_name = "F4_E2M1_UE8M0_rowx32"
        ncols = codes.shape[1] * 2
    else:
        stride = None
        matrix_base = base_word
        image, geom = pack_fp8(codes, scales, matrix_base, chunks)
        reserved_end_word = geom["end_word_exclusive"]
        lane_bytes = 33
        format_name = "F8_E4M3_UE8M0_32x32"
        ncols = codes.shape[1]
    if reserved_end_word >= (1 << 30):
        raise ValueError("ROM word address exceeds full-shape ISA A30")
    if reserved_end_word * geom["banks"] * lane_bytes > CAPACITY_BYTES:
        raise ValueError("matrix placement exceeds per-die ROM capacity")
    if fmt[0] == "I8":
        verify_fp4(image, codes, scales, geom)
    else:
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
        "output_format": "address-major, 64 bank lanes per address, little-endian lane words; FP8: 32 code bytes plus scale byte, FP4: 16 packed code bytes plus scale byte",
        "matrices": {name: {
            "engine": "qe", "base_word": matrix_base, "word_count": geom["word_count"],
            "nrows": int(codes.shape[0]), "ncols": int(ncols),
            "format": format_name, "source_weight_sha256": weight["sha256"],
            "source_scale_sha256": scale["sha256"], "geometry": geom,
            "expert_stride_words": stride, "expert_id_base": base_word if stride is not None else None,
            "expert_ids_materialized": [expert_id] if expert_id is not None else None,
            "all_experts_materialized": False if expert_id is not None else None,
            "expert_reserved_end_word_exclusive": reserved_end_word if expert_id is not None else None,
            "output_image_sha256": sha256(output),
            "output_image_bytes": output.stat().st_size,
        }},
        "matrix_coverage": "one_matrix_only",
        "unplaced_note": "Every other matrix, constant, and all inactive expert rows remain unplaced; any missing ME/QE/HE or indirect expert binding must fail closed.",
        "reproduction": f"python3 tools/v41_fullshape_weight_layout.py --input-manifest results/rtl/hdc_v41x_fullshape_200k_l0_rank0_image.json --image-dir SCRATCH/images/ctx200000_L00_r0 --matrix {name} --output SCRATCH/{name}_qebank.bin --record RESULT.json",
    }
    return record


def pack_constant_from_manifest(manifest_path: Path, image_dir: Path, name: str,
                                output: Path, base_word: int = 0) -> dict:
    """One CROM entry; each 64-bit word holds FP32 in lo, canonical +0 in hi."""
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema") != "opentallas.rtl.hdc_v41x_fullshape_layers.v1.die_layer_images":
        raise ValueError("unrecognized input manifest schema")
    key = f"w.{name}"
    entry = manifest["files"].get(key)
    if entry is None or entry["format"] not in ("BF16", "F32"):
        raise ValueError("missing or unsupported CROM tensor")
    path = image_dir / f"{key}.bin"
    if not path.is_file() or sha256(path) != entry["sha256"]:
        raise ValueError("missing or wrong source-pinned CROM tensor")
    raw = np.fromfile(path, dtype=np.uint8)
    if int(np.prod(entry["shape"])) != raw.size:
        raise ValueError("CROM tensor byte shape mismatch")
    if entry["format"] == "BF16":
        if raw.size % 2:
            raise ValueError("BF16 byte count is odd")
        bits = np.frombuffer(raw.tobytes(), dtype="<u2").astype(np.uint32) << 16
    else:
        if raw.size % 4:
            raise ValueError("FP32 byte count is not divisible by four")
        bits = np.frombuffer(raw.tobytes(), dtype="<u4")
    if name in ("hc_attn_scale", "hc_ffn_scale"):
        if entry["format"] != "F32" or bits.size != 3:
            raise ValueError("HC scale must have three FP32 coefficients")
        bits = np.concatenate((np.repeat(bits[0], 4), np.repeat(bits[1], 4),
                               np.repeat(bits[2], 16))).astype(np.uint32)
    if base_word < 0 or base_word + bits.size >= (1 << 30):
        raise ValueError("CROM address outside A30")
    words = np.zeros((bits.size, 2), dtype="<u4")
    words[:, 0] = bits
    # Round-trip the source bits through the actual low half of the 64-bit image.
    if name in ("hc_attn_scale", "hc_ffn_scale"):
        expected = np.concatenate((np.repeat(bits[0], 4), np.repeat(bits[4], 4),
                                   np.repeat(bits[8], 16)))
    else:
        expected = bits
    if not np.array_equal(words[:, 0], expected) or np.any(words[:, 1]):
        raise AssertionError("CROM readback mismatch")
    output.parent.mkdir(parents=True, exist_ok=True)
    words.tofile(output)
    return {
        "schema": SCHEMA, "status": "one_constant_exact_readback",
        "claim_boundary": "One source-pinned CROM tensor; no complete die CROM or token execution.",
        "source_image_manifest": str(manifest_path),
        "source_image_manifest_sha256": sha256(manifest_path),
        "layout_tool_sha256": sha256(Path(__file__)),
        "source_commit": manifest["source_commit"],
        "source_sha256": manifest["source_sha256"],
        "checkpoint": manifest["checkpoint"],
        "layer": manifest["layer"], "rank": manifest["rank"],
        "constants": {name: {
            "engine": "crom", "base_word": base_word,
            "word_count": int(bits.size), "format": "FP32_lo_plus_zero_hi",
            "source_format": entry["format"], "source_tensor_sha256": entry["sha256"],
            "output_image_sha256": sha256(output), "output_image_bytes": output.stat().st_size,
        }},
        "matrix_coverage": "none",
        "unplaced_note": "All other CROM entries, generated RoPE values, Engram token map, and ME/QE/HE weights remain unplaced.",
    }


def pack_unquantized_from_manifest(manifest_path: Path, image_dir: Path, name: str,
                                   engine: str, output: Path, base_word: int = 0) -> dict:
    """One source-pinned BF16 ME or FP32 HE matrix with exact bank readback."""
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema") != "opentallas.rtl.hdc_v41x_fullshape_layers.v1.die_layer_images":
        raise ValueError("unrecognized input manifest schema")
    key = f"w.{name}"
    entry = manifest["files"].get(key)
    required = "BF16" if engine == "me" else "F32" if engine == "he" else None
    if required is None or entry is None or entry["format"] != required:
        raise ValueError("missing or wrong-format ME/HE matrix")
    path = image_dir / f"{key}.bin"
    if not path.is_file() or sha256(path) != entry["sha256"]:
        raise ValueError("missing or wrong source-pinned ME/HE matrix")
    raw = np.fromfile(path, dtype=np.uint8)
    if int(np.prod(entry["shape"])) != raw.size:
        raise ValueError("ME/HE source byte shape mismatch")
    nrows, row_bytes = entry["shape"]
    if engine == "me":
        if row_bytes % 2:
            raise ValueError("odd BF16 row byte count")
        bits = np.frombuffer(raw.tobytes(), dtype="<u2").reshape(nrows, row_bytes // 2)
        image, geom = pack_me_bf16(bits, base_word)
        verify_me(image, bits, geom)
        width_per_address = geom["banks"] * 4
        fmt = "BF16_as_FP32_bank_word"
    else:
        if row_bytes % 4:
            raise ValueError("FP32 row byte count not divisible by four")
        bits = np.frombuffer(raw.tobytes(), dtype="<u4").reshape(nrows, row_bytes // 4)
        image, geom = pack_he_fp32(bits, base_word)
        verify_he(image, bits, geom)
        width_per_address = geom["banks"] * geom["hhw"] * 4
        fmt = "FP32_HCP_8bank"
    if geom["end_word_exclusive"] >= (1 << 30):
        raise ValueError("ME/HE address outside A30")
    if geom["end_word_exclusive"] * width_per_address > CAPACITY_BYTES:
        raise ValueError("ME/HE placement exceeds per-die ROM capacity")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.tofile(output)
    return {
        "schema": SCHEMA, "status": "one_matrix_exact_readback",
        "claim_boundary": f"One source-pinned {engine.upper()} matrix; no complete die ROM or token execution.",
        "source_image_manifest": str(manifest_path),
        "source_image_manifest_sha256": sha256(manifest_path),
        "layout_tool_sha256": sha256(Path(__file__)),
        "source_commit": manifest["source_commit"],
        "source_sha256": manifest["source_sha256"],
        "checkpoint": manifest["checkpoint"],
        "layer": manifest["layer"], "rank": manifest["rank"],
        "matrices": {name: {
            "engine": engine, "base_word": base_word,
            "word_count": geom["word_count"], "nrows": nrows,
            "ncols": int(bits.shape[1]), "format": fmt,
            "source_weight_sha256": entry["sha256"],
            "geometry": geom, "output_image_sha256": sha256(output),
            "output_image_bytes": output.stat().st_size,
            "expert_stride_words": None, "expert_id_base": None,
            "expert_ids_materialized": None, "all_experts_materialized": None,
        }},
        "matrix_coverage": "one_matrix_only",
        "unplaced_note": "All other matrices and constants remain unplaced.",
    }


def combine_layout_records(paths: list[Path]) -> dict:
    """Merge partial gates while checking physical region overlap and capacity."""
    if not paths:
        raise ValueError("no layout records")
    inputs = [json.loads(path.read_text()) for path in paths]
    pinned = (inputs[0]["source_image_manifest_sha256"], inputs[0]["layer"], inputs[0]["rank"])
    matrices, constants, regions = {}, {}, []
    for path, data in zip(paths, inputs):
        if data.get("schema") != SCHEMA or (data["source_image_manifest_sha256"], data["layer"], data["rank"]) != pinned:
            raise ValueError("incompatible source image or layout schema")
        for name, entry in data.get("matrices", {}).items():
            if name in matrices:
                raise ValueError(f"duplicate matrix {name}")
            matrices[name] = entry
            start = entry["expert_id_base"] if entry["expert_stride_words"] is not None else entry["base_word"]
            end = (entry["expert_reserved_end_word_exclusive"] if entry["expert_stride_words"] is not None
                   else entry["base_word"] + entry["word_count"])
            if entry["engine"] == "qe":
                bytes_per_bank = 17 if entry["format"].startswith("F4_") else 33
            elif entry["engine"] == "me":
                bytes_per_bank = 4
            else:
                bytes_per_bank = 32
            regions.append((entry["engine"], start, end, bytes_per_bank, name))
        for name, entry in data.get("constants", {}).items():
            if name in constants:
                raise ValueError(f"duplicate constant {name}")
            constants[name] = entry
            regions.append(("crom", entry["base_word"], entry["base_word"] + entry["word_count"], 8, name))
    for engine in {r[0] for r in regions}:
        part = sorted((r for r in regions if r[0] == engine), key=lambda r: r[1])
        for left, right in zip(part, part[1:]):
            if left[2] > right[1]:
                raise ValueError(f"ROM region overlap: {left[4]} and {right[4]}")
    reserved_bytes = sum((end - start) * (64 if engine in ("qe", "me") else 8 if engine == "he" else 1) * width
                         for engine, start, end, width, _ in regions)
    if reserved_bytes > CAPACITY_BYTES:
        raise ValueError("combined placement exceeds per-die ROM capacity")
    return {
        "schema": SCHEMA, "status": "partial_rank_layout_verified",
        "claim_boundary": "Source-pinned partial rank layout. Missing weights/constants and unmaterialized experts prevent full-layer/token claims.",
        "source_image_manifest_sha256": pinned[0], "layer": pinned[1], "rank": pinned[2],
        "source_records_sha256": {str(path): sha256(path) for path in paths},
        "matrices": matrices, "constants": constants,
        "rom_capacity_bytes": CAPACITY_BYTES, "reserved_bytes": reserved_bytes,
        "regions": [dict(engine=engine, start_word=start, end_word_exclusive=end,
                         bytes_per_bank_word=width, name=name)
                    for engine, start, end, width, name in sorted(regions)],
        "all_experts_materialized": all(e.get("all_experts_materialized") is not False
                                        for e in matrices.values()),
        "complete_die_image": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-manifest", type=Path)
    ap.add_argument("--image-dir", type=Path)
    one = ap.add_mutually_exclusive_group(required=True)
    one.add_argument("--matrix")
    one.add_argument("--constant")
    one.add_argument("--me")
    one.add_argument("--he")
    one.add_argument("--combine-record", type=Path, nargs="+")
    ap.add_argument("--output", type=Path)
    ap.add_argument("--record", type=Path, required=True)
    ap.add_argument("--base-word", type=int, default=0)
    ap.add_argument("--chunks", type=int, default=8)
    a = ap.parse_args()
    if a.combine_record:
        record = combine_layout_records(a.combine_record)
    elif a.matrix:
        if not a.input_manifest or not a.image_dir or not a.output:
            ap.error("matrix packing requires --input-manifest, --image-dir, and --output")
        record = pack_from_manifest(a.input_manifest, a.image_dir, a.matrix, a.output,
                                    a.base_word, a.chunks)
    else:
        if not a.input_manifest or not a.image_dir or not a.output:
            ap.error("weight/constant packing requires --input-manifest, --image-dir, and --output")
        if a.constant:
            record = pack_constant_from_manifest(a.input_manifest, a.image_dir, a.constant,
                                                 a.output, a.base_word)
        else:
            engine, name = ("me", a.me) if a.me else ("he", a.he)
            record = pack_unquantized_from_manifest(a.input_manifest, a.image_dir, name,
                                                    engine, a.output, a.base_word)
    a.record.parent.mkdir(parents=True, exist_ok=True)
    a.record.write_text(json.dumps(record, indent=2) + "\n")
    summary = {"status": record["status"]}
    if a.combine_record:
        summary.update(matrices=list(record["matrices"]), constants=list(record["constants"]),
                       reserved_bytes=record["reserved_bytes"])
    elif a.matrix:
        summary.update(matrix=a.matrix, geometry=record["matrices"][a.matrix]["geometry"])
    elif a.constant:
        summary.update(constant=a.constant, entry=record["constants"][a.constant])
    else:
        name = a.me if a.me else a.he
        summary.update(matrix=name, entry=record["matrices"][name])
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
