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


def test_area_clock_pin_survives_mixed_geometry_support():
    master = F.Q.Master('clocked', 100, 100, 6, 'area-clock regression')
    master.ports = {'ck': ('area', 'M7', 50.0, 50.0, 2.0, 4.0)}
    master.order = ['ck']
    assert F.pin_rects(master, 1, {}) == [('ck[0]', 'M7', (49.0, 48.0, 51.0, 52.0))]


def test_pq_place_root_row_keeps_mixed221_frames():
    # s81-die-2 2026-10-08: the adopted PQ root (132.192 x 211.68, root row 241.92) must not cost the 1792-pair
    # mixed221 layer die its 9th slot ("frame 0: mixed slots exceed field height" on the r3/r4 options).
    setup('--die layer1 --pairs 1792 --q-elem-h 221.4 --pq-place')
    assert F.PQ_ROOT_ROW == pytest.approx(241.92)
    assert F.CHS[0] == pytest.approx(259.2 + 241.92) and F.CHS[-1] == pytest.approx(259.2)
    assert F.SLOTS8 == 9
    assert F._frames_fit(F.SLOTS8, F.SLOT_H8)
    rng, _ = F.frame_plan_r8()
    bfs = F.bf_sites()
    for r in range(F.ROOTS):
        _, _, heights = F.pack_frame(list(range(*rng[r])), bfs, set())
        assert sum(heights) <= F.column_height() + 1e-6
    band = F.up(F.EDGE, F.GY) + F.PHY_H + 8.64 + F.CTRL_D + 8.64 + F.SVC_D
    field_h = F.TIERS * F.column_height() + sum(F.chh(t) for t in range(F.TIERS + 1))
    gap = (F.DIE[1] - field_h) / 2 - band
    assert F.PQ_FIELD_MARGIN <= gap < F.FIELD_MARGIN_DEFAULT


def test_explicit_field_margin_overrides_pq_default_on_every_gen():
    # a --pq-place run must not leak its 108-um minimum gap into a later configuration (any --gen)
    setup('--die layer1 --pairs 1792 --q-elem-h 221.4 --pq-place')
    assert F.FIELD_MARGIN == pytest.approx(F.PQ_FIELD_MARGIN)
    F.apply_options(F.die_options(argparse.ArgumentParser()).parse_args(['--elem-h', '157.68', '--field-margin', '216']))
    assert F.FIELD_MARGIN == pytest.approx(216.0)


R4 = ('--rev r9 --elem-h 198.72 --cc-reach-um 215 --vch-interleave --link-fix --corr-interleave --hop-fix --meso-d8 '
      '--cfifo-v2 --hc-xface --link-split --sel-xstg --pin-relay --ch-heights 259.2,302.4,388.8,388.8,302.4,259.2,259.2 '
      '--bf-per-region 4 --geometry-fix --vch-w 1641.6 --hc-corr 1512 --hub-column-width 1728 --su-mm2 25.61188 '
      '--pairs 1792 --q-elem-h 221.4 --pq-place --die layer1 --nxt-reach')


@pytest.mark.skipif(not __import__('os').environ.get('OT_S81_FULLDIE_SLOW'), reason='full r4 die build (~1 h); OT_S81_FULLDIE_SLOW=1')
def test_r4_nxt_reach_builds_with_adopted_pq_root():
    # s81-die-2 2026-10-08: m221pq_r4 (r3 + --nxt-reach) failed twice in _hop_fix: es_12_y0 found no spot (the relaxed
    # path lacked the legacy whole-die fallbacks) and the nxt_relaxed counter (an int in the class table) broke the summary
    setup(R4.replace('--rev r9', ''))
    m = F.build()
    F.finalize_r8(m)
    lg = F.legality(m)
    assert lg['overlaps'] == 0 and lg['outside'] == 0
    cls = m['hop_fix']['classes']
    assert all(isinstance(v, dict) for v in cls.values())
