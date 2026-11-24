from __future__ import annotations

import binascii
import sys
from pathlib import Path

import numpy as np

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "tools" / "qwen_code_rom"),
                str(Path(__file__).resolve().parents[1] / "tools")]

import bist_signatures as bs  # noqa: E402
import build  # noqa: E402
from mem_compiler.ecc import signature  # noqa: E402


def _write(path, mask):
    path.write_text("".join(row[::-1].tobytes().hex() + "\n" for row in mask))


def test_crc_matches_hardware_reference():
    bs.self_test()


def test_signature_is_of_programmed_vias(tmp_path):
    rng = np.random.default_rng(3)
    data = rng.integers(0, 256, size=(4096, 32), dtype=np.uint8)
    p = tmp_path / "m.viamap.hex"
    _write(p, build.physical(data))
    bits = bs.stored_words(p)
    assert np.array_equal(np.packbits(bits[:, :256], axis=1, bitorder="little"), data)
    assert not bits[:, 256:].any()
    words = [int.from_bytes(row.tobytes(), "little") for row in data]
    assert int(bs.crc(bits), 16) == signature(words, 266)
    flipped = build.physical(data)
    flipped[7, 3] ^= 1
    q = tmp_path / "f.viamap.hex"
    _write(q, flipped)
    assert bs.crc(bs.stored_words(q)) != bs.crc(bits)
