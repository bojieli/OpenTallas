"""Reduced V4.1 prefill window rows to both production HDC KV views."""

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_program_v41 as P
from runtime.prefill import v41_reduced_window_transfer as T


def _geometry():
    # Mirrors the Alloc order for two layers: KT0, KR0, KT1, KR1.
    n = P.TMAX * P.HD
    return T.WindowGeometry(2, P.TMAX, P.HD, (0, 2 * n), (n, 3 * n), 4 * n)


def test_one_layer_partial_tile_matches_production_kt_and_kr():
    g = _geometry()
    image = np.zeros(g.image_elements, dtype=np.float32)
    rows = np.arange(11 * P.HD, dtype=np.float32).reshape(11, P.HD) + 0.25
    packet = T.packet_from_rows(rows, layer=1, first=5)
    assert len(packet) % 64 == 0
    assert T.apply_packet(packet, image, g) == 11
    lay = SimpleNamespace()
    for pos in range(g.max_positions):
        for d in range(g.head_dim):
            kt = P.Layout.kt_elem(lay, g.kt_bases[1], pos, d)
            kr = g.kr_bases[1] + pos * g.head_dim + d
            assert kt == g.kt_element(1, pos, d)
            wanted = rows[pos - 5, d] if 5 <= pos < 16 else 0
            assert image[kt] == wanted and image[kr] == wanted
    assert not image[:2 * P.TMAX * P.HD].any()  # the other layer is untouched


def test_rejects_bad_packet_before_mutating_image():
    g = _geometry()
    image = np.zeros(g.image_elements, dtype=np.float32)
    packet = T.packet_from_rows(np.ones((2, P.HD), dtype=np.float32), 0, 13)
    bad = bytearray(packet)
    bad[65] ^= 1
    with pytest.raises(ValueError, match="CRC"):
        T.apply_packet(bad, image, g)
    with pytest.raises(ValueError, match="geometry"):
        T.apply_packet(packet, image, T.WindowGeometry(2, P.TMAX, 16, g.kt_bases, g.kr_bases, g.image_elements))
    with pytest.raises(ValueError, match="page-bounded"):
        T.packet_from_rows(np.ones((2, P.HD), dtype=np.float32), 0, 15)
    assert not image.any()
