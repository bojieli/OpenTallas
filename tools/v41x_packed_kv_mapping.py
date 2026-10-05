#!/usr/bin/env python3
"""Source-pinned address proof for a full-shape V4.1 packed window KV ring.

This is an executable interface contract, not a die prefetch or quantizer gate.
Core addresses count FP32/BF16 element lanes. HBM addresses count 32-byte sectors.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from runtime.prefill.v41_aux_kv_rows import (WINDOW_CODE_BYTES, WINDOW_ELEMENTS,
                                             WINDOW_ROW_BYTES, WINDOW_SCALE_BYTES,
                                             pack_window_row, parse_window_row)
from runtime.prefill.v41_hbm_placement import (MAX_CONTEXT, SECTOR, WINDOW_SLOTS)

ROOT = Path(__file__).resolve().parents[1]
HD = WINDOW_ELEMENTS
LANES = 16
PITCH_SECTORS = (WINDOW_ROW_BYTES + SECTOR - 1) // SECTOR
USER_SECTORS = WINDOW_SLOTS * PITCH_SECTORS
SECTOR_ADDRESS_BITS = 30
COMPRESSED_ROW_BYTES = 288


@dataclass(frozen=True)
class CoreAddress:
    kind: str
    slot: int
    dim: int
    scalar_offset: int
    word_offset: int
    lane: int


def core_scalar(kind: str, position: int, dim: int) -> CoreAddress:
    """Return offsets relative to the corresponding KT/KR region base.

    KT is transposed in groups of 16 rows; KR is row major. Those regions are
    two aliases of one packed row in HBM, not two independent HBM copies.
    """
    if kind not in ("KT", "KR") or not 0 <= position < MAX_CONTEXT or not 0 <= dim < HD:
        raise ValueError("invalid core window KV coordinate")
    slot = position % WINDOW_SLOTS
    if kind == "KT":
        scalar = (slot // LANES) * (HD * LANES) + dim * LANES + slot % LANES
    else:
        scalar = slot * HD + dim
    return CoreAddress(kind, slot, dim, scalar, scalar // LANES, scalar % LANES)


def invert_core_scalar(kind: str, scalar: int) -> tuple[int, int]:
    if kind not in ("KT", "KR") or not 0 <= scalar < WINDOW_SLOTS * HD:
        raise ValueError("invalid core window KV scalar address")
    if kind == "KT":
        group, remainder = divmod(scalar, HD * LANES)
        dim, row_lane = divmod(remainder, LANES)
        return group * LANES + row_lane, dim
    return divmod(scalar, HD)


def attention_local_row(position: int, local_row: int, selected_ckv_rows: Sequence[int]) -> tuple[str, int]:
    """Classify a normalized <=640-row job; selected rows retain their CKV IDs.

    This requires a full-shape emitter/descriptor. The current reduced emitter
    uses absolute POS/T1 row counts and does not implement this normalization.
    """
    if not 0 <= position < MAX_CONTEXT or len(selected_ckv_rows) > 512:
        raise ValueError("invalid attention job")
    window_count = min(position + 1, WINDOW_SLOTS)
    if not 0 <= local_row < window_count + len(selected_ckv_rows):
        raise ValueError("local row outside attention job")
    if local_row < window_count:
        return "window", position + 1 - window_count + local_row
    source_row = selected_ckv_rows[local_row - window_count]
    if source_row < 0:
        raise ValueError("invalid selected CKV row")
    return "compressed", source_row


def attention_word_sources(kind: str, position: int, selected_ckv_rows: Sequence[int],
                           word_offset: int) -> tuple[tuple[str, int, int] | None, ...]:
    """Reverse a 512-bit local-job KT/KR word to (role, source row, dim).

    The die fetches each source row in its native packed format, then decodes
    and scatters these 16 lanes. There is no 640-row unpacked SRAM implied.
    """
    if kind not in ("KT", "KR"):
        raise ValueError("invalid attention view")
    count = min(position + 1, WINDOW_SLOTS) + len(selected_ckv_rows)
    words = ((count + LANES - 1) // LANES) * HD if kind == "KT" else count * HD // LANES
    if not 0 <= word_offset < words:
        raise ValueError("word outside local attention job")
    result = []
    for lane in range(LANES):
        scalar = word_offset * LANES + lane
        if kind == "KT":
            group, remainder = divmod(scalar, HD * LANES)
            dim, row_lane = divmod(remainder, LANES)
            local_row = group * LANES + row_lane
        else:
            local_row, dim = divmod(scalar, HD)
        if local_row >= count:
            result.append(None)  # padding in the last transposed 16-row group
        else:
            role, source_row = attention_local_row(position, local_row, selected_ckv_rows)
            result.append((role, source_row, dim))
    return tuple(result)


@dataclass(frozen=True)
class PackedAddress:
    user: int
    position: int
    slot: int
    dim: int
    row_first_sector: int
    code_sector: int
    code_byte: int
    scale_sector: int
    scale_byte: int


def packed_address(user: int, position: int, dim: int, *, region_base_sector: int,
                   region_sector_count: int, users: int) -> PackedAddress:
    """Map a core scalar to its code and shared block-scale byte in HBM.

    Each user gets a distinct 128-row ring. The caller must reserve that
    expanded region; the old one-user Placement window region is insufficient.
    """
    if not 0 <= user < users or not 0 <= position < MAX_CONTEXT or not 0 <= dim < HD:
        raise ValueError("invalid user, position, or dimension")
    if users <= 0 or region_base_sector < 0 or region_sector_count < users * USER_SECTORS:
        raise ValueError("window region does not reserve every user ring")
    region_end = region_base_sector + region_sector_count
    if region_end > 1 << SECTOR_ADDRESS_BITS:
        raise ValueError("window sector address overflows")
    slot = position % WINDOW_SLOTS
    row_first = region_base_sector + user * USER_SECTORS + slot * PITCH_SECTORS
    code_sector = row_first + dim // SECTOR
    scale_sector = row_first + WINDOW_CODE_BYTES // SECTOR
    if scale_sector >= region_end:
        raise ValueError("window sector outside region")
    return PackedAddress(user, position, slot, dim, row_first, code_sector,
                         dim % SECTOR, scale_sector, dim // 32)


def staging_word(row: bytes, kind: str, slot: int, word: int) -> tuple:
    """Gather one 512-bit core-facing word from packed rows, on demand.

    For KR a single packed row supplies 16 adjacent dimensions. For KT the
    word gathers the same dimension from 16 separately tagged packed rows.
    `row` is a single row only for KR; KT uses scatter_word below.
    """
    if kind != "KR" or not 0 <= word < HD // LANES or not 0 <= slot < WINDOW_SLOTS:
        raise ValueError("single-row staging word is KR only")
    values = parse_window_row(row).exact_values
    return values[word * LANES:(word + 1) * LANES]


def scatter_word(rows: dict[int, bytes], kind: str, word_offset: int) -> tuple:
    """Reverse the core word address to 16 exact, packed-row-decoded values."""
    if not 0 <= word_offset < WINDOW_SLOTS * HD // LANES:
        raise ValueError("word outside window ring")
    lanes = []
    for lane in range(LANES):
        slot, dim = invert_core_scalar(kind, word_offset * LANES + lane)
        lanes.append(parse_window_row(rows[slot]).exact_values[dim])
    return tuple(lanes)


class AtomicBlockStore:
    """Transaction oracle: 32 codes and one scale publish together.

    A physical writer may issue sector 0..15 and byte-strobed sector 16 in
    either order, but a later prefetch must wait until both have drained.
    This oracle marks an updated block unavailable before that point.
    """

    def __init__(self, initial: bytes):
        parse_window_row(initial)
        self.visible = bytearray(initial)
        self.pending: dict[int, tuple[bytes, int]] = {}
        self.code_done: set[int] = set()
        self.scale_done: set[int] = set()

    def begin(self, block: int, codes: bytes, scale: int) -> None:
        if not 0 <= block < 16 or len(codes) != 32 or not 0 <= scale < 255:
            raise ValueError("atomic update is one 32-code block plus finite scale")
        if block in self.pending:
            raise ValueError("block already has an outstanding update")
        self.pending[block] = (codes, scale)

    def drain_code(self, block: int) -> None:
        self.code_done.add(block)
        self._publish(block)

    def drain_scale(self, block: int) -> None:
        self.scale_done.add(block)
        self._publish(block)

    def _publish(self, block: int) -> None:
        if block in self.code_done and block in self.scale_done:
            codes, scale = self.pending.pop(block)
            self.visible[32 * block:32 * (block + 1)] = codes
            self.visible[512 + block] = scale
            self.code_done.remove(block)
            self.scale_done.remove(block)

    def read(self, block: int) -> bytes:
        if block in self.pending:
            raise RuntimeError("prefetch must wait for the atomic block update")
        return bytes(self.visible)


class TaggedWindowRing:
    """Absolute-position tag oracle for per-user reuse of 128 physical rows."""

    def __init__(self):
        self.rows: dict[tuple[int, int], tuple[int, bytes]] = {}

    def write(self, user: int, position: int, data: bytes) -> None:
        if user < 0 or not 0 <= position < MAX_CONTEXT:
            raise ValueError("invalid window tag")
        parse_window_row(data)
        self.rows[(user, position % WINDOW_SLOTS)] = (position, data)

    def read(self, user: int, position: int) -> bytes:
        if user < 0 or not 0 <= position < MAX_CONTEXT:
            raise ValueError("invalid window tag")
        tag, data = self.rows[(user, position % WINDOW_SLOTS)]
        if tag != position:
            raise ValueError("stale window ring position")
        return data


def build_record() -> dict:
    sources = [Path(__file__), ROOT / "runtime/prefill/v41_aux_kv_rows.py",
               ROOT / "runtime/prefill/v41_hbm_placement.py",
               ROOT / "tools/hdc_program_v41.py", ROOT / "tools/hdc_isa_v41.py",
               ROOT / "rtl/chip/ot_chip_v41x_window_row_codec.sv",
               ROOT / "tools/rtl_chip_v41x_window_row_codec.py",
               ROOT / "tests/test_v41x_packed_kv_mapping.py",
               ROOT / "docs/V41X_PACKED_WINDOW_KV_MAPPING.md"]
    for slot in range(WINDOW_SLOTS):
        for dim in range(HD):
            for kind in ("KT", "KR"):
                a = core_scalar(kind, slot, dim)
                assert invert_core_scalar(kind, a.scalar_offset) == (slot, dim)
    # The largest full-shape op is 640 window-format rows. Packed staging
    # stores payload bytes, while HBM transfers complete 32-byte sectors.
    max_rows = 640
    record = {
        "status": "pass", "scope": "conditional window-row address/layout proof; full-shape emitter normalization, die integration, quantizer, and timing unproved",
        "profile": "opentallas.deepseek_v41.window_fp8_e4m3_s32_e8m0.row.v1",
        "core_scalar_addresses_checked": 2 * WINDOW_SLOTS * HD,
        "core_word_bits": LANES * 32,
        "code_bytes_per_row": WINDOW_CODE_BYTES,
        "scale_bytes_per_row": WINDOW_SCALE_BYTES,
        "payload_bytes_per_row": WINDOW_ROW_BYTES,
        "hbm_sectors_per_row": PITCH_SECTORS,
        "hbm_pitch_bytes_per_row": PITCH_SECTORS * SECTOR,
        "hbm_sectors_per_user_layer_die": USER_SECTORS,
        "hbm_bytes_per_user_layer_die": USER_SECTORS * SECTOR,
        "max_op_rows": max_rows,
        "max_op_packed_staging_bytes": max_rows * WINDOW_ROW_BYTES,
        "max_op_hbm_transfer_bytes": max_rows * PITCH_SECTORS * SECTOR,
        "max_op_unpacked_core_words": max_rows * HD // LANES,
        "mixed_128_window_512_ckv_payload_bytes": WINDOW_SLOTS * WINDOW_ROW_BYTES + 512 * COMPRESSED_ROW_BYTES,
        "mixed_128_window_512_ckv_hbm_bytes": WINDOW_SLOTS * PITCH_SECTORS * SECTOR + 512 * COMPRESSED_ROW_BYTES,
        "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    }
    return record


def main() -> None:
    record = build_record()
    out = ROOT / "results/rtl/v41x_packed_kv_mapping.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in record.items() if k != "sources"}, sort_keys=True))


if __name__ == "__main__":
    main()
