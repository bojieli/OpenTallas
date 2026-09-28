"""Window KV address proof at the full-shape die/core boundary."""

import json
from fractions import Fraction
from pathlib import Path

import pytest

from runtime.prefill.v41_aux_kv_rows import pack_window_row
from tools import v41x_packed_kv_mapping as M


def row(code=0x38, scale=127):
    return pack_window_row([code] * 512, [scale] * 16)


def test_all_core_aliases_inverse_and_word_scatter():
    rows = {slot: row(0x38 if slot % 2 else 0x3c, 127) for slot in range(128)}
    for slot in (0, 15, 16, 127):
        for dim in (0, 15, 16, 31, 32, 511):
            kt = M.core_scalar("KT", slot, dim)
            kr = M.core_scalar("KR", slot, dim)
            assert M.invert_core_scalar("KT", kt.scalar_offset) == (slot, dim)
            assert M.invert_core_scalar("KR", kr.scalar_offset) == (slot, dim)
            assert (kt.word_offset, kt.lane) == divmod(kt.scalar_offset, 16)
            assert (kr.word_offset, kr.lane) == divmod(kr.scalar_offset, 16)
            expected = Fraction(3, 2) if slot % 2 == 0 else Fraction(1)
            assert M.scatter_word(rows, "KT", kt.word_offset)[kt.lane] == expected
            assert M.scatter_word(rows, "KR", kr.word_offset)[kr.lane] == M.staging_word(rows[slot], "KR", slot, dim // 16)[dim % 16]
    assert M.core_scalar("KT", 128, 0).scalar_offset == M.core_scalar("KT", 0, 0).scalar_offset
    assert M.core_scalar("KR", M.MAX_CONTEXT - 1, 511).slot == 127


def test_full_shape_two_users_region_and_ring_eviction():
    base = 1 << 18
    count = 2 * M.USER_SECTORS
    for user in (0, 1):
        for pos in (0, 127, 128, M.MAX_CONTEXT - 1):
            for dim in (0, 31, 32, 511):
                a = M.packed_address(user, pos, dim, region_base_sector=base,
                                     region_sector_count=count, users=2)
                assert a.row_first_sector == base + user * M.USER_SECTORS + (pos % 128) * 17
                assert a.code_sector == a.row_first_sector + dim // 32
                assert a.code_byte == dim % 32
                assert a.scale_sector == a.row_first_sector + 16
                assert a.scale_byte == dim // 32
                assert base <= a.code_sector < a.scale_sector < base + count
    # A ring slot's address repeats after 128 positions. Absolute tags are
    # required to reject a stale read after the overwrite.
    assert M.packed_address(0, 0, 0, region_base_sector=base,
                            region_sector_count=count, users=2).row_first_sector == M.packed_address(
                                0, 128, 0, region_base_sector=base,
                                region_sector_count=count, users=2).row_first_sector
    assert M.packed_address(0, 127, 511, region_base_sector=base,
                            region_sector_count=count, users=2).scale_sector < M.packed_address(
                                1, 0, 0, region_base_sector=base,
                                region_sector_count=count, users=2).row_first_sector
    ring = M.TaggedWindowRing()
    ring.write(0, 0, row())
    ring.write(1, 0, row(0x3c))
    assert ring.read(0, 0) != ring.read(1, 0)
    ring.write(0, 128, row(0x30))
    with pytest.raises(ValueError, match="stale"):
        ring.read(0, 0)
    assert ring.read(0, 128) == row(0x30)
    assert ring.read(1, 0) == row(0x3c)


def test_region_fail_closed_and_capacity_accounting():
    kw = dict(region_base_sector=1 << 18, region_sector_count=M.USER_SECTORS, users=2)
    with pytest.raises(ValueError, match="reserve"):
        M.packed_address(1, 0, 0, **kw)
    kw["region_sector_count"] = 2 * M.USER_SECTORS
    for user, pos, dim in ((2, 0, 0), (0, M.MAX_CONTEXT, 0), (0, 0, 512)):
        with pytest.raises(ValueError):
            M.packed_address(user, pos, dim, **kw)
    with pytest.raises(ValueError, match="overflows"):
        M.packed_address(0, 0, 0, region_base_sector=(1 << 30) - 1,
                         region_sector_count=2 * M.USER_SECTORS, users=2)
    record = M.build_record()
    assert record["hbm_bytes_per_user_layer_die"] == 128 * 544 == 69_632
    assert record["max_op_packed_staging_bytes"] == 640 * 528 == 337_920
    assert record["max_op_hbm_transfer_bytes"] == 640 * 544 == 348_160
    assert record["max_op_unpacked_core_words"] == 20_480
    assert record["mixed_128_window_512_ckv_payload_bytes"] == 215_040
    assert record["mixed_128_window_512_ckv_hbm_bytes"] == 217_088
    # A full 1M context does not multiply the 128-position sliding window.
    assert 28 * 10 * record["hbm_bytes_per_user_layer_die"] == 19_496_960


def test_normalized_attention_row_classification_requires_ckv_ids():
    selected = tuple(9000 + i for i in range(512))
    assert M.attention_local_row(0, 0, selected) == ("window", 0)
    assert M.attention_local_row(0, 1, selected) == ("compressed", 9000)
    assert M.attention_local_row(M.MAX_CONTEXT - 1, 0, selected) == (
        "window", M.MAX_CONTEXT - 128)
    assert M.attention_local_row(M.MAX_CONTEXT - 1, 127, selected) == (
        "window", M.MAX_CONTEXT - 1)
    assert M.attention_local_row(M.MAX_CONTEXT - 1, 128, selected) == (
        "compressed", 9000)
    assert M.attention_local_row(M.MAX_CONTEXT - 1, 639, selected) == (
        "compressed", 9511)
    p = M.MAX_CONTEXT - 1
    assert M.attention_word_sources("KT", p, selected, 0) == tuple(
        ("window", p - 127 + lane, 0) for lane in range(16))
    assert M.attention_word_sources("KT", p, selected, 8 * 512) == tuple(
        ("compressed", 9000 + lane, 0) for lane in range(16))
    assert M.attention_word_sources("KR", p, selected, 128 * 32) == tuple(
        ("compressed", 9000, dim) for dim in range(16))
    assert M.attention_word_sources("KT", 0, (), 0)[0] == ("window", 0, 0)
    assert M.attention_word_sources("KT", 0, (), 0)[1:] == (None,) * 15
    with pytest.raises(ValueError, match="outside"):
        M.attention_local_row(0, 513, selected)


@pytest.mark.parametrize("order", [("code", "scale"), ("scale", "code")])
def test_atomic_block_read_after_write(order):
    store = M.AtomicBlockStore(row())
    store.begin(15, bytes([0x3c] * 32), 128)
    with pytest.raises(RuntimeError, match="wait"):
        store.read(15)
    getattr(store, "drain_" + order[0])(15)
    with pytest.raises(RuntimeError, match="wait"):
        store.read(15)
    getattr(store, "drain_" + order[1])(15)
    assert store.read(15)[480:512] == bytes([0x3c] * 32)
    assert store.read(15)[527] == 128
    assert store.read(0)[:480] == row()[:480]
    with pytest.raises(ValueError, match="outstanding"):
        store.begin(0, b"\0" * 32, 127)
        store.begin(0, b"\0" * 32, 127)


def test_record_source_pins_and_scope():
    record = json.loads((Path(__file__).resolve().parents[1] /
                         "results/rtl/v41x_packed_kv_mapping.json").read_text())
    assert record == M.build_record()
    assert "die integration" in record["scope"]
