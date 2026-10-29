"""Opt-in IDXQ host packing contract; does not select a hardware master.

Existing six 256-bit operand rows stay at 0x800..0x805. A new collar must
explicitly permit operand bits 424..472 and append them to its packed face.
The production IDX256R master deliberately rejects these bits today.
"""
from dataclasses import dataclass

LEGACY_SEGMENTS = ((0, 44), (51, 373), (766, 342), (1450, 10))
LEGACY_MASK = sum(((1 << width) - 1) << base for base, width in LEGACY_SEGMENTS)
EXT_BASE, EXT_WIDTH, PACKED_WIDTH = 424, 49, 818
EXT_MASK = ((1 << EXT_WIDTH) - 1) << EXT_BASE
FIELDS = (("n_rows", 0, 5), ("row_pitch", 5, 12),
          ("weight_row_stride", 17, 16), ("query_row_stride", 33, 16))

@dataclass(frozen=True)
class Multirow:
    n_rows: int
    row_pitch: int
    weight_row_stride: int
    query_row_stride: int

    def encode(self):
        if not 1 <= self.n_rows <= 8:
            raise ValueError("IDXQ K8/link slots require 1..8 rows")
        if self.n_rows > 1 and self.row_pitch == 0:
            raise ValueError("multirow pitch must be positive")
        value = 0
        for name, base, width in FIELDS:
            field = getattr(self, name)
            if not 0 <= field < (1 << width):
                raise ValueError(f"{name} outside {width}-bit field")
            value |= field << base
        return value


def install(legacy_operand, controls):
    if legacy_operand < 0 or legacy_operand & ~LEGACY_MASK:
        raise ValueError("legacy operand has a reserved bit set")
    return legacy_operand | (controls.encode() << EXT_BASE)


def pack(operand, *, multirow=False):
    allowed = LEGACY_MASK | (EXT_MASK if multirow else 0)
    if operand < 0 or operand & ~allowed:
        raise ValueError("reserved operand bit; current collar rejects IDXQ extension")
    result, dest = 0, 0
    for base, width in LEGACY_SEGMENTS:
        result |= ((operand >> base) & ((1 << width) - 1)) << dest
        dest += width
    assert dest == 769
    if multirow:
        result |= ((operand >> EXT_BASE) & ((1 << EXT_WIDTH) - 1)) << dest
    return result


def operand_rows(operand):
    if not 0 <= operand < 1 << 1536:
        raise ValueError("six host operand rows required")
    return tuple((0x800 + row, (operand >> (256 * row)) & ((1 << 256) - 1))
                 for row in range(6))
