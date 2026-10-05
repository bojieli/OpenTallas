#!/usr/bin/env python3
"""Source-pinned V4.1 rank0 QE image of an indexed layer (layer 20; also layer 0) in the core's exact 16-lane
stream order.  A copy of tools/v41_fullshape_qe_stream_image.py generalised to layer 20 (the indexer's wq_b in
the dense list), kept separate so the layer-0 records pinned to that tool stay current.

The logical word is 16 * 272 bits. Routed FP4 words are stored as 16 * 144
bits and require expansion at the QE port. No RTL or throughput claim is made.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from tools import v41_fullshape_weight_layout as W
SCHEMA = "opentallas.v41x.fullshape.qe_stream.v1"
LANES = 16
SLOTS = 8
COLS = 32
WORD_BYTES = LANES * 34
FP4_WORD_BYTES = LANES * 18
SELECTED = (110, 112, 141, 144, 357, 361)
MATRIX_ORDER = ("wq_a", "wkv", "wq_b", "wo_b", "shared.w1", "shared.w3", "shared.w2")
FAMILY_ORDER = ("w1", "w3", "w2")
FULL_NAMES = MATRIX_ORDER + tuple(f"exp{i}.{family}" for family in FAMILY_ORDER for i in SELECTED)
DEFAULT_OTHER = ROOT / "results/rtl/hdc_v41x_fullshape_token_selected_rom_layout.json"


def full_names(selected, layer=0) -> tuple[str, ...]:
    dense = MATRIX_ORDER + (("indexer.wq_b",) if layer == 20 else ())
    return dense + tuple(f"exp{i}.{family}" for family in FAMILY_ORDER for i in selected)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for chunk in iter(lambda: src.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def source_matrix(manifest: dict, folder: Path, name: str) -> tuple[np.ndarray, np.ndarray, bool]:
    def one(key: str, expected: str) -> np.ndarray:
        meta = manifest["files"].get(key)
        if meta is None or meta["format"] != expected or meta["dtype"] != "uint8":
            raise ValueError(f"missing or unexpected checkpoint format: {key}")
        path = folder / f"{key}.bin"
        if not path.is_file() or digest(path) != meta["sha256"]:
            raise ValueError(f"source-pinned hash mismatch: {key}")
        data = np.fromfile(path, np.uint8)
        if data.size != int(np.prod(meta["shape"])):
            raise ValueError(f"source shape mismatch: {key}")
        return data.reshape(meta["shape"])

    fp4 = name.startswith("exp")
    codes = one(f"w.{name}", "I8" if fp4 else "F8_E4M3")
    scales = one(f"w.{name}.scale", "F8_E8M0")
    nrows, packed_cols = codes.shape
    if nrows <= 0 or nrows % 16 or (packed_cols * (2 if fp4 else 1)) % COLS:
        raise ValueError(f"unsupported matrix geometry: {name}")
    nb = packed_cols * (2 if fp4 else 1) // COLS
    if scales.shape != ((nrows if fp4 else nrows // 32), nb):
        raise ValueError(f"checkpoint scale shape mismatch: {name}")
    if not fp4 and np.any((codes == 0x7f) | (codes == 0xff)):
        raise ValueError(f"E4M3 NaN code: {name}")
    return codes, scales, fp4


def pack_stream(codes: np.ndarray, scales: np.ndarray, fp4: bool) -> tuple[np.ndarray, np.ndarray, dict]:
    """Return 544-B logical words and packed 544/288-B physical words.

    Word address = (round * nb + block) * 8 + slot; lane row =
    (round * 8 + slot) * 16 + lane. Padded rows have zero codes and exponent.
    """
    nrows, packed_cols = codes.shape
    ncols = packed_cols * (2 if fp4 else 1)
    nb = ncols // COLS
    tiles = (nrows + LANES * SLOTS - 1) // (LANES * SLOTS)
    if ncols % COLS or scales.shape != ((nrows if fp4 else nrows // 32), nb):
        raise ValueError("codes and scale shape mismatch")
    if not fp4 and np.any((codes == 0x7f) | (codes == 0xff)):
        raise ValueError("E4M3 NaN code")
    count = tiles * nb * SLOTS
    logical = np.zeros((count, LANES, 34), np.uint8)
    physical = np.zeros((count, LANES, 18 if fp4 else 34), np.uint8)
    for r in range(tiles):
        for kb in range(nb):
            for j in range(SLOTS):
                idx = (r * nb + kb) * SLOTS + j
                rows = (r * SLOTS + j) * LANES + np.arange(LANES)
                active = rows < nrows
                rr = rows[active]
                if fp4:
                    packed = codes[rr, kb * 16:(kb + 1) * 16]
                    logical[idx, active, 0:32:2] = packed & 15
                    logical[idx, active, 1:32:2] = packed >> 4
                    physical[idx, active, :16] = packed
                    exponent = scales[rr, kb].astype(np.int16) - 127
                else:
                    raw = codes[rr, kb * 32:(kb + 1) * 32]
                    logical[idx, active, :32] = raw
                    physical[idx, active, :32] = raw
                    exponent = scales[rr // 32, kb].astype(np.int16) - 127
                e = exponent.astype("<i2").view(np.uint8).reshape(-1, 2)
                logical[idx, active, 32:34] = e
                physical[idx, active, -2:] = e
    geom = dict(nout=nrows, nb=nb, tiles=tiles, slots=SLOTS, lanes=LANES,
                word_count=count, logical_bytes_per_word=WORD_BYTES,
                physical_bytes_per_word=FP4_WORD_BYTES if fp4 else WORD_BYTES,
                padded_rows=tiles * SLOTS * LANES - nrows, fp4=fp4)
    return logical, physical, geom


def verify_stream(logical: np.ndarray, physical: np.ndarray, codes: np.ndarray,
                  scales: np.ndarray, geom: dict) -> None:
    fp4 = geom["fp4"]
    nrows, _ = codes.shape
    if logical.shape != (geom["word_count"], LANES, 34):
        raise AssertionError("logical word shape")
    if physical.shape != (geom["word_count"], LANES, 18 if fp4 else 34):
        raise AssertionError("physical word shape")
    for r in range(geom["tiles"]):
        for kb in range(geom["nb"]):
            for j in range(SLOTS):
                idx = (r * geom["nb"] + kb) * SLOTS + j
                for lane in range(LANES):
                    row = (r * SLOTS + j) * LANES + lane
                    word = logical[idx, lane]
                    compact = physical[idx, lane]
                    if row >= nrows:
                        if word.any() or compact.any():
                            raise AssertionError("nonzero final-tile padding")
                        continue
                    if fp4:
                        p = codes[row, kb * 16:(kb + 1) * 16]
                        if not np.array_equal(word[0:32:2], p & 15) or not np.array_equal(word[1:32:2], p >> 4):
                            raise AssertionError(f"FP4 lane mismatch at {idx}:{lane}")
                        if not np.array_equal(compact[:16], p):
                            raise AssertionError(f"FP4 physical mismatch at {idx}:{lane}")
                        scale = scales[row, kb]
                    else:
                        p = codes[row, kb * 32:(kb + 1) * 32]
                        if not np.array_equal(word[:32], p) or not np.array_equal(compact[:32], p):
                            raise AssertionError(f"FP8 lane mismatch at {idx}:{lane}")
                        scale = scales[row // 32, kb]
                    expected = int(scale) - 127
                    if int.from_bytes(word[32:34].tobytes(), "little", signed=True) != expected:
                        raise AssertionError(f"logical exponent mismatch at {idx}:{lane}")
                    if int.from_bytes(compact[-2:].tobytes(), "little", signed=True) != expected:
                        raise AssertionError(f"physical exponent mismatch at {idx}:{lane}")


def verify_numeric_samples(logical: np.ndarray, codes: np.ndarray,
                           scales: np.ndarray, geom: dict) -> int:
    """Independently decode selected real source elements through the golden LUT."""
    from tools import hdc_golden_v41 as V
    fp4 = geom["fp4"]
    checked = 0
    for row in sorted({0, geom["nout"] // 2, geom["nout"] - 1}):
        for kb in sorted({0, geom["nb"] // 2, geom["nb"] - 1}):
            word = ((row // 128) * geom["nb"] + kb) * SLOTS + (row // LANES) % SLOTS
            lane = row % LANES
            exponent = int.from_bytes(logical[word, lane, 32:34].tobytes(), "little", signed=True)
            src_scale = int(scales[row if fp4 else row // 32, kb]) - 127
            if exponent != src_scale:
                raise AssertionError("numeric scale mismatch")
            for col in (0, 15, 31):
                code = int(logical[word, lane, col])
                if fp4:
                    packed = int(codes[row, kb * 16 + col // 2])
                    original = (packed >> (4 * (col & 1))) & 15
                    lut = V.E2M1
                else:
                    original = int(codes[row, kb * 32 + col])
                    lut = V.E4M3
                actual = np.ldexp(float(lut[code]), exponent)
                expected = np.ldexp(float(lut[original]), src_scale)
                if code != original or actual != expected:
                    raise AssertionError("numeric LUT mismatch")
                checked += 1
    return checked


def build(manifest_path: Path, source_dir: Path, out_dir: Path,
          names: tuple[str, ...] | None = None, other_path: Path = DEFAULT_OTHER) -> dict:
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("layer") not in (0, 20) or manifest.get("rank") != 0 or manifest.get("tp") != 4:
        raise ValueError("this gate supports shipped TP4 layer 0 / 20, rank 0 only")
    # The token's router selection (the image manifest's populated experts); the 200K shard is SELECTED.
    selected = tuple(manifest.get("experts_populated", SELECTED))
    FULL = full_names(selected, manifest["layer"])
    if names is None:
        names = FULL
    if len(names) != len(set(names)) or any(name not in FULL for name in names):
        raise ValueError("invalid or repeated matrix name")
    out_dir.mkdir(parents=True, exist_ok=True)
    matrices = {}
    base = 0
    family_base = {}
    physical_base_sector = 0
    numeric_samples = 0
    for name in names:
        codes, scales, fp4 = source_matrix(manifest, source_dir, name)
        logical, physical, geom = pack_stream(codes, scales, fp4)
        verify_stream(logical, physical, codes, scales, geom)
        numeric_samples += verify_numeric_samples(logical, codes, scales, geom)
        if fp4:
            family = name.rsplit(".", 1)[1]
            stride = geom["word_count"]
            if family not in family_base:
                family_base[family] = (base, physical_base_sector, stride)
                base += 384 * stride
                physical_base_sector += 384 * stride * 9
            fbase, hbase, expected_stride = family_base[family]
            if stride != expected_stride:
                raise ValueError("expert stride mismatch")
            expert_id = int(name.split(".")[0][3:])
            address = fbase + expert_id * stride
            sector_address = hbase + expert_id * stride * 9
        else:
            expert_id = None
            stride = None
            address = base
            sector_address = physical_base_sector
            base += geom["word_count"]
            physical_base_sector += geom["word_count"] * 17
        safe = name.replace(".", "_")
        path = out_dir / f"qe_{safe}.bin"
        path.write_bytes(physical.tobytes())
        matrices[name] = dict(engine="qe", format="FP4_E2M1" if fp4 else "FP8_E4M3",
                              base_word=address, word_count=geom["word_count"],
                              expert_id_base=family_base[name.rsplit('.',1)[1]][0] if fp4 else None,
                              expert_stride_words=stride, geometry=geom,
                              logical_word_bytes=WORD_BYTES,
                              physical_word_bytes=geom["physical_bytes_per_word"],
                              hbm_sector_base=sector_address,
                              sectors_per_word=9 if fp4 else 17,
                              image_file=path.name, image_layout="packed_fp4_16x144" if fp4 else "fp8_16x272",
                              image_sha256=digest(path), logical_stream_sha256=hashlib.sha256(logical.tobytes()).hexdigest(),
                              image_bytes=path.stat().st_size,
                              adapter_required=fp4)
    if names == FULL:
        if tuple(family_base) != FAMILY_ORDER:
            raise AssertionError("missing expert family")
    other = json.loads(other_path.read_text())
    other_bytes = sum((r["end_word_exclusive"] - r["start_word"]) *
                      (r["bytes_per_bank_word"] * (64 if r["engine"] == "me" else 8 if r["engine"] == "he" else 1))
                      for r in other["regions"] if r["engine"] != "qe")
    physical_bytes = physical_base_sector * 32
    direct_bytes = base * WORD_BYTES
    full = names == FULL
    if full and physical_bytes + other_bytes > W.CAPACITY_BYTES:
        raise ValueError("packed physical QE image exceeds die ROM capacity")
    return dict(schema=SCHEMA, status="source_pinned_layout_readback_pass" if full else "partial_matrix_gate",
                claim_boundary="image/addresses only; FP4 port adapter and full RTL token pending",
                source_image_manifest=str(manifest_path.relative_to(ROOT)) if manifest_path.is_relative_to(ROOT) else str(manifest_path),
                source_image_manifest_sha256=digest(manifest_path),
                other_engine_layout_manifest=str(Path(other_path).resolve().relative_to(ROOT)),
                other_engine_layout_sha256=digest(other_path),
                layout_tool_sha256=digest(Path(__file__)),
                source_commit=manifest.get("source_commit"), source_sha256=manifest.get("source_sha256"),
                checkpoint=manifest.get("checkpoint"),
                layer=manifest["layer"], rank=0, context=manifest.get("context"), matrices=matrices,
                selected_expert_ids=list(selected), all_experts_materialized=False,
                expert_family_coverage={f"exp.{family}": list(selected) for family in FAMILY_ORDER},
                expert_access_policy="only materialized selected IDs; other slots fail closed",
                logical_qrom_words=base, logical_direct_bytes=direct_bytes,
                physical_qe_bytes_reserved=physical_bytes, other_engine_bytes_reserved=other_bytes,
                packed_die_bytes_reserved=physical_bytes + other_bytes,
                rom_capacity_bytes=W.CAPACITY_BYTES,
                direct_expanded_fits_die=direct_bytes + other_bytes <= W.CAPACITY_BYTES,
                packed_requires_fp4_port_adapter=True,
                numeric_lut_elements_checked=numeric_samples,
                token_runnable=False)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, default=ROOT / "results/rtl/hdc_v41x_fullshape_200k_l0_rank0_image.json")
    p.add_argument("--source-dir", type=Path, default=Path("/tmp/codex_v41_fullshape_golden/images/ctx200000_L00_r0"))
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--record", type=Path, required=True)
    p.add_argument("--matrix", action="append")
    p.add_argument("--other-layout", type=Path, default=DEFAULT_OTHER,
                   help="the token-selected ME/HE/CROM layout record of the same shard")
    args = p.parse_args()
    record = build(args.manifest, args.source_dir, args.output_dir,
                   tuple(args.matrix) if args.matrix else None, args.other_layout)
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: record[k] for k in ("status", "logical_qrom_words", "packed_die_bytes_reserved", "direct_expanded_fits_die")}))


if __name__ == "__main__":
    main()
