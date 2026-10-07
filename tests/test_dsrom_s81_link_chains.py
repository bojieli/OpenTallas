"""Full-width link wiring tests; stub placement, retain the production net builder."""
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import dsrom_s81_fulldie as F


def link_model(monkeypatch, side, split, count, serdes=True):
    def inst(name, master='station512'):
        return SimpleNamespace(name=name, master=master, x=100., y=100., w=20., h=20.)

    coll = inst('collective', 'collective')
    lk = inst(f'lnk{side}1', 'serdes' if serdes else 'ucie')
    m = dict(geo=dict(x_sp=50., x_fe=500., ch_y=[0., 100., 200., 300.]),
             hub=dict(collective=coll), x_vch=200., links=[lk], insts=[coll, lk], buses=[])

    def add(it):
        m['insts'].append(it)
        return it

    placer = SimpleNamespace(add=add)
    chains = F.Chains(m, placer)
    chains.run = lambda name, *a, **kw: [
        (add(inst(f'{name}_{j}')), j, 0) for j in range(count if name.endswith('r') else 1)]
    monkeypatch.setattr(F, 'LINK_FIX', True)
    monkeypatch.setattr(F, 'LINK_SPLIT', split)
    monkeypatch.setattr(F, 'real_lef', lambda _: {'name': 'serdes'})
    monkeypatch.setattr(F, 'link_span_y', lambda *a: 110.)
    for fn in ('s14_x', 'vch_x', 'corr_y'):
        monkeypatch.setattr(F, fn, lambda *a: 150.)
    monkeypatch.setattr(F, '_hub_at', lambda p, name, *a: inst(name, 'hub_end'))
    monkeypatch.setattr(F, 'link_ck_relay', lambda m, p, lk, cor, nm, drv: inst(f'kc_{nm}', 'relay'))
    monkeypatch.setattr(F, '_split_stations', lambda p, ch, lk, nm, port, *a: [
        (add(inst(f'{nm}_{port}_{j}', 'station256')), 256*j, 256*j+255) for j in range(2)])
    F._link_chains(m, chains, placer, dict(edgeW=(0, 0, 50, 500), edgeE=(500, 0, 550, 500)),
                   lambda *a: ('hub_end', 20., 20.), None, 0.)
    return m, lk.name, f'hl_{side}1'


def trace_bits(m, source, sink):
    """Walk each bit through wires and identity station registers; reject missing/multiple drivers."""
    drivers = {}
    for _, cls, bits, eps in m['buses']:
        if cls != 'lane':
            continue
        expanded = []
        for inst, port in eps:
            base, lo, hi = F.pslice(port)
            lo = 0 if lo is None else lo
            expanded.append([(inst, base, lo + j) for j in range(bits)])
        for load in expanded[1:]:
            for dst, src in zip(load, expanded[0]):
                assert dst not in drivers, ('multiple drivers', dst)
                drivers[dst] = src
    for bit in range(512):
        node = (*sink, bit)
        seen = set()
        while node != (*source, bit):
            assert node not in seen, ('cycle', node)
            seen.add(node)
            if node[1] == 'do0':
                node = (node[0], 'di0', node[2])
            else:
                assert node in drivers, ('undriven', node)
                node = drivers[node]


@pytest.mark.parametrize('side', ['W', 'E'])
@pytest.mark.parametrize('split,serdes,count', [
    (False, True, 0), (False, True, 1), (False, True, 3),
    (True, True, 1), (True, True, 3), (True, False, 0), (True, False, 3)])
def test_all_512_rx_tx_bits_and_receive_clocks(monkeypatch, side, split, serdes, count):
    m, lk, end = link_model(monkeypatch, side, split, count, serdes)
    trace_bits(m, (lk, 'rx'), (end, 'di0'))
    trace_bits(m, ('collective', f'td{side}1'), (lk, 'tx'))
    clocks = defaultdict(list)
    for _, cls, _, eps in m['buses']:
        if cls == 'fclk':
            for ep in eps[1:]:
                clocks[ep].append(eps[0])
    for j in range(count):
        assert len(clocks[(f'K{side}1r_{j}', 'fi0')]) == 1
    assert len(clocks[(end, 'fi0')]) == 1
    if count:
        assert clocks[(end, 'fi0')] == [(f'K{side}1r_{count-1}', 'fo0')]
    for j in range(1, count):
        assert clocks[(f'K{side}1r_{j}', 'fi0')] == [(f'K{side}1r_{j-1}', 'fo0')]
    F.port_usage(m)  # catches direction and slice-width conflicts


def test_missing_split_tail_is_rejected(monkeypatch):
    m, lk, end = link_model(monkeypatch, 'W', True, 3)
    m['buses'] = [b for b in m['buses'] if b[0] != 'KW1r_de']
    with pytest.raises(AssertionError, match='undriven'):
        trace_bits(m, (lk, 'rx'), (end, 'di0'))


@pytest.mark.parametrize('k', [1, 16])
@pytest.mark.parametrize('reverse', [False, True])
def test_upper_slice_does_not_widen_unsliced_peer(k, reverse):
    endpoints = [('wide', 'data[256:511]'), ('half', 'data')]
    if reverse:
        endpoints.reverse()
    m = dict(insts=[SimpleNamespace(name=n, master=n) for n in ('wide', 'half')],
             buses=[('upper', 'lane', 256, endpoints)])
    assert F.port_widths(m, k) == {('wide', 'data'): 512 // k, ('half', 'data'): 256 // k}
