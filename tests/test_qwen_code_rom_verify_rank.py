from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("numpy")
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "tools" / "qwen_code_rom")]

import build  # noqa: E402
import verify_rank as vr  # noqa: E402


def _write(path, mask):
    path.write_text("".join(row[::-1].tobytes().hex() + "\n" for row in mask))


def test_decode_inverts_physical_bitline_order(tmp_path):
    rng = np.random.default_rng(7)
    data = rng.integers(0, 256, size=(4096, 32), dtype=np.uint8)
    p = tmp_path / "m.viamap.hex"
    _write(p, build.physical(data))
    assert np.array_equal(vr.decode_mask(p), data)


def test_decode_detects_flipped_via_and_dead_bitline(tmp_path):
    rng = np.random.default_rng(8)
    data = rng.integers(0, 256, size=(4096, 32), dtype=np.uint8)
    mask = build.physical(data)
    flipped = mask.copy()
    flipped[100, 17] ^= 0x04
    p = tmp_path / "f.viamap.hex"
    _write(p, flipped)
    assert not np.array_equal(vr.decode_mask(p), data)
    dead = mask.copy()
    dead[3, 260] = 1
    q = tmp_path / "d.viamap.hex"
    _write(q, dead)
    with pytest.raises(ValueError, match="dead bitlines"):
        vr.decode_mask(q)
