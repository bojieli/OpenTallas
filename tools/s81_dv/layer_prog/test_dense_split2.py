#!/usr/bin/env python3
"""DENSE2 (DRIVE-S81 10-20): unit tests of the opt-in dense-layer split over a 2-stage die group.

  python3 test_dense_split2.py                       logic tests (fake die / fake fixture shapes; no fixtures needed)
  OT_DENSE2_FIX=<fixtures>/L0 OT_DENSE2_DIE=<dieref> python3 test_dense_split2.py   + exact numerics on the real die/fixture

Checks:
  1 default (OT_XS_DENSE_SPLIT2 unset) placement is identical to the pre-DENSE2 algorithm (copied verbatim below) at
    112 / 116 / 122 frames, and still refuses < 112 frames (wq_a one-phase);
  2 split A / B at 98 / 84 frames: every frame one tensor, <= 4 rows, rows contiguous per frame; A rows ++ B rows
    (stage order, frame order) == the one-stage rank-row order 0..447 (each row exactly once); X = no rows;
  3 spec_env / _apply_env: a spec without the key never changes the env, a pooled worker is cleaned between specs;
  4 build_split on synthetic costs: per layer A then B on two DIFFERENT consecutive dense stages, at most one dense
    item a stage, every expert exactly once, causality (every expert of layer L-1 on a stage <= A(L)'s stage, every
    expert of L on a stage >= B(L)'s stage), A(L)+1 == B(L);
  5 (with fixtures) on the real die minus frames: a frame compiled under split A / B (frame_programme, identity
    assignment) returns, for every placed row, the golden segment sums of that row and the row's FP32 accumulator
    rounds to the fixture's BF16 a_proj output at the same golden index (exactly as lower_xs gen asserts).
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ.setdefault('OT_XS_APROJ_TOPO', '1')
import lower_xs as LX  # noqa: E402


# ------------------------------------------------------------------------------------------------ fakes
class FakeDie:
    def __init__(self, topo):
        self._s = {f's{g:02d}': dict(sid=g) for g in range(len(topo))}
        self._f = {f's{g:02d}': [f'u_f_{g:02d}_{j}' for j in range(n)] for g, n in enumerate(topo)}
        self.inst = {f: dict(master='col_h10_l4') for fr in self._f.values() for f in fr}

    def slices(self):
        return dict(self._s)

    def frames_of(self, sl):
        return list(self._f[sl])

    def strap(self, f, k):
        return 0x249


class _W:
    def __init__(self, n):
        self.shape = (n, 5120)


FX = dict(w=dict(wq_a=(_W(320), None), wkv=(_W(128), None)))
TOPOS = {112: [8] * 12 + [4] * 4, 116: [8] * 10 + [6] * 6, 122: [8] * 12 + [7, 7, 6, 6],
         98: [6, 8, 6, 8, 6, 8, 3, 4, 3, 4, 6, 8, 6, 8, 6, 8], 84: [6, 8, 3, 4, 6, 8, 3, 4, 3, 4, 6, 8, 3, 4, 6, 8]}


def ref_placement(die, sl, fx):
    """the pre-DENSE2 OT_XS_APROJ_TOPO branch of lower_xs.placement, verbatim"""
    frames = die.frames_of(sl)
    g = LX.slice_index(die, sl)
    slices = sorted(die.slices(), key=lambda s: LX.slice_index(die, s))
    all_frames = [f for s in slices for f in die.frames_of(s)]
    tensors = [('wq_a', fx['w']['wq_a'][0].shape[0]), ('wkv', fx['w']['wkv'][0].shape[0])]
    total = sum(n for _, n in tensors)
    numer = [n * len(all_frames) for _, n in tensors]
    counts = [n // total for n in numer]
    for i in sorted(range(len(counts)), key=lambda i: (-(numer[i] % total), i))[:len(all_frames) - sum(counts)]:
        counts[i] += 1
    assigned, row0, fi = {}, 0, 0
    for (name, nrows), nf in zip(tensors, counts):
        assert 0 < nf <= nrows and nrows <= nf * LX.ROWS_PER_FRAME, ('a_proj one-phase capacity', name, nrows, nf)
        q, rem = divmod(nrows, nf)
        off = row0
        for j in range(nf):
            n = q + (j < rem)
            assigned[all_frames[fi]] = list(range(off, off + n))
            off += n
            fi += 1
        row0 += nrows
    return g, [dict(frame=f, master=die.inst[f]['master'], lk=die.strap(f, 'lk'), rows=assigned[f]) for f in frames]


def set_split(v, rows=None):
    for k in ('OT_XS_DENSE_SPLIT2', 'OT_XS_DENSE_SPLIT2_ROWS'):
        os.environ.pop(k, None)
    if v:
        os.environ['OT_XS_DENSE_SPLIT2'] = v
    if rows is not None:
        os.environ['OT_XS_DENSE_SPLIT2_ROWS'] = str(rows)


def die_rows(die, fx):
    out = []
    for sl in sorted(die.slices(), key=lambda s: LX.slice_index(die, s)):
        out += LX.placement(die, sl, fx)[1]
    return out


def tensor_of(r):
    return 'wq_a' if r < 320 else 'wkv'


# ------------------------------------------------------------------------------------------------ tests
def test_default_identical():
    set_split(None)
    for F in (112, 116, 122):
        die = FakeDie(TOPOS[F])
        assert sum(TOPOS[F]) == F
        for sl in die.slices():
            assert LX.placement(die, sl, FX) == ref_placement(die, sl, FX), (F, sl)
    for F in (98, 84):
        die = FakeDie(TOPOS[F])
        try:
            die_rows(die, FX)
        except AssertionError as e:
            assert 'a_proj one-phase capacity' in repr(e)
        else:
            raise AssertionError(f'default must still refuse {F} frames')
    print('PASS test_default_identical')


def test_split_rows():
    for F in (98, 84):
        die = FakeDie(TOPOS[F])
        for R in (None, 160, 224, 300):
            seq = []
            for half in 'AB':
                set_split(half, R)
                pl = die_rows(die, FX)
                assert len(pl) == F
                for p in pl:
                    r = p['rows']
                    assert 0 < len(r) <= LX.ROWS_PER_FRAME, (F, half, p)
                    assert r == list(range(r[0], r[0] + len(r))), p
                    assert len({tensor_of(x) for x in r}) == 1, ('frame mixes wq_a and wkv', p)
                    seq += r
            assert seq == list(range(448)), (F, R)
        set_split('X')
        assert all(p['rows'] == [] for p in die_rows(die, FX))
    set_split('A', 448)
    try:
        die_rows(FakeDie(TOPOS[98]), FX)
    except AssertionError as e:
        assert 'DENSE2 split rows' in repr(e)
    else:
        raise AssertionError('R = 448 must be refused')
    set_split(None)
    print('PASS test_split_rows')


def test_spec_env():
    import xs_capacity as XC
    base = {'OT_XS_QPAIRS': '12'}
    assert XC.spec_env(dict(id='exp_n3', experts=3, dense_layer=None), base) == base
    e = XC.spec_env(dict(id='L3A_n0', experts=0, dense_layer=3, dense_split2='A', dense_split2_rows=224), base)
    assert e == dict(base, OT_XS_DENSE_SPLIT2='A', OT_XS_DENSE_SPLIT2_ROWS='224')
    XC._apply_env(e)
    assert os.environ['OT_XS_DENSE_SPLIT2'] == 'A'
    XC._apply_env(XC.spec_env(dict(id='exp_n3', experts=3, dense_layer=None), base))
    assert 'OT_XS_DENSE_SPLIT2' not in os.environ and 'OT_XS_DENSE_SPLIT2_ROWS' not in os.environ
    assert XC.spec_ops(dict(dense_layer=2, dense_split2='A'))[:2] == (['ffn.experts_gu', 'ffn.down'], [])
    assert XC.spec_ops(dict(dense_layer=2, dense_split2='B')) == XC.spec_ops(dict(dense_layer=2))
    try:
        XC.spec_env(dict(id='x', experts=1, dense_layer=None, dense_split2='A'), base)
    except AssertionError:
        pass
    else:
        raise AssertionError('A half without a dense layer must be refused')
    print('PASS test_spec_env')


def test_build_split():
    import xs_stage_map as SM
    cls = ('L0', 'L1', 'L2', 'L14', 'L20', 'L24')
    c = dict(slope=82.3, phases_per_expert=6.0, dense_split2_rows=224,
             dense_split2=dict(A={k: dict(q=300, bf=0, phases=1) for k in cls},
                               B={k: dict(q=900 + 40 * i, bf=1400, phases=60) for i, k in enumerate(cls)}))
    nmin = SM.min_stages_split(c)
    for nst in (nmin, nmin + 9):
        m = SM.build_split(nst, c, 't')
        assert m['stages_count'] <= nst
        st = m['stages']
        where = {}
        exp_stage = {}
        for i, s in enumerate(st):
            assert s['dense_split2'] in ('A', 'B', 'X')
            if s['dense_layer'] is not None:
                where[(s['dense_layer'], s['dense_split2'])] = i
            for L, a, b in s['experts']:
                for e in range(a, b + 1):
                    assert (L, e) not in exp_stage
                    exp_stage[(L, e)] = i
            assert s['model_load'] < 8192 * 1.0 or nst != nmin
        assert len(exp_stage) == 40 * 384
        for L in range(40):
            a, b = where[(L, 'A')], where[(L, 'B')]
            assert b == a + 1, (L, a, b)
            assert all(exp_stage[(L, e)] >= b for e in range(384))
            if L:
                assert all(exp_stage[(L - 1, e)] <= a for e in range(384))
        sp = SM.specs_of(m)
        assert all(x['dense_split2'] in 'ABX' for x in sp)
    print('PASS test_build_split', nmin)


def test_numerics():
    fixd, dsrc = os.environ.get('OT_DENSE2_FIX'), os.environ.get('OT_DENSE2_DIE')
    if not (fixd and dsrc):
        print('SKIP test_numerics (OT_DENSE2_FIX / OT_DENSE2_DIE unset)')
        return
    import numpy as np
    import dv_layer_compile as C
    import hdc_golden_v41 as G
    import v41_rom_ksplit_bankmap as S
    import v41_die_images_w17w10 as I
    import xs_topo as TP
    keep = int(os.environ.get('OT_DENSE2_FRAMES', '98'))
    die = C.Die(C.die_tree(src=dsrc))
    per = {sl: list(die.frames_of(sl)) for sl in die.slices()}
    drop = set()
    while sum(map(len, per.values())) > keep:          # drop the last frame of the largest slice, round-robin
        sl = max(sorted(per), key=lambda k: len(per[k]))
        drop.add(per[sl].pop()[2:])
    die.plan['blocks'] = [b for b in die.plan['blocks'] if not (b['kind'] == 'frame' and b['name'] in drop)]
    die.inst = {k: v for k, v in die.inst.items() if k[2:] not in drop}
    TP.set_from_die(die)
    fx = LX.load_fixture(fixd)
    ap = fx['a_proj']
    xq, xe = G.quant_fp8(fx['x'])
    seen = []
    for half in 'AB':
        set_split(half)
        pl = [p for sl in sorted(die.slices(), key=lambda s: LX.slice_index(die, s)) for p in LX.placement(die, sl, fx)[1]]
        assert len(pl) == keep
        seen += [r for p in pl for r in p['rows']]
        picks = [pl[0], pl[len(pl) // 2], pl[-1]]
        for p in picks:
            mats, gidx = LX.frame_mats(fx, p['rows'])
            _f, ph, plan, qa, q, bf = LX.frame_programme(p['master'], p['lk'], mats, fx['x'], iters=0, rank_rows=p['rows'])
            gold = I.golden_phase(mats, fx['x'])
            m = mats[0]
            segs = S.segments(m.K, ph['matrices'][0]['split'])
            blocks = np.stack([np.ldexp((m.w.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(G.F),
                                        m.w.e[:, b] + xe[b]).astype(G.F) for b in range(m.K // 32)], axis=-1)
            for r in range(m.rows):
                vals = [int(G.bits(G.csum(blocks[r, e0 // 32:(e0 + el) // 32]))) for e0, el in segs]
                assert plan['rows_vals'][str(r)] == vals, (half, p['frame'], r)
                fb = int(G.bits(G.F(ap[gidx[r]])))
                assert fb >> 16 == gold[r][1] and not fb & 0xFFFF, (half, p['frame'], r, gidx[r])
            print('NUMERICS', half, p['frame'], 'rows', p['rows'][0], '..', p['rows'][-1], 'golden idx', gidx[0], '..', gidx[-1],
                  'faults', plan['faults'])
    assert seen == list(range(448)), 'A ++ B rows != one-stage order'
    set_split(None)
    print('PASS test_numerics', keep, 'frames')


def test_gu_prop_default_off():
    import importlib
    os.environ.pop('OT_XS_GU_PROP', None)
    import xs_place as XP
    importlib.reload(XP)
    assert not XP.GU_PROP and XP.gu_slice_deal(576) == XP.deal(576, 16)
    print('PASS test_gu_prop_default_off')


if __name__ == '__main__':
    test_gu_prop_default_off()
    test_default_identical()
    test_split_rows()
    test_spec_env()
    test_build_split()
    test_numerics()
    print('DENSE2_TESTS PASS')
