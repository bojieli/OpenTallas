import pytest
import sys
from pathlib import Path

from tools.qwen_kv_bank_prototype import BankedTail, SectorAssembly, k_element, v_element

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from hdc_program import Layout, TMAX


def test_address_mapping_matches_shipped_program_layout():
    # Call the real layout methods; no checkpoint or generated model is needed.
    layout = object.__new__(Layout)
    layout.KV, layout.TW, layout.HD, layout.kv_v0 = 8, TMAX // 16, 128, 4096
    for layer, head, position, dimension in ((0, 0, 0, 0), (0, 7, 17, 15),
                                             (2, 3, 31, 127), (35, 7, 63, 64)):
        assert k_element(layer, head, position, dimension, kv_heads=8,
                         position_tiles=TMAX // 16) == layout.k_elem(layer, head, position, dimension)
        assert v_element(layer, head, position, dimension, v0_element=4096,
                         kv_heads=8, max_positions=TMAX) == layout.v_elem(layer, head, position, dimension)


@pytest.mark.parametrize("sw", [8, 16])
def test_vector_k_beats_stripe_distinct_tail_write_ports_and_flush_full_sectors(sw):
    width, hd, kv, tiles = 16, 128, 8, 512
    v0 = 36 * kv * tiles * hd * width
    tail = BankedTail(sw)
    sectors = SectorAssembly()
    position = 32  # tile parity zero, lane zero
    first_word = k_element(0, 0, position, 0, kv_heads=kv,
                           position_tiles=tiles) // width
    for pos in (position, position + 1):
        for base in range(0, hd, sw):
            tail.write_vector([(k_element(0, 0, pos, d, kv_heads=kv,
                                           position_tiles=tiles), (d + pos) & 255)
                               for d in range(base, base + sw)], v0_element=v0)
    tail.flush_k_tile(first_word, sectors)
    assert sectors.rmw_writes == 0 and not sectors.pending
    assert sectors.full_writes == hd * width // 32
    for d in range(hd):
        word = tail.read_word(first_word + d)
        assert word[0] == (d + position) & 255
        assert word[1] == (d + position + 1) & 255
        assert word[2:] == bytes(width - 2)


@pytest.mark.parametrize("sw", [8, 16])
def test_v_vectors_assemble_32_byte_sectors_and_partial_requires_rmw(sw):
    v0, kv, tmax, hd = 4096, 8, 8192, 128
    sectors = SectorAssembly()
    for base in range(0, hd, sw):
        for d in range(base, base + sw):
            sectors.put(v_element(0, 0, 0, d, v0_element=v0, kv_heads=kv,
                                  max_positions=tmax), d)
    assert sectors.full_writes == 4 and sectors.rmw_writes == 0
    assert b"".join(sectors.memory[(v0 // 32) + i] for i in range(4)) == bytes(range(hd))
    sectors.put(v0 + 3, 217)
    sectors.drain_partial()
    assert sectors.rmw_writes == 1
    assert sectors.memory[v0 // 32][2:5] == bytes((2, 217, 4))


def test_bank_collision_is_explicit_instead_of_silent_drop():
    tail = BankedTail(8)
    with pytest.raises(ValueError, match="one tail write port"):
        tail.write_vector([(0, 1), (8 * 16, 2)], v0_element=8192)
