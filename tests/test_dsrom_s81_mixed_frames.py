import argparse
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import dsrom_s81_fulldie as F

V9 = '--gen r8 --rev r9 --elem-h 198.72 --bf-per-region 4 --ch-heights 259.2,302.4,388.8,388.8,302.4,259.2,259.2'


def setup(extra):
    F.apply_options(F.die_options(argparse.ArgumentParser()).parse_args((V9 + ' ' + extra).split()))


@pytest.fixture(autouse=True)
def reset_globals():
    yield
    F.apply_options(F.die_options(argparse.ArgumentParser()).parse_args(['--elem-h', '157.68', '--field-margin', '216']))


@pytest.mark.parametrize('die', ['layer', 'layer1'])
def test_flat_bf_map_identical_on_both_layer_flavours(die):
    setup(f'--die {die} --pairs 2304 --q-elem-h 183.60')
    assert F.BF_PAIRS == 512
    assert F.bf_sites() == {i * 2304 // 512 for i in range(512)}
    elems, offsets, heights = F.pack_frame(range(18), F.bf_sites(), set())
    assert [p for p, _, _, _ in elems] == list(range(18))
    assert [h for h in heights] == [280.8, 265.68, 265.68, 280.8, 265.68, 265.68, 280.8, 265.68, 280.8, 265.68, 265.68]
    assert sum(heights) == pytest.approx(2982.96)
    assert offsets[-1] + heights[-1] == pytest.approx(2982.96)
    # The allocator candidate does NOT fit the later widened-channel v9 floorplan.
    assert not F._frames_fit(F.SLOTS8, F.SLOT_H8)


def test_larger_q_requires_fewer_pairs_without_shrinking_channels():
    setup('--die layer1 --pairs 2048 --q-elem-h 221.4')
    assert not F._frames_fit(F.SLOTS8, F.SLOT_H8)
    F.set_pairs(1792)
    assert F._frames_fit(F.SLOTS8, F.SLOT_H8)
    assert F.column_height() <= 2887.574


def test_mixed_and_uniform_packing_preserve_pair_identity():
    setup('--pairs 2048')
    baseline, _, hs = F.pack_frame(range(16), F.bf_sites(), set())
    assert len(set(hs)) == 1
    setup('--pairs 2048 --q-elem-h 183.60')
    mixed, _, _ = F.pack_frame(range(16), F.bf_sites(), set())
    assert mixed == baseline
    assert F._frames_fit(F.SLOTS8, F.SLOT_H8)
