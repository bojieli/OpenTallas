"""One-layer prefill window-row transfer for the reduced V4.1 HDC image.

This is not the released V4.1 compressed serving KV format. It serializes the
reduced golden's FP32 window rows and writes both KT and KR HDC views.
"""

from dataclasses import dataclass
import struct
import zlib

import numpy as np


PROFILE = "opentallas.deepseek_v41_reduced.hdc_window_fp32.v1"
MAGIC = b"OTV41W1\0"
HEADER = struct.Struct("<8sHH7I24x")  # 64 bytes
BLOCK = 16
LAYOUT_FP32_WINDOW = 1


@dataclass(frozen=True)
class WindowGeometry:
    layers: int
    max_positions: int
    head_dim: int
    kt_bases: tuple[int, ...]
    kr_bases: tuple[int, ...]
    image_elements: int

    def __post_init__(self):
        if self.layers <= 0 or self.max_positions <= 0 or self.max_positions % BLOCK or self.head_dim <= 0:
            raise ValueError("invalid reduced V4.1 window geometry")
        if len(self.kt_bases) != self.layers or len(self.kr_bases) != self.layers:
            raise ValueError("one KT and KR base required per layer")
        intervals = []
        for kt, kr in zip(self.kt_bases, self.kr_bases):
            n = self.max_positions * self.head_dim
            intervals.extend(((kt, kt + n), (kr, kr + n)))
        if min(start for start, _ in intervals) < 0 or max(end for _, end in intervals) > self.image_elements:
            raise ValueError("window regions exceed KV image")
        if any(a[0] < b[1] and b[0] < a[1] for i, a in enumerate(intervals) for b in intervals[i + 1:]):
            raise ValueError("window regions overlap")

    def kt_element(self, layer, pos, dim):
        return self.kt_bases[layer] + (pos // BLOCK) * self.head_dim * BLOCK + dim * BLOCK + pos % BLOCK

    def kr_element(self, layer, pos, dim):
        return self.kr_bases[layer] + pos * self.head_dim + dim


def packet_from_rows(rows, layer, first):
    """Encode a page-bounded [position, dimension] FP32 row slice."""
    if not isinstance(rows, np.ndarray) or rows.dtype != np.float32 or rows.ndim != 2:
        raise ValueError("rows must be a two-dimensional FP32 array")
    count, dim = rows.shape
    if not (0 <= layer <= 0xFFFFFFFF and 0 <= first <= 0xFFFFFFFF and 0 < count <= BLOCK
            and first // BLOCK == (first + count - 1) // BLOCK and dim > 0):
        raise ValueError("invalid page-bounded window span")
    payload = rows.astype("<f4", copy=False).tobytes(order="C")
    header = HEADER.pack(MAGIC, 1, LAYOUT_FP32_WINDOW, layer, first, count,
                         dim, len(payload), zlib.crc32(payload), 0)
    return header + payload + bytes(-len(payload) % 64)


def apply_packet(packet, image, geometry):
    """Validate a complete packet before writing both window views."""
    if len(packet) < HEADER.size or len(packet) % 64:
        raise ValueError("packet length is not a whole transfer beat")
    magic, version, layout, layer, first, count, dim, nbytes, crc, reserved = HEADER.unpack_from(packet)
    if magic != MAGIC or version != 1 or layout != LAYOUT_FP32_WINDOW or reserved:
        raise ValueError("unknown reduced V4.1 window packet")
    if not (0 <= layer < geometry.layers and 0 <= first and 0 < count <= BLOCK
            and first // BLOCK == (first + count - 1) // BLOCK
            and first + count <= geometry.max_positions and dim == geometry.head_dim
            and nbytes == count * dim * 4):
        raise ValueError("packet geometry mismatch")
    if len(packet) != HEADER.size + ((nbytes + 63) // 64) * 64:
        raise ValueError("packet payload length mismatch")
    payload = packet[HEADER.size:HEADER.size + nbytes]
    if any(packet[HEADER.size + nbytes:]) or zlib.crc32(payload) != crc:
        raise ValueError("packet padding or CRC mismatch")
    if not isinstance(image, np.ndarray) or image.dtype != np.float32 or image.shape != (geometry.image_elements,):
        raise ValueError("destination must be the flat FP32 reduced V4.1 KV image")
    values = np.frombuffer(payload, dtype="<f4").reshape(count, dim)
    for t in range(count):
        for d in range(dim):
            image[geometry.kt_element(layer, first + t, d)] = values[t, d]
            image[geometry.kr_element(layer, first + t, d)] = values[t, d]
    return count
