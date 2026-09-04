"""Authenticated out-of-line request-symbol records for ABI 3.0.

The 128-byte submission record already freezes ``request_descriptor_id`` but
cannot carry the runtime-symbol map itself.  A request descriptor is therefore
a separately registered, bounded-lifetime record.  It binds one descriptor ID
to one deployment, session generation and transaction, and carries ordered
``(symbol_id, value)`` entries.  The record has both a SHA-256 content binding
and the ABI's usual CRC32C transport check.

This is deliberately separate from the deployment descriptor table.  Request
descriptors are mutable queue-side objects, are consumed exactly once, and may
never become program operands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .constants import (
    ABI_MAJOR,
    ABI_MINOR,
    DESCRIPTOR_ALIGNMENT,
    REQUEST_DESCRIPTOR_HEADER_BYTES,
    REQUEST_DESCRIPTOR_MAGIC,
    REQUEST_SYMBOL_ENTRY_BYTES,
)
from .crc import record_crc, sha256
from .layout import Field, Layout, RecordError


REQUEST_DESCRIPTOR_TYPE_MAJOR = 1
REQUEST_DESCRIPTOR_TYPE_MINOR = 0


REQUEST_DESCRIPTOR_HEADER = Layout(
    "request_descriptor_header",
    REQUEST_DESCRIPTOR_HEADER_BYTES,
    [
        Field("magic", 0, 4, "magic", REQUEST_DESCRIPTOR_MAGIC),
        Field("abi_major", 4, 1),
        Field("abi_minor", 5, 1),
        Field("type_major", 6, 1),
        Field("type_minor", 7, 1),
        Field("header_bytes", 8, 2),
        Field("entry_bytes", 10, 2),
        Field("total_bytes", 12, 4),
        Field("request_descriptor_id", 16, 4),
        Field("symbol_count", 20, 4),
        Field("deployment_id", 24, 4),
        Field("deployment_generation", 28, 4),
        Field("session_id", 32, 4),
        Field("session_generation", 36, 4),
        Field("transaction_id", 40, 8),
        Field("payload_bytes", 48, 4),
        Field("flags", 52, 4),
        Field("content_digest", 56, 32, "bytes"),
        Field("reserved", 88, 36, "reserved"),
        Field("record_crc", 124, 4),
    ],
    crc_field="record_crc",
)


REQUEST_SYMBOL_ENTRY = Layout(
    "request_symbol_entry",
    REQUEST_SYMBOL_ENTRY_BYTES,
    [
        Field("symbol_id", 0, 4),
        Field("reserved", 4, 4, "reserved"),
        Field("value", 8, 8),
    ],
)


def _content_digest(record: bytes) -> bytes:
    """SHA-256 of the complete record with digest and CRC fields zero."""

    material = bytearray(record)
    digest_field = REQUEST_DESCRIPTOR_HEADER.field("content_digest")
    material[digest_field.offset : digest_field.end] = bytes(digest_field.size)
    crc_field = REQUEST_DESCRIPTOR_HEADER.field("record_crc")
    material[crc_field.offset : crc_field.end] = bytes(crc_field.size)
    return sha256(bytes(material))


@dataclass(frozen=True, slots=True)
class RequestSymbolEntry:
    """One unsigned 64-bit binding for one frozen runtime-symbol ID."""

    symbol_id: int
    value: int

    def encode(self) -> bytes:
        return bytes(
            REQUEST_SYMBOL_ENTRY.encode(
                {"symbol_id": self.symbol_id, "value": self.value}
            )
        )

    @classmethod
    def decode(cls, record: bytes) -> "RequestSymbolEntry":
        return cls(**REQUEST_SYMBOL_ENTRY.decode(record))


@dataclass(frozen=True, slots=True)
class RequestSymbolDescriptor:
    """One immutable symbol record owned by exactly one ABI transaction."""

    request_descriptor_id: int
    deployment_id: int
    deployment_generation: int
    session_id: int
    session_generation: int
    transaction_id: int
    entries: tuple[RequestSymbolEntry, ...]
    type_major: int = REQUEST_DESCRIPTOR_TYPE_MAJOR
    type_minor: int = REQUEST_DESCRIPTOR_TYPE_MINOR
    flags: int = 0

    @classmethod
    def from_symbols(
        cls,
        *,
        request_descriptor_id: int,
        deployment_id: int,
        deployment_generation: int,
        session_id: int,
        session_generation: int,
        transaction_id: int,
        symbols: Mapping[int, int],
    ) -> "RequestSymbolDescriptor":
        """Build the deterministic canonical ordering used by the driver."""

        return cls(
            request_descriptor_id=request_descriptor_id,
            deployment_id=deployment_id,
            deployment_generation=deployment_generation,
            session_id=session_id,
            session_generation=session_generation,
            transaction_id=transaction_id,
            entries=tuple(
                RequestSymbolEntry(int(symbol_id), int(value))
                for symbol_id, value in sorted(symbols.items())
            ),
        )

    def encode(self) -> bytes:
        if self.type_major != REQUEST_DESCRIPTOR_TYPE_MAJOR:
            raise RecordError(
                f"unsupported request descriptor type_major {self.type_major}"
            )
        if self.type_minor > REQUEST_DESCRIPTOR_TYPE_MINOR:
            raise RecordError(
                f"request descriptor requires type_minor {self.type_minor}"
            )
        if self.flags:
            raise RecordError("request descriptor flags are reserved and must be zero")
        payload = b"".join(entry.encode() for entry in self.entries)
        total = REQUEST_DESCRIPTOR_HEADER_BYTES + len(payload)
        total = -(-total // DESCRIPTOR_ALIGNMENT) * DESCRIPTOR_ALIGNMENT
        record = bytearray(total)
        record[:REQUEST_DESCRIPTOR_HEADER_BYTES] = REQUEST_DESCRIPTOR_HEADER.encode(
            {
                "abi_major": ABI_MAJOR,
                "abi_minor": ABI_MINOR,
                "type_major": self.type_major,
                "type_minor": self.type_minor,
                "header_bytes": REQUEST_DESCRIPTOR_HEADER_BYTES,
                "entry_bytes": REQUEST_SYMBOL_ENTRY_BYTES,
                "total_bytes": total,
                "request_descriptor_id": self.request_descriptor_id,
                "symbol_count": len(self.entries),
                "deployment_id": self.deployment_id,
                "deployment_generation": self.deployment_generation,
                "session_id": self.session_id,
                "session_generation": self.session_generation,
                "transaction_id": self.transaction_id,
                "payload_bytes": len(payload),
                "flags": self.flags,
                "content_digest": bytes(32),
                "record_crc": 0,
            }
        )
        payload_end = REQUEST_DESCRIPTOR_HEADER_BYTES + len(payload)
        record[REQUEST_DESCRIPTOR_HEADER_BYTES:payload_end] = payload
        digest_field = REQUEST_DESCRIPTOR_HEADER.field("content_digest")
        record[digest_field.offset : digest_field.end] = _content_digest(record)
        crc_field = REQUEST_DESCRIPTOR_HEADER.field("record_crc")
        crc = record_crc(bytes(record), crc_field.offset)
        record[crc_field.offset : crc_field.end] = crc.to_bytes(4, "little")
        return bytes(record)

    @classmethod
    def decode(cls, record: bytes) -> "RequestSymbolDescriptor":
        if len(record) < REQUEST_DESCRIPTOR_HEADER_BYTES:
            raise RecordError("request descriptor is shorter than its header")
        if len(record) % DESCRIPTOR_ALIGNMENT:
            raise RecordError("request descriptor size is not a multiple of 64")
        values = REQUEST_DESCRIPTOR_HEADER.decode(
            record[:REQUEST_DESCRIPTOR_HEADER_BYTES]
        )
        if values["abi_major"] != ABI_MAJOR:
            raise RecordError("unsupported request descriptor ABI major version")
        if values["abi_minor"] > ABI_MINOR:
            raise RecordError("unsupported request descriptor ABI minor version")
        if values["type_major"] != REQUEST_DESCRIPTOR_TYPE_MAJOR:
            raise RecordError(
                f"unsupported request descriptor type_major {values['type_major']}"
            )
        if values["type_minor"] > REQUEST_DESCRIPTOR_TYPE_MINOR:
            raise RecordError(
                f"request descriptor requires type_minor {values['type_minor']}"
            )
        if values["header_bytes"] != REQUEST_DESCRIPTOR_HEADER_BYTES:
            raise RecordError("request descriptor header_bytes is not 128")
        if values["entry_bytes"] != REQUEST_SYMBOL_ENTRY_BYTES:
            raise RecordError("request descriptor entry_bytes is not 16")
        if values["total_bytes"] != len(record):
            raise RecordError(
                f"request descriptor total_bytes {values['total_bytes']} does not "
                f"match record length {len(record)}"
            )
        if values["flags"]:
            raise RecordError("request descriptor flags are reserved")
        expected_crc = record_crc(record, REQUEST_DESCRIPTOR_HEADER.crc_offset())
        if values["record_crc"] != expected_crc:
            raise RecordError("request descriptor CRC32C mismatch")
        if values["content_digest"] != _content_digest(record):
            raise RecordError("request descriptor SHA-256 mismatch")
        expected_payload = values["symbol_count"] * REQUEST_SYMBOL_ENTRY_BYTES
        if values["payload_bytes"] != expected_payload:
            raise RecordError(
                f"request descriptor payload_bytes {values['payload_bytes']} does "
                f"not match {values['symbol_count']} symbol entries"
            )
        payload_end = REQUEST_DESCRIPTOR_HEADER_BYTES + expected_payload
        if payload_end > len(record):
            raise RecordError("request descriptor payload runs past the record")
        if any(record[payload_end:]):
            raise RecordError("request descriptor padding is not zero")
        entries = tuple(
            RequestSymbolEntry.decode(record[offset : offset + REQUEST_SYMBOL_ENTRY_BYTES])
            for offset in range(
                REQUEST_DESCRIPTOR_HEADER_BYTES,
                payload_end,
                REQUEST_SYMBOL_ENTRY_BYTES,
            )
        )
        return cls(
            request_descriptor_id=values["request_descriptor_id"],
            deployment_id=values["deployment_id"],
            deployment_generation=values["deployment_generation"],
            session_id=values["session_id"],
            session_generation=values["session_generation"],
            transaction_id=values["transaction_id"],
            entries=entries,
            type_major=values["type_major"],
            type_minor=values["type_minor"],
            flags=values["flags"],
        )

    def symbol_map(self) -> dict[int, int]:
        """Return bindings, refusing ambiguity rather than overwriting it."""

        symbols: dict[int, int] = {}
        for entry in self.entries:
            if entry.symbol_id in symbols:
                raise RecordError(
                    f"request descriptor repeats symbol ID {entry.symbol_id}"
                )
            symbols[entry.symbol_id] = entry.value
        return symbols


def entries_from_pairs(
    pairs: Sequence[tuple[int, int]],
) -> tuple[RequestSymbolEntry, ...]:
    """Test/tool helper that preserves order and duplicate IDs deliberately."""

    return tuple(RequestSymbolEntry(int(symbol), int(value)) for symbol, value in pairs)


__all__ = [
    "REQUEST_DESCRIPTOR_HEADER",
    "REQUEST_DESCRIPTOR_TYPE_MAJOR",
    "REQUEST_DESCRIPTOR_TYPE_MINOR",
    "REQUEST_SYMBOL_ENTRY",
    "RequestSymbolDescriptor",
    "RequestSymbolEntry",
    "entries_from_pairs",
]
