#!/usr/bin/env python3
"""Stream a released Engram rank's columns into dsfd_host RAW boot descriptors.

Input columns retain their released 264-byte rows. Only bytes 257..263 (padding)
change in the HBM image: the lookup engine's CRC-32, then three zero bytes.
Columns start on 32-byte atoms, exactly as ot_dsrom_engram_lookup.col_base.
Output records are one class byte followed by one little-endian 512-bit word;
the caller sends them against dsfd_host credits and waits for fenced completions.
This packer does not establish that the controller's boot routing is qualified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import BinaryIO, Iterable, Iterator

ROW_BYTES = 264
ATOM_BYTES = 32
MAX_SEGMENT_BYTES = 65535 * 64  # descriptor nb is 16 bits; no arbitrary build bound
# 10 is the existing RoPE boot class. 11 is the Engram class, whose local
# 30-bit atom spans 34.36 GB. Controller dispatch of this new class must pass
# its own exactness/closure gates before a generated stream is deployed.
BOOT_ATOM = 3 << 30
REGION_ATOMS = 1 << 30


def _crc_entry(byte: int) -> int:
    crc = byte << 24
    for _ in range(8):
        crc = ((crc << 1) & 0xffffffff) ^ (0x04c11db7 if crc >> 31 else 0)
    return crc


CRC_TABLE = tuple(_crc_entry(byte) for byte in range(256))


def crc32_msb(data: bytes) -> int:
    """RTL crc_byte: polynomial 04c11db7, init ffffffff, no final XOR."""
    crc = 0xffffffff
    for byte in data:
        crc = ((crc << 8) & 0xffffffff) ^ CRC_TABLE[(crc >> 24) ^ byte]
    return crc


def packed_row(row: bytes, rowstripe: bool = False) -> bytes:
    if len(row) != ROW_BYTES:
        raise ValueError("released row must contain exactly 264 bytes")
    return row[:257] + crc32_msb(row[:257]).to_bytes(4, "little") + bytes(27 if rowstripe else 3)


def column_bases(rows: Iterable[int], rowstripe: bool = False) -> list[int]:
    bases, offset = [], 0
    for count in rows:
        if count <= 0:
            raise ValueError("column row counts must be positive")
        bases.append(offset)
        offset += (count * (288 if rowstripe else ROW_BYTES) + ATOM_BYTES - 1) // ATOM_BYTES * ATOM_BYTES
    return bases


def column_chunks(stream: BinaryIO, rows: int, rowstripe: bool = False) -> Iterator[bytes]:
    """Bounded stream; the last chunk includes only the column's atom padding."""
    chunk = bytearray()
    for _ in range(rows):
        row = stream.read(ROW_BYTES)
        if len(row) != ROW_BYTES:
            raise ValueError("truncated released column")
        chunk.extend(packed_row(row, rowstripe))
        while len(chunk) >= MAX_SEGMENT_BYTES:
            yield bytes(chunk[:MAX_SEGMENT_BYTES])
            del chunk[:MAX_SEGMENT_BYTES]
    if stream.read(1):
        raise ValueError("released column has trailing data")
    chunk.extend(bytes((-len(chunk)) % ATOM_BYTES))
    if chunk:
        yield bytes(chunk)


def raw_descriptor(atom: int, nbytes: int, tag: int) -> int:
    if atom < 0 or atom >= REGION_ATOMS or nbytes <= 0 or nbytes % ATOM_BYTES:
        raise ValueError("invalid static-region RAW span")
    nsec = nbytes // ATOM_BYTES
    nb = (nbytes + 63) // 64
    if nsec >= 1 << 24 or nb >= 1 << 16 or atom + nsec >= REGION_ATOMS:
        raise ValueError("RAW descriptor fields overflow")
    return (1 << 7) | ((tag & 255) << 8) | ((BOOT_ATOM | atom) << 16) | (nsec << 144) | (nb << 240)


def host_records(columns: Iterable[tuple[BinaryIO, int]], rowstripe: bool = False) -> Iterator[tuple[int, bytes]]:
    atom, tag, fingerprint = 0, 0, 0
    for stream, rows in columns:
        for chunk in column_chunks(stream, rows, rowstripe):
            desc = raw_descriptor(atom, len(chunk), tag)
            yield 1, desc.to_bytes(64, "little")
            for start in range(0, len(chunk), 64):
                yield 2, chunk[start:start + 64].ljust(64, b"\0")
            for start in range(0, len(chunk), 32):
                fingerprint ^= atom + start // 32
                for word in range(start, start + 32, 4):
                    fingerprint ^= int.from_bytes(chunk[word:word + 4], "little")
            atom += len(chunk) // ATOM_BYTES
            tag += 1
    # BOOT_END CSR index2: expected count, fingerprint, explicit region class.
    marker = 2 | ((atom | (fingerprint << 32) | (3 << 64)) << 64)
    yield 0, marker.to_bytes(64, "little")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--columns", type=Path, nargs=6, required=True,
                    help="released local columns 6r..6r+5, each as contiguous 264-byte rows")
    ap.add_argument("--layer", type=int, choices=(1, 14), required=True)
    ap.add_argument("--rank", type=int, choices=range(4), required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--rowstripe", action="store_true", help="opt-in 288-byte whole-row PC layout; bind ROWSTRIPE=1 service and boot mapper")
    a = ap.parse_args()
    import hdc_v41_engram_shipped as shipped
    primes = shipped.shipped_tables().primes.reshape(2, 24)
    rows_per_column = list(map(int, primes[(0 if a.layer == 1 else 1), a.rank * 6:(a.rank + 1) * 6]))
    # Validate lengths before emitting anything; supplied counts must match the
    # released prime ledger for the chosen layer and rank at deployment.
    for path, rows in zip(a.columns, rows_per_column):
        if path.stat().st_size != rows * ROW_BYTES:
            raise ValueError(f"{path}: size differs from released row count")
    sources = [path.open("rb") for path in a.columns]
    digest, records = hashlib.sha256(), 0
    try:
        with a.output.open("xb") as out:
            for cls, data in host_records(zip(sources, rows_per_column), a.rowstripe):
                record = bytes([cls]) + data
                out.write(record)
                digest.update(record)
                records += 1
    finally:
        for source in sources:
            source.close()
    print(json.dumps(dict(records=records, sha256=digest.hexdigest(),
                          layer=a.layer, rank=a.rank,
                          column_byte_bases=column_bases(rows_per_column, a.rowstripe),
                          rowstripe=a.rowstripe, stored_row_bytes=288 if a.rowstripe else 264,
                          requires="Engram class 11 dispatch, SW/SE atom striping, fenced completions")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
