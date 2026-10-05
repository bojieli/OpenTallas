"""Versioned Qwen3 BF16 paged-KV transfer into the current FP32 HDC image.

The packet is a software/RDMA staging record, not the unfinished ingest RTL's
256-bit descriptor. The decoder consumes validated whole records atomically.
"""

from dataclasses import dataclass
import struct
import zlib

import numpy as np


PROFILE = "opentallas.qwen3.hdc_kv_bf16_nhd_to_fp32.v1"
MAGIC = b"OTQKV1\0\0"
HEADER = struct.Struct("<8sHH9I16x")  # exactly one 64-byte transfer beat
BLOCK = 16
LAYOUT_NHD_BF16 = 1


@dataclass(frozen=True)
class Geometry:
    layers: int
    heads: int  # heads local to the destination die
    head_dim: int
    max_positions: int

    def __post_init__(self):
        if min(self.layers, self.heads, self.head_dim, self.max_positions) <= 0:
            raise ValueError("all geometry extents must be positive")
        if self.max_positions % BLOCK:
            raise ValueError("max_positions must be a multiple of 16")

    @property
    def k_elements(self):
        return self.layers * self.heads * self.max_positions * self.head_dim

    @property
    def image_elements(self):
        return 2 * self.k_elements

    def k_element(self, layer, head, position, dim):
        return ((layer * self.heads + head) * (self.max_positions // BLOCK)
                + position // BLOCK) * self.head_dim * BLOCK + dim * BLOCK + position % BLOCK

    def v_element(self, layer, head, position, dim):
        return self.k_elements + ((layer * self.heads + head) * self.max_positions + position) * self.head_dim + dim


def _check_uint16_pages(pages):
    if not isinstance(pages, np.ndarray) or pages.dtype != np.dtype("<u2") or pages.ndim != 6:
        raise ValueError("pages must be a uint16 array [layer, K/V, physical_block, 16, head, dim]")
    if pages.shape[1] != 2 or pages.shape[3] != BLOCK:
        raise ValueError("pages must have K/V axis 2 and block size 16")


def packet_from_pages(pages, block_table, layer, first_position, count, head_start=0, head_count=None):
    """Extract a logical token span from vLLM-style physical BF16 pages.

    ``block_table[i]`` is the physical page of logical positions 16*i..16*i+15.
    The payload is K then V, each [position, local_head, dimension] in little
    endian BF16; the final transfer beat is zero padded and excluded from CRC.
    """
    _check_uint16_pages(pages)
    table = np.asarray(block_table)
    if table.ndim != 1 or not np.issubdtype(table.dtype, np.integer):
        raise ValueError("block_table must be a one-dimensional integer array")
    head_count = pages.shape[4] - head_start if head_count is None else head_count
    if not (0 <= layer < pages.shape[0] and 0 <= first_position and 0 < count <= BLOCK
            and first_position // BLOCK == (first_position + count - 1) // BLOCK
            and first_position + count <= len(table) * BLOCK
            and 0 <= head_start < pages.shape[4] and 0 < head_count <= pages.shape[4] - head_start):
        raise ValueError("invalid layer, token span, or head slice")
    block_id = int(table[first_position // BLOCK])
    if not 0 <= block_id < pages.shape[2]:
        raise ValueError("block table points outside physical KV pool")
    offset = first_position % BLOCK
    view = pages[layer, :, block_id, offset:offset + count, head_start:head_start + head_count, :]
    payload = view.astype("<u2", copy=False).tobytes(order="C")
    header = HEADER.pack(MAGIC, 1, LAYOUT_NHD_BF16, layer, first_position, count,
                         pages.shape[4], head_start, head_count, pages.shape[5],
                         len(payload), zlib.crc32(payload))
    return header + payload + bytes(-len(payload) % 64)


def apply_packet_fp32(packet, image, geometry, expected_head_start=0):
    """Validate a record, then place its BF16 values into HDC's FP32 K/V image."""
    if len(packet) < HEADER.size or len(packet) % 64:
        raise ValueError("packet length is not a whole transfer beat")
    (magic, version, layout, layer, first, count, global_heads, head_start,
     head_count, dim, payload_len, crc) = HEADER.unpack_from(packet)
    if magic != MAGIC or version != 1 or layout != LAYOUT_NHD_BF16:
        raise ValueError("unknown Qwen3 KV transfer format")
    if not (0 <= layer < geometry.layers and 0 <= first and 0 < count <= BLOCK
            and first // BLOCK == (first + count - 1) // BLOCK
            and first + count <= geometry.max_positions and head_start == expected_head_start
            and head_count == geometry.heads and global_heads >= head_start + head_count
            and dim == geometry.head_dim and payload_len == 2 * count * head_count * dim * 2):
        raise ValueError("packet geometry does not match destination")
    if len(packet) != HEADER.size + ((payload_len + 63) // 64) * 64:
        raise ValueError("packet payload length mismatch")
    payload = packet[HEADER.size:HEADER.size + payload_len]
    if any(packet[HEADER.size + payload_len:]) or zlib.crc32(payload) != crc:
        raise ValueError("packet padding or CRC mismatch")
    if not isinstance(image, np.ndarray) or image.dtype != np.float32 or image.shape != (geometry.image_elements,):
        raise ValueError("destination must be the geometry's flat FP32 HDC image")
    bf16 = np.frombuffer(payload, dtype="<u2").astype(np.uint32).reshape(2, count, head_count, dim)
    values = (bf16 << 16).view(np.float32)
    for t in range(count):
        for h in range(head_count):
            for d in range(dim):
                image[geometry.k_element(layer, h, first + t, d)] = values[0, t, h, d]
                image[geometry.v_element(layer, h, first + t, d)] = values[1, t, h, d]
    return count


def transfer_span(pages, block_table, image, geometry, first, count, head_start=0):
    """Transfer a logical span as page-bounded records; return on-wire bytes."""
    _check_uint16_pages(pages)
    if count < 0 or first < 0 or first + count > geometry.max_positions:
        raise ValueError("invalid transfer span")
    wire_bytes = 0
    for layer in range(geometry.layers):
        pos = first
        while pos < first + count:
            n = min(first + count - pos, BLOCK - pos % BLOCK)
            record = packet_from_pages(pages, block_table, layer, pos, n, head_start, geometry.heads)
            apply_packet_fp32(record, image, geometry, head_start)
            wire_bytes += len(record)
            pos += n
    return wire_bytes
