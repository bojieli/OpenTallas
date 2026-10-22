#!/usr/bin/env python3
"""DRIVE-S81-GUPROP (10-20): unit tests of the opt-in GU_PROP placement (no fixtures).
  * default (OT_XS_GU_PROP unset): gu_slice_deal == deal(nff, 16) and merged_cap tags == the S81-ROMOPT-A formula
  * GU_PROP at the 98- and 84-frame topologies: whole quads per slice in proportion to the frames, contiguous; the frame
    rows of gu_prop_frames keep the default row COUNT per frame; merged_cap tags decode (cap_model) to the SW row-pair
    layout (gate quad q -> row 2 q, up quad q -> row 2 q + 1 of the slice region, leaf 0); no cap pairing-slot collision
    inside any phase (TP.chunk of every frame).
"""
import importlib
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 's81_slice'))
T98 = [6, 8, 6, 8, 6, 8, 3, 4, 3, 4, 6, 8, 6, 8, 6, 8]
T84 = [6, 8, 3, 4, 6, 8, 3, 4, 3, 4, 6, 8, 3, 4, 6, 8]


def load(gp):
    os.environ.update(OT_XS_TOPO='1', OT_XS_PROP='1', OT_XS_GU_MERGE='1')
    if gp:
        os.environ['OT_XS_GU_PROP'] = '1'
    else:
        os.environ.pop('OT_XS_GU_PROP', None)
    import xs_flags
    import xs_topo
    import xs_place
    for m in (xs_flags, xs_topo, xs_place):
        importlib.reload(m)
    return xs_place


def test_default():
    XP = load(False)
    XP.TP.TOPO = T98
    assert not XP.GU_PROP and XP.gu_slice_deal(576) == XP.deal(576, 16)
    mc = XP.merged_cap(576)
    for s, js in enumerate(XP.deal(576, 16)):
        for i, j in enumerate(js):
            assert mc['cap_tags'][j] == 640 * s + i and mc['cap_tags'][576 + j] == 640 * s + 320 + i
    print('PASS test_default')


def test_gu_prop(topo, R=4):
    from cap_model import decode
    XP = load(True)
    XP.TP.TOPO = topo
    assert XP.GU_PROP
    js = XP.gu_slice_deal(576)
    assert sum(map(len, js)) == 576 and [j for x in js for j in x] == list(range(576))
    assert all(len(x) % 4 == 0 for x in js)
    g = XP.gu_prop_frames(576, js, R)
    ref = [[2 * len(f) for f in XP.deal_into(x, XP.TP.nfr(s))] for s, x in enumerate(js)]
    assert [[len(f) for f in fs] for fs in g] == ref, 'frame row counts changed'
    mc = XP.merged_cap(576)
    grp = dict(groups=g)
    most = max(len(f) for fs in g for f in fs)
    for s, x in enumerate(js):
        rb, rc = mc['cap_range'][s]
        cfg = dict(rbase=rb, rcnt=rc, np=0, fmt=2, obase=0, ops=0, rsplit=0, lo32=0, hi32=0)
        for i, j in enumerate(x):
            q, r = divmod(i, 4)
            for kind, row in ((0, 2 * q), (1, 2 * q + 1)):
                bad, leaf, _p, addr, _d = decode(mc['cap_tags'][kind * 576 + j] << 13, 0, cfg)
                assert not bad and leaf == 0 and addr == 4 * row + r, (s, i, kind, bad, leaf, addr)
        for c in range(-(-most // R)):
            tags = [mc['cap_tags'][row] for f in g[s] for row in XP.TP.chunk(grp, f, c, R)]
            assert len({t & 63 for t in tags}) == len(tags), ('pairing-slot collision', s, c)
    print('PASS test_gu_prop', sum(topo), 'frames', [len(x) for x in js])


if __name__ == '__main__':
    test_default()
    test_gu_prop(T98)
    test_gu_prop(T84)
    test_default()
