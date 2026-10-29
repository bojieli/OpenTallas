"""Recoded-state predicates use exact three-valued AND, including known-false atoms.

HBM pc_ctrl_leaf had cube obligations on gold next-state bits that can contain
power-up X from metadata. A raw XOR falsely rejected those obligations; masking
only when ALL state bits are known would instead hide a known-false predicate.
"""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec


def _design(values, gate=None):
    m = lec.Aig()
    if gate is None:
        unknown = [m.add_input('x0'), m.add_input('x1')]
        q = [m.add_input('q0'), m.add_input('q1')]
        nxt = [unknown[i] if v is None else v for i, v in enumerate(values)]
        names = ['u.st[0]', 'u.st[1]']
        nin = 2
    else:
        q = [m.add_input('q')]
        nxt, names, nin = [gate], ['u.hot'], 0
    aig = dict(I=nin, L=len(q), O=0, A=0, latches=nxt, outputs=[], ands=m.ands)
    # Unnamed AIG inputs model RTL X, as in a gold array before its first write.
    amap = dict(input={}, output={}, latch={
        i: [(name+'$_DFF_P_.lecq', 0)] for i, name in enumerate(names)})
    return aig, amap


def _assert_constant(m, expected):
    # Exhaust every current-state/X assignment on this tiny mechanism.
    for bits in itertools.product((0, 1), repeat=m.ni):
        val = {0: 0, **{i+1: b for i, b in enumerate(bits)}}
        get = lambda lit: val[lit >> 1] ^ (lit & 1)
        for i in range(len(m.ands)//2):
            val[m.ni+i+1] = get(m.ands[2*i]) & get(m.ands[2*i+1])
        assert [get(o) for o in m.outs] == [expected]


def test_all_two_bit_ternary_cube_obligations():
    for values in itertools.product((0, 1, None), repeat=2):
        for target in itertools.product((0, 1), repeat=2):
            false = any(v is not None and v != t for v, t in zip(values, target))
            expected_cube = 0 if false else (1 if None not in values else None)
            for gate in (0, 1):
                gold, gm = _design(values)
                mapped, tm = _design((), gate=gate)
                model = lec.Lec(gold, gm, mapped, tm)
                model.hyp['gate', 'ff:u.hot'] = (
                    'cube', 'gold', ['ff:u.st[0]', 'ff:u.st[1]'], list(target))
                m, _ = model.build(with_compare=False, with_hyp=True)
                _assert_constant(m, int(expected_cube is not None and expected_cube != gate))
