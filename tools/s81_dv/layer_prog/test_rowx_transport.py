"""ROWX compiler transform versus independent xhalf/PK2 RTL field decoding."""
import copy
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rowx_transport as R


def hword(tile, rank, piece):
    # Independent concatenation from the source xhalf, MSB to LSB.
    fields = [(0, 88), (piece >> 89 & ((1 << 39) - 1), 39), (0, 9),
              (piece & ((1 << 89) - 1), 89), (piece >> 128, 16),
              (rank, 10), (tile, 4), (1, 1)]
    h = 0
    for val, width in fields:
        h = h << width | val
    return h


def scenario(half=0, nsel=512, skew=False):
    rng = random.Random(442)
    gids = [((0 if skew and r < 300 else r % 16) % 4) << 4 |
            ((0 if skew and r < 300 else r % 16) // 4) << 6 | (r // 16) << 8
            for r in range(nsel)]
    pieces = {(t, r): rng.getrandbits(144) for t in range(half * 8, half * 8 + 8) for r in range(nsel)}
    ex = {o: {t: [] for t in range(half * 8, half * 8 + 8)} for o in range(16)}
    for o in ex:
        for t in ex[o]:
            for w in range(280):
                q = int(w % 40 % 5 == 0) << 512
                for j in range(2):
                    r = 2 * w + j
                    if r < nsel and R.owner_of(gids[r]) == o:
                        q |= hword(t, r, pieces[t, r]) << (256 * j)
                ex[o][t].append(q)
    return ex, gids, pieces


@pytest.mark.parametrize('half,receiver,skew', [(0, 0, False), (1, 15, False), (0, 7, True)])
def test_all_rows_and_static_slots(half, receiver, skew):
    ex, gids, pieces = scenario(half, skew=skew)
    out = R.merge_repair(ex, gids, receiver, half)
    frame = R.rows_frame(out, 0x8d, pos=524287, user=1023)
    assert len(out) == 2048 and len(frame) == 2049
    hdr = frame[0]
    assert hdr >> 508 == 6 and (hdr >> 480) & 4095 == 2048 and hdr & 1
    assert (hdr >> 495) & 255 == 0x8d and (hdr >> 459) & ((1 << 21) - 1) == 524287
    landed = {}
    for r in range(512):
        for p in range(4):
            q = out[4 * r + p]
            for j in range(2):
                t = 8 * half + 2 * p + j
                h = q >> (256 * j) & R.MASK256
                if R.owner_of(gids[r]) == receiver:
                    assert h == 0  # Own fetched data is never re-landed (RTL fault 29).
                    continue
                assert h & 1 and (h >> 1) & 15 == t and (h >> 5) & 1023 == r
                b = ((h >> 15) & 65535) << 128 | ((h >> 129) & ((1 << 39) - 1)) << 89 | ((h >> 31) & ((1 << 89) - 1))
                assert b == pieces[t, r]
                assert (t, r) not in landed
                landed[t, r] = b
    assert len(landed) == 8 * sum(R.owner_of(g) != receiver for g in gids)
    s = R.ExportSpec()
    assert [s.entry_cycle(0, w) for w in (0, 39, 40, 279)] == [0, 39, 320, 1959]
    assert s.entry_cycle(7, 279) == 2239
    assert (s.header_spec() >> 31) & 15 == 6


@pytest.mark.parametrize('bad', ['rank_mutant', 'tile_mutant', 'duplicate_holder', 'drop_slot',
                                  'drop_held', 'stamp_field', 'head_mutant', 'nonzero_invalid'])
def test_malformed_or_mutant_streams_fail_closed(bad):
    ex, gids, _ = scenario()
    if bad == 'rank_mutant':
        ex[0][0][0] ^= 1 << 5
    elif bad == 'tile_mutant':
        ex[0][0][0] ^= 1 << 1
    elif bad == 'duplicate_holder':
        ex[1][0][0] |= ex[0][0][0] & R.MASK256
    elif bad == 'drop_slot':
        ex[0][0].pop()
    elif bad == 'drop_held':
        ex[0][0][0] &= ~R.MASK256
    elif bad == 'stamp_field':
        ex[0][0][0] |= 1 << 120
    elif bad == 'head_mutant':
        ex[0][0][0] ^= 1 << 512
    else:
        ex[0][0][279] |= 1 << 10
    with pytest.raises(ValueError):
        R.merge_repair(ex, gids, 0, 0)


@pytest.mark.parametrize('spec', [R.ExportSpec(passes=6), R.ExportSpec(period=319), R.ExportSpec(nxw=5), R.ExportSpec(passes=17)])
def test_invalid_static_booking(spec):
    with pytest.raises(ValueError):
        spec.check(512)


def test_missing_owner_and_wrong_half():
    ex, gids, _ = scenario()
    with pytest.raises(ValueError):
        R.merge_repair(ex, gids, 0, 1)
    del ex[15]
    with pytest.raises(ValueError):
        R.merge_repair(ex, gids, 0, 0)


def test_pvrd_wrap_deadlines_are_not_a_fictitious_full_export_buffer():
    reads = R.landing_reads(512, 0, rb=256)
    assert len(reads) == 4096
    by = {(r['rank'], r['tile']): r for r in reads}
    a, b = by[0, 0], by[0, 4]
    assert (a['leaf'], a['row']) == (b['leaf'], b['row']) == (0, 256)
    assert a['available_cycle'] == 0 and a['overwrite_cycle'] == b['available_cycle'] == 160
    assert by[1, 0]['row'] == 258
    for x in reads:
        assert x['overwrite_cycle'] - x['available_cycle'] == 160
        assert x['row'] <= 383
