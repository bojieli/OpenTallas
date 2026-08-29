"""CRC32C (Castagnoli) and SHA-256 helpers for the ABI 3.0 wire format.

Normative rules (TA-ABI3-WIRE-1 section 1):

- record CRC is reflected CRC32C with polynomial ``0x82f63b78``, initial state
  ``0xffffffff`` and final XOR ``0xffffffff``;
- a CRC field is treated as zero while its own record CRC is calculated; and
- SHA-256 digests are 32 raw bytes in binary records and 64 lowercase hex
  characters in canonical JSON.
"""

from __future__ import annotations

import hashlib
from typing import Iterable

CRC32C_POLY_REFLECTED = 0x82F63B78
"""Reflected Castagnoli polynomial frozen by TA-ABI3-WIRE-1."""


def _build_table() -> tuple[int, ...]:
    table = []
    for index in range(256):
        value = index
        for _ in range(8):
            if value & 1:
                value = (value >> 1) ^ CRC32C_POLY_REFLECTED
            else:
                value >>= 1
        table.append(value)
    return tuple(table)


_TABLE = _build_table()


def crc32c(data: bytes, state: int = 0xFFFFFFFF) -> int:
    """Return the CRC32C of ``data``.

    ``state`` is the running (pre-final-XOR) state so that a CRC can be
    computed over discontiguous spans without materialising a copy.
    """
    for byte in data:
        state = _TABLE[(state ^ byte) & 0xFF] ^ (state >> 8)
    return state ^ 0xFFFFFFFF


def crc32c_spans(spans: Iterable[bytes]) -> int:
    """Return the CRC32C over the concatenation of ``spans``."""
    state = 0xFFFFFFFF
    for span in spans:
        for byte in span:
            state = _TABLE[(state ^ byte) & 0xFF] ^ (state >> 8)
    return state ^ 0xFFFFFFFF


def record_crc(record: bytes, crc_offset: int, crc_bytes: int = 4) -> int:
    """CRC of ``record`` with its own CRC field treated as zero.

    The rule is applied by checksumming the bytes before the field, then four
    zero bytes, then the bytes after the field.  For records whose CRC field is
    the final field this is identical to checksumming the prefix followed by
    zeros, but the general form is used so one helper serves every record.
    """
    if crc_offset < 0 or crc_offset + crc_bytes > len(record):
        raise ValueError("CRC field lies outside the record")
    return crc32c_spans(
        (
            record[:crc_offset],
            b"\x00" * crc_bytes,
            record[crc_offset + crc_bytes :],
        )
    )


def sha256(data: bytes) -> bytes:
    """Return the raw 32-byte SHA-256 digest of ``data``."""
    return hashlib.sha256(data).digest()


def sha256_hex(data: bytes) -> str:
    """Return the 64-character lowercase hexadecimal SHA-256 digest."""
    return hashlib.sha256(data).hexdigest()


def sha256_spans(spans: Iterable[bytes]) -> bytes:
    """Return the raw SHA-256 digest over the concatenation of ``spans``."""
    digest = hashlib.sha256()
    for span in spans:
        digest.update(span)
    return digest.digest()
