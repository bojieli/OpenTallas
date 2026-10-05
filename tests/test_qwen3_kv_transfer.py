"""BF16 NHD GPU page -> transfer beats -> current FP32 HDC image."""

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from runtime.prefill import qwen3_kv_transfer as T
import hdc_program as P


def test_paged_transfer_matches_existing_hdc_addressing_and_preserves_partial_tile():
    geom = T.Geometry(layers=2, heads=2, head_dim=16, max_positions=P.TMAX)
    assert geom.max_positions == 64 and P.W == 16
    production_layout = SimpleNamespace(KV=geom.heads, HD=geom.head_dim,
                                        TW=geom.max_positions // P.W, kv_v0=geom.k_elements)
    # The physical pool is deliberately scrambled; page 0 is not logical page 0.
    rng = np.random.default_rng(9181)
    pages = rng.integers(0, 65536, (2, 2, 5, 16, 4, 16), dtype=np.uint16)
    table = np.array([3, 1, 4, 0], dtype=np.int32)
    image = np.zeros(geom.image_elements, dtype=np.float32)
    before = image.copy()
    transferred = T.transfer_span(pages, table, image, geom, 7, 23, head_start=1)
    # Two layers, each 9 + 14 positions, split at a page boundary.
    expected_wire = 2 * sum(64 + ((2 * n * 2 * 16 * 2 + 63) // 64) * 64 for n in (9, 14))
    assert transferred == expected_wire
    expected = before.copy()
    for layer in range(2):
        for pos in range(7, 30):
            phys = table[pos // 16]
            for head in range(2):
                for d in range(16):
                    for kind, address in ((0, geom.k_element(layer, head, pos, d)),
                                          (1, geom.v_element(layer, head, pos, d))):
                        raw = pages[layer, kind, phys, pos % 16, head + 1, d]
                        expected[address] = np.array([np.uint32(raw) << 16], dtype=np.uint32).view(np.float32)[0]
                    # Check that the production Layout uses precisely these FP32 element addresses.
                    assert address == P.Layout.v_elem(production_layout, layer, head, pos, d)
                    assert geom.k_element(layer, head, pos, d) == P.Layout.k_elem(production_layout, layer, head, pos, d)
    np.testing.assert_array_equal(image.view(np.uint32), expected.view(np.uint32))
    # An appended prefix starts mid-tile and must leave resident lanes untouched.
    saved = image.copy()
    T.transfer_span(pages, table, image, geom, 30, 2, head_start=1)
    for layer in range(2):
        for pos in range(7, 30):
            for head in range(2):
                for d in range(16):
                    assert image.view(np.uint32)[geom.k_element(layer, head, pos, d)] == saved.view(np.uint32)[geom.k_element(layer, head, pos, d)]


def test_packet_rejects_corruption_and_geometry_mismatch_without_writes():
    pages = np.arange(2 * 2 * 1 * 16 * 2 * 16, dtype=np.uint16).reshape(2, 2, 1, 16, 2, 16)
    geom = T.Geometry(2, 2, 16, 64)
    packet = T.packet_from_pages(pages, [0], 0, 3, 4)
    assert len(packet) % 64 == 0
    image = np.zeros(geom.image_elements, dtype=np.float32)
    bad = bytearray(packet)
    bad[64] ^= 1
    with pytest.raises(ValueError, match="CRC"):
        T.apply_packet_fp32(bad, image, geom)
    assert not image.any()
    with pytest.raises(ValueError, match="geometry"):
        T.apply_packet_fp32(packet, image, T.Geometry(2, 1, 16, 64))
    assert not image.any()
    with pytest.raises(ValueError, match="unknown"):
        T.apply_packet_fp32(b"BADMAGIC" + packet[8:], image, geom)
    assert not image.any()
    with pytest.raises(ValueError, match="span"):
        T.packet_from_pages(pages, [0], 0, 15, 2)
