"""Declarative fixed-record layout engine for ABI 3.0 binary records.

Every ABI 3.0 record is a fixed-size, naturally aligned, little-endian byte
string with reserved spans that must be zero.  Rather than hand-writing
``struct.pack`` calls per record -- which is where wire-format drift starts --
each record declares a :class:`Layout`: an ordered field table with explicit
offsets.  The layout itself validates that

* fields do not overlap and do not run past the record size;
* every byte of the record is covered by exactly one field (including explicit
  reserved fields), so a silently unencoded gap is impossible; and
* integer fields are naturally aligned to their own width.

Encoding rejects out-of-range values, and decoding rejects nonzero reserved
bytes, so a corrupted or hostile record fails closed before any use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Iterable, Mapping, Sequence

BYTE_ORDER: Final = "little"


class LayoutError(ValueError):
    """Raised when a layout definition is internally inconsistent."""


class RecordError(ValueError):
    """Raised when a record fails encode-time or decode-time validation."""


@dataclass(frozen=True, slots=True)
class Field:
    """One field of a fixed record.

    ``kind`` is one of ``"uint"``, ``"bytes"``, ``"magic"`` or ``"reserved"``.
    ``uint`` fields are unsigned little-endian integers of ``size`` bytes.
    ``bytes`` fields are opaque fixed-width byte strings (digests, keys).
    ``magic`` fields are byte strings with one legal value.
    ``reserved`` fields must be zero in every conforming record.
    """

    name: str
    offset: int
    size: int
    kind: str = "uint"
    constant: bytes | None = None

    def __post_init__(self) -> None:
        if self.size <= 0:
            raise LayoutError(f"field {self.name!r} has non-positive size")
        if self.offset < 0:
            raise LayoutError(f"field {self.name!r} has negative offset")
        if self.kind not in {"uint", "bytes", "magic", "reserved"}:
            raise LayoutError(f"field {self.name!r} has unknown kind {self.kind!r}")
        if self.kind == "magic":
            if self.constant is None or len(self.constant) != self.size:
                raise LayoutError(f"magic field {self.name!r} needs a sized constant")
        if self.kind == "uint":
            if self.size not in (1, 2, 4, 8):
                raise LayoutError(f"uint field {self.name!r} has width {self.size}")
            if self.offset % self.size:
                raise LayoutError(
                    f"uint field {self.name!r} at offset {self.offset} is not "
                    f"naturally aligned to {self.size} bytes"
                )

    @property
    def end(self) -> int:
        return self.offset + self.size

    @property
    def max_value(self) -> int:
        return (1 << (self.size * 8)) - 1


class Layout:
    """An ordered, gap-free field table describing one fixed-size record."""

    __slots__ = ("name", "size", "fields", "_by_name", "crc_field")

    def __init__(
        self,
        name: str,
        size: int,
        fields: Sequence[Field],
        crc_field: str | None = None,
    ) -> None:
        self.name = name
        self.size = size
        self.fields = tuple(sorted(fields, key=lambda f: f.offset))
        self._by_name = {field.name: field for field in self.fields}
        if len(self._by_name) != len(self.fields):
            raise LayoutError(f"{name}: duplicate field name")
        cursor = 0
        for field in self.fields:
            if field.offset != cursor:
                raise LayoutError(
                    f"{name}: field {field.name!r} starts at {field.offset}, "
                    f"expected {cursor} (overlap or uncovered gap)"
                )
            cursor = field.end
        if cursor != size:
            raise LayoutError(
                f"{name}: fields cover {cursor} bytes, record size is {size}"
            )
        if crc_field is not None and crc_field not in self._by_name:
            raise LayoutError(f"{name}: crc field {crc_field!r} is not declared")
        self.crc_field = crc_field

    def field(self, name: str) -> Field:
        try:
            return self._by_name[name]
        except KeyError:
            raise LayoutError(f"{self.name}: no field {name!r}") from None

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(
            f.name for f in self.fields if f.kind not in {"reserved", "magic"}
        )

    # -- encoding ---------------------------------------------------------
    def encode(self, values: Mapping[str, Any]) -> bytearray:
        """Encode ``values`` into a ``bytearray`` of exactly ``self.size``."""
        unknown = set(values) - set(self._by_name)
        if unknown:
            raise RecordError(f"{self.name}: unknown field(s) {sorted(unknown)}")
        record = bytearray(self.size)
        for field in self.fields:
            if field.kind == "reserved":
                if values.get(field.name):
                    raise RecordError(
                        f"{self.name}.{field.name} is reserved and must be zero"
                    )
                continue
            if field.kind == "magic":
                assert field.constant is not None
                record[field.offset : field.end] = field.constant
                continue
            if field.name not in values:
                raise RecordError(f"{self.name}: missing field {field.name!r}")
            value = values[field.name]
            if field.kind == "uint":
                number = int(value)
                if not 0 <= number <= field.max_value:
                    raise RecordError(
                        f"{self.name}.{field.name}={number} does not fit in "
                        f"{field.size} unsigned bytes"
                    )
                record[field.offset : field.end] = number.to_bytes(
                    field.size, BYTE_ORDER
                )
            else:  # bytes
                blob = bytes(value)
                if len(blob) != field.size:
                    raise RecordError(
                        f"{self.name}.{field.name} must be exactly "
                        f"{field.size} bytes, got {len(blob)}"
                    )
                record[field.offset : field.end] = blob
        return record

    # -- decoding ---------------------------------------------------------
    def decode(self, record: bytes, *, check_reserved: bool = True) -> dict[str, Any]:
        """Decode ``record``, failing closed on size, magic and reserved bytes."""
        if len(record) != self.size:
            raise RecordError(
                f"{self.name}: record is {len(record)} bytes, expected {self.size}"
            )
        out: dict[str, Any] = {}
        for field in self.fields:
            span = record[field.offset : field.end]
            if field.kind == "reserved":
                if check_reserved and any(span):
                    raise RecordError(
                        f"{self.name}.{field.name}: reserved bytes are nonzero"
                    )
                continue
            if field.kind == "magic":
                if span != field.constant:
                    raise RecordError(
                        f"{self.name}.{field.name}: bad magic {span!r}"
                    )
                continue
            if field.kind == "uint":
                out[field.name] = int.from_bytes(span, BYTE_ORDER)
            else:
                out[field.name] = bytes(span)
        return out

    # -- CRC helpers ------------------------------------------------------
    def crc_offset(self) -> int:
        if self.crc_field is None:
            raise LayoutError(f"{self.name}: no CRC field declared")
        return self.field(self.crc_field).offset


def reserved_span(offset: int, size: int, index: int = 0) -> Field:
    """Convenience constructor for a reserved-zero span."""
    return Field(f"reserved_{index}" if index else "reserved", offset, size, "reserved")


def check_zero(values: Mapping[str, Any], names: Iterable[str], context: str) -> None:
    """Raise unless every named value is zero (used for conditional reserves)."""
    for name in names:
        if values.get(name):
            raise RecordError(f"{context}: {name} must be zero")
