"""depth_opt.py: same function on random generic netlists, serial chains become trees, registers and muxes untouched."""
import importlib.util
import itertools
import random
from pathlib import Path

S = importlib.util.spec_from_file_location("depth_opt", Path(__file__).with_name("depth_opt.py"))
D = importlib.util.module_from_spec(S); S.loader.exec_module(D)

F = {'$_AND_': lambda a, b: a & b, '$_OR_': lambda a, b: a | b, '$_XOR_': lambda a, b: a ^ b, '$_XNOR_': lambda a, b: 1 ^ a ^ b,
     '$_NAND_': lambda a, b: 1 ^ (a & b), '$_NOR_': lambda a, b: 1 ^ (a | b), '$_ANDNOT_': lambda a, b: a & (1 ^ b),
     '$_ORNOT_': lambda a, b: a | (1 ^ b)}


def cell(t, y, **pins):
    return {'type': t, 'connections': {**{k: [v] for k, v in pins.items()}, 'Y': [y]},
            'port_directions': {**{k: 'input' for k in pins}, 'Y': 'output'}}


def module(cells, ins, outs):
    return {'ports': {'i': {'direction': 'input', 'bits': list(ins)}, 'o': {'direction': 'output', 'bits': list(outs)}},
            'cells': cells, 'netnames': {}}


def evaluate(m, vec):
    val = dict(zip(m['ports']['i']['bits'], vec))
    drv = {c['connections']['Y'][0]: c for c in m['cells'].values()}

    def v(b):
        if b not in val:
            c = drv[b]; x = c['connections']
            if c['type'] == '$_NOT_':
                val[b] = 1 ^ v(x['A'][0])
            elif c['type'] == '$_MUX_':
                val[b] = v(x['B'][0]) if v(x['S'][0]) else v(x['A'][0])
            else:
                val[b] = F[c['type']](v(x['A'][0]), v(x['B'][0]))
        return val[b]
    return [v(b) for b in m['ports']['o']['bits']]


def rand_module(rng, n_in=7, n_gate=60):
    ins = list(range(2, 2 + n_in)); bits = list(ins); cells = {}
    for k in range(n_gate):
        y = 100 + k; t = rng.choice(['$_AND_', '$_OR_', '$_XOR_', '$_XNOR_', '$_NOT_', '$_MUX_', '$_AND_', '$_OR_'])
        # mostly read recent nets, so long single-user chains appear
        pick = lambda: rng.choice(bits[-4:] if rng.random() < 0.7 else bits)
        if t == '$_NOT_':
            cells[f'g{k}'] = cell(t, y, A=pick())
        elif t == '$_MUX_':
            cells[f'g{k}'] = cell(t, y, A=pick(), B=pick(), S=pick())
        else:
            cells[f'g{k}'] = cell(t, y, A=pick(), B=pick())
        bits.append(y)
    return module(cells, ins, bits[-5:])


def test_random_netlists_keep_their_function():
    rng = random.Random(7)
    for _ in range(60):
        m = rand_module(rng)
        vecs = list(itertools.product((0, 1), repeat=7))
        before = [evaluate(m, v) for v in vecs]
        D.optimize(m)
        assert [evaluate(m, v) for v in vecs] == before
        assert all(c['type'] in F or c['type'] in ('$_NOT_', '$_MUX_') for c in m['cells'].values())


def test_serial_chain_becomes_a_tree_and_late_leaf_joins_last():
    # y = ((((a|b)|c)|d)|...) 16 leaves in series, then AND with a late signal
    cells = {}; prev = 2
    for k in range(15):
        cells[f'o{k}'] = cell('$_OR_', 100 + k, A=prev, B=3 + k); prev = 100 + k
    m = module(cells, range(2, 18), [prev])
    assert max(D.ff_depths(D.Net(m), D.UNIT)) == 15
    D.optimize(m)
    assert max(D.ff_depths(D.Net(m), D.UNIT)) == 4
    rng = random.Random(1)
    for _ in range(200):
        v = [rng.randint(0, 1) for _ in range(16)]
        assert evaluate(m, v) == [int(any(v))]
    assert evaluate(m, [0] * 16) == [0]


def test_de_morgan_cone_and_mixed_polarity():
    # y = ~(a | ~(b & c) | d) & e  = ~a & b & c & ~d & e : one AND tree over 5 literals after the pass
    cells = {'a1': cell('$_AND_', 20, A=3, B=4), 'n1': cell('$_NOT_', 21, A=20), 'o1': cell('$_OR_', 22, A=2, B=21),
             'o2': cell('$_OR_', 23, A=22, B=5), 'n2': cell('$_NOT_', 24, A=23), 'a2': cell('$_AND_', 25, A=24, B=6)}
    m = module(cells, range(2, 7), [25])
    D.optimize(m)
    assert not any(c['type'] == '$_NOT_' for c in m['cells'].values())
    for v in itertools.product((0, 1), repeat=5):
        a, b, c, d, e = v
        assert evaluate(m, v) == [(1 ^ a) & b & c & (1 ^ d) & e]
    assert max(D.ff_depths(D.Net(m), D.UNIT)) == 3


def test_shared_nets_and_flops_are_kept():
    # t = a & b is read twice: it stays one net; the flop is untouched
    cells = {'t': cell('$_AND_', 20, A=2, B=3), 'u': cell('$_AND_', 21, A=20, B=4), 'w': cell('$_OR_', 22, A=20, B=5),
             'ff': {'type': '$_DFF_PN0_', 'connections': {'C': [9], 'D': [21], 'Q': [30], 'R': [8]},
                    'port_directions': {'C': 'input', 'D': 'input', 'Q': 'output', 'R': 'input'}}}
    m = module(cells, [2, 3, 4, 5, 8, 9], [22, 30])
    D.optimize(m)
    assert m['cells']['ff']['connections'] == {'C': [9], 'D': [21], 'Q': [30], 'R': [8]}
    drv = {c['connections']['Y'][0] for c in m['cells'].values() if 'Y' in c['connections']}
    assert {20, 21, 22} <= drv
