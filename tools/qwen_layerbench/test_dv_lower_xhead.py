#!/usr/bin/env python3
"""tests of dv_lower_xhead (QW-XHEAD 10-19): DV x relocation, ib / hr packing against the RTL field slices, the consumer
constraints."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dv_lower_vec as V      # noqa: E402
import dv_lower_xhead as X    # noqa: E402

AW, NW = X.AW, X.NW


def test_relocation_matches_producers():
    ops = X.me_ops()
    for name, mode in (('qkv', 'resid'), ('gu', 'resid'), ('o', 'attn'), ('down', 'silu')):
        lw = V.lower_vec(mode, ar_order='row' if mode == 'resid' else 'slice')
        _, ea = X.x_edges(lw['expected']['x'])
        f = X.dv_fields(ops[name], ea)
        assert f['me_xbase'] == 0 and f['isa_xbase'] != 0
        try:                                    # the ISA (central VM) base does not match the stream
            X.dv_fields(dict(ops[name], me_k=ops[name]['me_k'] + 1), ea)
            raise AssertionError('a wrong footprint was accepted')
        except X.LowerError:
            pass


def test_ib_fields_where_the_head_reads_them():
    f = dict(me_nout=4096, me_tiles=3, me_k=2, me_wsrc=0, me_xbase=0x123456, me_xks=1, me_xjs=0, me_xcs=2, me_split=8,
             me_round=1, me_wbase=64)
    ib = X.pack_ib(f)
    IBW = X.IBW
    sl = lambda lo, w: (ib >> lo) & ((1 << w) - 1)    # noqa: E731  (ot_qfd_xhead b_* slices)
    assert sl(IBW - 2 * NW, NW) == 3                    # b_tiles
    assert sl(IBW - 3 * NW, NW) == 2                    # b_k
    assert sl(13 * AW + 12, 1) == 0                     # b_wsrc
    assert sl(8 * AW + 12, AW) == 0x123456              # b_xbase
    assert sl(7 * AW + 12, AW) == 1                     # b_xks
    assert sl(6 * AW + 12, AW) == 0                     # b_xjs
    assert sl(5 * AW + 12, AW) == 2                     # b_xcs
    assert sl(5 * AW + 5, 4) == 8                       # b_split
    assert sl(4 * AW + 4, 1) == 1                       # b_round


def test_hr_word_layout():
    w = X.hr_word(go=1, ib=(1 << 378) | 5, xpf72=(1 << 71) | 3)
    assert w & 1 == 1                                   # hv
    assert (w >> 1) & 1 == 1                            # xpf_v = hr[1]
    assert (w >> 72) & 1 == 1                           # xpf[71] = hr[72]
    assert (w >> 73) & 7 == 5 and (w >> 451) & 1 == 1   # ib = hr[451:73]
    assert w >> 452 == 1                                # go = hr[452]


def test_consumer_constraints():
    ages = dict(x_tap=3, xpf_lead=3, go_lag=2, d_head=12, read_tail=6)
    f = dict(pc=16, me_tiles=1, me_k=32, me_round=1, me_split=7, me_xks=1, me_xcs=32, me_xbase=0)
    xs = {m: [100 + m, 140 + m] for m in range(12)}
    hr = list(range(12))
    c = X.lower_consumer('gu', f, xs, ages, hr)
    assert all(v == 0 for v in c['slack_go'].values()) and all(v >= 0 for v in c['slack_xpf'].values())
    assert c['go_w5'] == 140 + 3 + 2 and c['xpf_w5'] == 100 + 3 - 3
    c2 = X.lower_consumer('gu', f, xs, ages, hr, go_at=100)
    assert c2['go_w5'] == c['go_w5'] and c2['go_delay'] == c['go_w5'] - 100
    try:
        X.lower_consumer('gu', f, xs, ages, hr, prev_xt={m: 200 for m in range(12)})
        raise AssertionError('XPF before the previous op writes accepted')
    except X.LowerError:
        pass


if __name__ == '__main__':
    for n, t in sorted(globals().items()):
        if n.startswith('test_'):
            t()
            print('PASS', n)
