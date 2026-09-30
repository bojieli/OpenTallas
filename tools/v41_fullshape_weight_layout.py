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
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.v41x.fullshape.weight_layout.v1"
CAPACITY_BYTES = 2_714_287_356  # arch_budget_v41.json placement, floor to bytes


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry(nrows: int, nblocks: int, chunks: int = 8,
             min_plg: int = 0, fixed_plg: int | None = None) -> dict:
    """Choose an exact row layout minimizing padded bank words.

    The tile has 8*chunks 264-bit lane banks.  A segment uses 8*2**plg
    blocks per row; chunks/2**plg rows share one bank address.
    """
    if nrows <= 0 or nblocks <= 0 or chunks <= 0 or chunks & (chunks - 1):
        raise ValueError("positive shape and power-of-two chunk count required")
    choices = []
    candidates = (fixed_plg,) if fixed_plg is not None else range(min_plg, chunks.bit_length())
    for plg in candidates:
        if plg is None or plg < 0:
            raise ValueError("invalid fixed segment level")
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
    # ot_hdc_v41x_me_adapt computes plg from K, not from a packing optimum:
    # clamp(ceil(log2(ceil(K/8))), PMIN_LG=1, log2(MG)).
    nch = (ncols + 7) // 8
    plg = min(chunks.bit_length() - 1, max(1, (nch - 1).bit_length()))
    geom = geometry(nrows, ncols, chunks, fixed_plg=plg)
    if geom["plg"] != plg:
        raise AssertionError("ME geometry differs from RTL adapter")
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


def wo_a_fp8_to_bf16(codes: np.ndarray, scales: np.ndarray) -> np.ndarray:
    """The released wo_a FP8 QDQ followed by the golden's BF16 RNE boundary."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools import hdc_golden as G
    from tools import hdc_golden_v41 as V

    if codes.dtype != np.uint8 or scales.dtype != np.uint8 or codes.ndim != 2 or scales.ndim != 2:
        raise ValueError("wo_a requires FP8 codes and UE8M0 bytes")
    nrows, cols = codes.shape
    if nrows % 32 or cols % 32 or scales.shape != (nrows // 32, cols // 32):
        raise ValueError("wo_a 32x32 scale shape mismatch")
    if np.any((codes == 0x7f) | (codes == 0xff)):
        raise ValueError("wo_a contains E4M3 NaN code")
    out = np.empty((nrows, cols), dtype=np.uint16)
    for r in range(0, nrows, 32):
        exponent = scales[r // 32].astype(np.int16) - 127
        q = V.E4M3[codes[r:r + 32]].reshape(32, cols // 32, 32)
        dense = (q * np.exp2(exponent).reshape(1, cols // 32, 1)).astype(np.float32)
        out[r:r + 32] = (G.bits(G.to_bf16(dense.reshape(32, cols))) >> 16).astype(np.uint16)
    return out


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
    expert_match = re.fullmatch(r"exp(\d+)\.(w[123])", name)
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
        "source_experts_populated": manifest.get("experts_populated"),
        "rom_capacity_bytes": CAPACITY_BYTES,
        "output_format": "address-major, 64 bank lanes per address, little-endian lane words; FP8: 32 code bytes plus scale byte, FP4: 16 packed code bytes plus scale byte",
        "matrices": {name: {
            "engine": "qe", "base_word": matrix_base, "word_count": geom["word_count"],
            "nrows": int(codes.shape[0]), "ncols": int(ncols),
            "format": format_name, "source_weight_sha256": weight["sha256"],
            "source_scale_sha256": scale["sha256"], "geometry": geom,
            "expert_stride_words": stride, "expert_id_base": base_word if stride is not None else None,
            "expert_family": f"exp.{expert_match.group(2)}" if expert_match else None,
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
        "source_experts_populated": manifest.get("experts_populated"),
        "constants": {name: {
            "engine": "crom", "base_word": base_word,
            "word_count": int(bits.size), "format": "FP32_lo_plus_zero_hi",
            "source_format": entry["format"], "source_tensor_sha256": entry["sha256"],
            "output_image_sha256": sha256(output), "output_image_bytes": output.stat().st_size,
        }},
        "matrix_coverage": "none",
        "unplaced_note": "All other CROM entries, generated RoPE values, Engram token map, and ME/QE/HE weights remain unplaced.",
    }


def pack_pre0_constant(manifest_path: Path, output: Path, base_word: int) -> dict:
    """The model-independent four-value HC initial state used by the builder."""
    manifest = json.loads(manifest_path.read_text())
    if base_word < 0 or base_word + 4 >= (1 << 30):
        raise ValueError("pre0 CROM address outside A30")
    words = np.zeros((4, 2), dtype="<u4")
    words[0, 0] = 0x3f800000
    output.parent.mkdir(parents=True, exist_ok=True)
    words.tofile(output)
    if np.fromfile(output, dtype="<u4").reshape(4, 2).tolist() != words.tolist():
        raise AssertionError("pre0 CROM readback mismatch")
    return {
        "schema": SCHEMA, "status": "generated_constant_exact_readback",
        "claim_boundary": "One generated CROM constant; no complete die CROM or token execution.",
        "source_image_manifest": str(manifest_path),
        "source_image_manifest_sha256": sha256(manifest_path),
        "layout_tool_sha256": sha256(Path(__file__)),
        "source_commit": manifest["source_commit"],
        "source_sha256": manifest["source_sha256"],
        "checkpoint": manifest["checkpoint"],
        "layer": manifest["layer"], "rank": manifest["rank"],
        "source_experts_populated": manifest.get("experts_populated"),
        "constants": {"pre0": {
            "engine": "crom", "base_word": base_word, "word_count": 4,
            "format": "FP32_lo_plus_zero_hi",
            "generated_rule": "hdc_program_v41.Layout: [1.0, 0.0, 0.0, 0.0]",
            "output_image_sha256": sha256(output), "output_image_bytes": output.stat().st_size,
        }},
        "matrix_coverage": "none",
    }


def pack_unquantized_from_manifest(manifest_path: Path, image_dir: Path, name: str,
                                   engine: str, output: Path, base_word: int = 0) -> dict:
    """One source-pinned BF16 ME or FP32 HE matrix with exact bank readback."""
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema") != "opentallas.rtl.hdc_v41x_fullshape_layers.v1.die_layer_images":
        raise ValueError("unrecognized input manifest schema")
    key = f"w.{name}"
    entry = manifest["files"].get(key)
    required = ("F8_E4M3" if name == "wo_a" and engine == "me" else
                "BF16" if engine == "me" else "F32" if engine == "he" else None)
    if required is None or entry is None or entry["format"] != required:
        raise ValueError("missing or wrong-format ME/HE matrix")
    path = image_dir / f"{key}.bin"
    if not path.is_file() or sha256(path) != entry["sha256"]:
        raise ValueError("missing or wrong source-pinned ME/HE matrix")
    raw = np.fromfile(path, dtype=np.uint8)
    if int(np.prod(entry["shape"])) != raw.size:
        raise ValueError("ME/HE source byte shape mismatch")
    nrows, row_bytes = entry["shape"]
    source_scale_sha = None
    if engine == "me" and name == "wo_a":
        scale_entry = manifest["files"].get("w.wo_a.scale")
        scale_path = image_dir / "w.wo_a.scale.bin"
        if (scale_entry is None or scale_entry["format"] != "F8_E8M0" or
                not scale_path.is_file() or sha256(scale_path) != scale_entry["sha256"]):
            raise ValueError("missing or wrong source-pinned wo_a scale")
        codes = raw.reshape(nrows, row_bytes)
        scales = np.fromfile(scale_path, dtype=np.uint8).reshape(scale_entry["shape"])
        bits = wo_a_fp8_to_bf16(codes, scales)
        image, geom = pack_me_bf16(bits, base_word)
        verify_me(image, bits, geom)
        width_per_address = geom["banks"] * 4
        fmt = "FP8_QDQ_then_BF16_as_FP32_bank_word"
        source_scale_sha = scale_entry["sha256"]
    elif engine == "me":
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
        "source_experts_populated": manifest.get("experts_populated"),
        "matrices": {name: {
            "engine": engine, "base_word": base_word,
            "word_count": geom["word_count"], "nrows": nrows,
            "ncols": int(bits.shape[1]), "format": fmt,
            "source_weight_sha256": entry["sha256"],
            "source_scale_sha256": source_scale_sha,
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
    expert_regions = {}
    source_experts = inputs[0].get("source_experts_populated")
    for path, data in zip(paths, inputs):
        if data.get("schema") != SCHEMA or (data["source_image_manifest_sha256"], data["layer"], data["rank"]) != pinned:
            raise ValueError("incompatible source image or layout schema")
        if data.get("source_experts_populated") != source_experts:
            raise ValueError("different source expert coverage")
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
            family = entry.get("expert_family")
            if family:
                old = expert_regions.get(family)
                descriptor = (entry["engine"], start, end, bytes_per_bank, family)
                if old is None:
                    expert_regions[family] = descriptor
                    regions.append(descriptor)
                elif old != descriptor:
                    raise ValueError(f"expert family region mismatch: {family}")
            else:
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
    coverage = {family: sorted({eid for entry in matrices.values()
                                if entry.get("expert_family") == family
                                for eid in entry["expert_ids_materialized"]})
                for family in expert_regions}
    token_selected = (source_experts is not None and
                      all(coverage.get(f"exp.w{kind}") == sorted(source_experts)
                          for kind in (1, 2, 3)))
    return {
        "schema": SCHEMA, "status": "partial_rank_layout_verified",
        "claim_boundary": "Source-pinned partial rank layout. Missing weights/constants and unmaterialized experts prevent full-layer/token claims.",
        "source_image_manifest_sha256": pinned[0], "layer": pinned[1], "rank": pinned[2],
        "source_records_sha256": {str(path): sha256(path) for path in paths},
        "matrices": matrices, "constants": constants,
        "source_experts_populated": source_experts,
        "expert_family_coverage": coverage,
        "selected_expert_weights_complete": token_selected,
        "expert_access_policy": "fail_closed_if_any_requested_id_lacks_w1_w3_or_w2",
        "rom_capacity_bytes": CAPACITY_BYTES, "reserved_bytes": reserved_bytes,
        "regions": [dict(engine=engine, start_word=start, end_word_exclusive=end,
                         bytes_per_bank_word=width, name=name)
                    for engine, start, end, width, name in sorted(regions)],
        "all_experts_materialized": all(e.get("all_experts_materialized") is not False
                                        for e in matrices.values()),
        "complete_die_image": False,
    }


def validate_expert_access(layout: dict, requested_ids: list[int] | tuple[int, ...]) -> None:
    """Fail before a token reads an unmaterialized routed-expert slot."""
    requested = set(requested_ids)
    if any(not isinstance(eid, int) or not 0 <= eid < 384 for eid in requested):
        raise ValueError("invalid routed expert ID")
    coverage = layout.get("expert_family_coverage", {})
    for kind in ("w1", "w3", "w2"):
        missing = requested - set(coverage.get(f"exp.{kind}", ()))
        if missing:
            raise ValueError(f"unmaterialized {kind} expert IDs: {sorted(missing)}")


def derive_hbm_sector_map(layout: dict) -> dict:
    """Map identical bank-image bytes to 256-bit HBM sectors, by ROM region.

    This is an address/payload equivalence check.  The present weight-window
    RTL cannot request a 34- or 66-sector QE word and must not be credited.
    """
    sector = 0
    regions = []
    for region in sorted((r for r in layout["regions"] if r["engine"] != "crom"),
                         key=lambda r: (r["engine"], r["start_word"])):
        banks = 8 if region["engine"] == "he" else 64
        bytes_per_word = banks * region["bytes_per_bank_word"]
        if bytes_per_word % 32:
            raise ValueError("weight bank word is not sector aligned")
        spw = bytes_per_word // 32
        count = (region["end_word_exclusive"] - region["start_word"]) * spw
        if sector + count >= (1 << 28):
            raise ValueError("HBM sector address exceeds current HAW28")
        regions.append(dict(**region, hbm_sector_base=sector,
                            hbm_sector_end_exclusive=sector + count,
                            sectors_per_word=spw))
        sector += count
    by_key = {(r["engine"], r["name"]): r for r in regions}
    matrix_map = {}
    for name, entry in layout["matrices"].items():
        region_name = entry.get("expert_family") or name
        region = by_key[(entry["engine"], region_name)]
        offset = entry["base_word"] - region["start_word"]
        hbase = region["hbm_sector_base"] + offset * region["sectors_per_word"]
        matrix_map[name] = dict(hbm_sector_base=hbase,
                                sectors_per_word=region["sectors_per_word"],
                                sector_count=entry["word_count"] * region["sectors_per_word"],
                                payload_sha256=entry["output_image_sha256"])
        if entry["output_image_bytes"] != matrix_map[name]["sector_count"] * 32:
            raise ValueError(f"{name}: ROM bytes do not match HBM sectors")
    return {
        "status": "same_payload_sector_map_only",
        "claim_boundary": "HBM sectors hold byte-identical bank words, but full-shape HBM weight fetch RTL is not yet implemented; existing LENW4 window cannot request 34/66-sector QE words.",
        "sector_bytes": 32, "hbm_sector_count_reserved": sector,
        "hbm_bytes_reserved": sector * 32,
        "regions": regions, "matrices": matrix_map,
    }


def rtl_engine_preflight(layout: dict) -> dict:
    """Compare exact image geometry with current adopted core bank/buffer defaults."""
    sources = {
        "core": ROOT / "rtl/hdc/v41x/ot_hdc_core_v41x.sv",
        "me": ROOT / "rtl/hdc/v41x/ot_hdc_v41x_me_adapt.sv",
        "he": ROOT / "rtl/hdc/v41x/ot_hdc_v41x_he_adapt.sv",
    }

    def param(path: Path, name: str) -> int:
        # A plain default, or a profile select `FULL_SHAPE ? full : reduced` (the full-shape value applies).
        text = path.read_text()
        match = re.search(rf"parameter\s+integer\s+{name}\s*=\s*FULL_SHAPE\s*\?\s*(\d+)\s*:\s*\d+", text) or \
            re.search(rf"parameter\s+integer\s+{name}\s*=\s*(\d+)", text)
        if match is None:
            raise ValueError(f"cannot read RTL parameter {name} in {path}")
        return int(match.group(1))

    matrices = layout["matrices"]
    me = [x for x in matrices.values() if x["engine"] == "me"]
    he = [x for x in matrices.values() if x["engine"] == "he"]
    me_end = max((x["base_word"] + x["word_count"] for x in me), default=0)
    he_end = max((x["base_word"] + x["word_count"] for x in he), default=0)
    required = {
        "me_bank_aw": (me_end - 1).bit_length() if me_end else 0,
        "me_kmax": max((x["ncols"] for x in me), default=0),
        "he_bank_aw": (he_end - 1).bit_length() if he_end else 0,
        "he_kcmax": max((x["ncols"] // 8 for x in he), default=0),
    }
    current = {
        "me_bank_aw": param(sources["core"], "MBAW"),
        "me_kmax": param(sources["me"], "KMAX"),
        "he_bank_aw": param(sources["core"], "HBAW"),
        "he_kcmax": param(sources["he"], "KCMAX"),
    }
    gaps = {name: {"required": value, "current": current[name]}
            for name, value in required.items() if value > current[name]}
    return {
        "status": "rtl_parameter_gap" if gaps else "rtl_parameter_widths_sufficient",
        "required": required, "current_defaults": current, "gaps": gaps,
        "source_sha256": {name: sha256(path) for name, path in sources.items()},
        "claim_boundary": "Static parameter check only; sufficient widths would still need elaboration, exact shard simulation and physical closure.",
    }


def assemble_token_layer0(manifest_path: Path, image_dir: Path, out_dir: Path) -> dict:
    """Address-plan all supported weights of one token-selected layer-0 shard.

    Routed experts occupy their absolute 0..383 IDs in three fixed-stride
    regions.  Only the six selected IDs are materialized in this image.
    Unsupported/absent inputs are listed so a consumer must fail closed.
    """
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("layer") != 0 or manifest.get("rank") != 0 or manifest.get("context") not in (200000, 1048576):
        raise ValueError("assembler is pinned to L0/rank0 at the 200K or 1M shard")
    out_dir.mkdir(parents=True, exist_ok=True)
    record_paths = []
    qe_base = 0

    def emit(name: str, engine: str, base: int) -> dict:
        output = out_dir / f"{name}.{engine}.bin"
        if engine == "qe":
            data = pack_from_manifest(manifest_path, image_dir, name, output, base)
        elif engine == "crom":
            data = pack_constant_from_manifest(manifest_path, image_dir, name, output, base)
        else:
            data = pack_unquantized_from_manifest(manifest_path, image_dir, name, engine, output, base)
        path = out_dir / f"{name}.{engine}.json"
        path.write_text(json.dumps(data, indent=2) + "\n")
        record_paths.append(path)
        return data

    dense_qe = ("wq_a", "wkv", "wq_b", "wo_b", "shared.w1", "shared.w3", "shared.w2")
    for name in dense_qe:
        entry = emit(name, "qe", qe_base)["matrices"][name]
        qe_base += entry["word_count"]
    for kind in ("w1", "w3", "w2"):
        region_base = qe_base
        stride = None
        for expert_id in manifest["experts_populated"]:
            name = f"exp{expert_id}.{kind}"
            entry = emit(name, "qe", region_base)["matrices"][name]
            if stride is None:
                stride = entry["expert_stride_words"]
            elif stride != entry["expert_stride_words"]:
                raise ValueError("routed expert stride differs within family")
        qe_base = region_base + 384 * stride
    me_base = 0
    for name in ("gate", "wo_a"):
        entry = emit(name, "me", me_base)["matrices"][name]
        me_base += entry["word_count"]
    he_base = 0
    for name in ("hc_attn_fn", "hc_ffn_fn"):
        entry = emit(name, "he", he_base)["matrices"][name]
        he_base += entry["word_count"]
    crom_base = 0
    constants = ("attn_norm", "ffn_norm", "q_norm", "kv_norm",
                 "hc_attn_scale", "hc_attn_base", "hc_ffn_scale", "hc_ffn_base",
                 "attn_sink", "gate.bias")
    for name in constants:
        entry = emit(name, "crom", crom_base)["constants"][name]
        crom_base += entry["word_count"]
    pre0_output = out_dir / "pre0.crom.bin"
    pre0_data = pack_pre0_constant(manifest_path, pre0_output, crom_base)
    pre0_path = out_dir / "pre0.crom.json"
    pre0_path.write_text(json.dumps(pre0_data, indent=2) + "\n")
    record_paths.append(pre0_path)
    crom_base += 4
    combined = combine_layout_records(record_paths)
    validate_expert_access(combined, list(manifest["experts_populated"]))
    known = {f"w.{name}" for name in (*dense_qe, "gate", "wo_a", "hc_attn_fn", "hc_ffn_fn", *constants)}
    known |= {f"w.exp{eid}.{kind}" for eid in manifest["experts_populated"]
              for kind in ("w1", "w3", "w2")}
    missing = sorted(k for k in manifest["files"] if k.startswith("w.") and
                     not k.endswith(".scale") and k not in known)
    combined.update(
        status="token_selected_partial_rank_layout",
        claim_boundary="Every present source tensor and selected expert weight is placed; generated CROM/Engram/RoPE contracts and RTL binding still prevent token execution.",
        source_commit=manifest["source_commit"],
        source_sha256=manifest["source_sha256"],
        checkpoint=manifest["checkpoint"],
        source_image_manifest=str(manifest_path),
        source_image_manifest_sha256=sha256(manifest_path),
        layout_tool_sha256=sha256(Path(__file__)),
        context=manifest["context"],
        selected_expert_ids=list(manifest["experts_populated"]),
        selected_expert_weights_complete=combined["selected_expert_weights_complete"],
        unplaced_source_tensors=missing,
        unplaced_generated=("rope_plain", "rope_yarn", "tmap"),
        complete_die_image=False,
        token_runnable=False,
    )
    combined["hbm_weight_layout"] = derive_hbm_sector_map(combined)
    combined["rtl_engine_preflight"] = rtl_engine_preflight(combined)
    return combined


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
    one.add_argument("--assemble-token-layer0", action="store_true")
    one.add_argument("--derive-hbm-map", action="store_true")
    one.add_argument("--preflight-rtl", action="store_true")
    ap.add_argument("--output", type=Path)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--input-layout", type=Path)
    ap.add_argument("--record", type=Path, required=True)
    ap.add_argument("--base-word", type=int, default=0)
    ap.add_argument("--chunks", type=int, default=8)
    a = ap.parse_args()
    if a.preflight_rtl:
        if not a.input_layout:
            ap.error("RTL preflight requires --input-layout")
        layout = json.loads(a.input_layout.read_text())
        record = {
            "schema": "opentallas.v41x.fullshape.weight_rtl_preflight.v1",
            "status": "source_pinned_parameter_preflight",
            "source_layout_sha256": sha256(a.input_layout),
            "source_image_manifest_sha256": layout["source_image_manifest_sha256"],
            "source_commit": layout["source_commit"],
            "layout_tool_sha256": sha256(Path(__file__)),
            "rtl_engine_preflight": rtl_engine_preflight(layout),
        }
    elif a.derive_hbm_map:
        if not a.input_layout:
            ap.error("HBM map requires --input-layout")
        layout = json.loads(a.input_layout.read_text())
        record = {
            "schema": "opentallas.v41x.fullshape.hbm_sector_map.v1",
            "status": "same_payload_sector_map_only",
            "source_layout_sha256": sha256(a.input_layout),
            "source_image_manifest_sha256": layout["source_image_manifest_sha256"],
            "source_commit": layout["source_commit"],
            "layout_tool_sha256": sha256(Path(__file__)),
            "hbm_weight_layout": derive_hbm_sector_map(layout),
        }
    elif a.assemble_token_layer0:
        if not a.input_manifest or not a.image_dir or not a.out_dir:
            ap.error("assembly requires --input-manifest, --image-dir and --out-dir")
        record = assemble_token_layer0(a.input_manifest, a.image_dir, a.out_dir)
    elif a.combine_record:
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
    if a.preflight_rtl:
        summary.update(gaps=record["rtl_engine_preflight"]["gaps"])
    elif a.derive_hbm_map:
        summary.update(sectors=record["hbm_weight_layout"]["hbm_sector_count_reserved"],
                       matrices=len(record["hbm_weight_layout"]["matrices"]))
    elif a.assemble_token_layer0:
        summary.update(matrices=len(record["matrices"]), constants=len(record["constants"]),
                       selected_experts=record["selected_expert_ids"],
                       reserved_bytes=record["reserved_bytes"],
                       unplaced=record["unplaced_source_tensors"])
    elif a.combine_record:
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
