"""QW-GEN5: g5 structural clock sources (divider, UCIe PHY clock, centre core feed) on a minimal model."""
import os
from types import SimpleNamespace as N

import pytest
from qwen_rom_fulldie import Inst, Master
from qwen_split import g5_clocking as G
from qwen_split.bump_feed_clock import source_clock


def model():
    ins = [Inst('io_collective', 'qfd_collective_static_io_production', 0.0, 0.0, 1563.816, 4157.976),
           Inst('io_ucie', 'ot_qfd_ucie_x64_phy', 0.216, 5000.0, 777.6, 777.6, orient='MX'),
           Inst('clk_rx', 'qfd_clkrx', 1101.6, 21349.088, 412.536, 412.536),
           Inst('ckb_rom', 'qfd_ckbump', 1023.6, 24224.02, 43.176, 43.176),
           Inst('bump_fwd_epoch', 'qfd_sigbump', 1143.6, 24224.02, 43.176, 43.176)]
    col = Master('qfd_collective_static_io_production', 1563.816, 4157.976, 7, '')
    col.ports['blk_ck'] = ('pins', 2, 'E', 'M4', [2179.248, 2179.344], 1)
    phy = Master('ot_qfd_ucie_x64_phy', 777.6, 777.6, 5, '')
    phy.ports['clk'] = ('pins', 1, 'N', 'M5', [338.628], 1)
    phy.ports['lclk'] = ('pins', 1, 'N', 'M5', [338.58], 1)
    M = {q.name: q for q in (col, phy)}
    m = dict(insts=ins, buses=[
        ('clk_coll_blk', 'clock_trunk', 1, [('clk_rx', 'pll_coll_blk'), ('io_collective', 'blk_ck0'), ('io_collective', 'blk_ck1')]),
        ('clk_coll', 'clock_trunk', 1, [('clk_rx', 'pll_coll'), ('io_collective', 'clk')]),
        ('rst_io', 'reset', 1, [('rs_bump', 'rso'), ('io_collective', 'rst_n')]),
        ('clk_ucie', 'clock_trunk', 1, [('clk_rx', 'pll_ucie'), ('io_collective', 'fdi_ck0'), ('io_ucie', 'clk')]),
        ('pll_fwd', 'clock_trunk', 1, [('ckb_rom', 'pll_ck'), ('clk_rx', 'pll_fwd')])])
    v = N(Inst=Inst, Master=Master, masters=lambda m_, k=1: dict(M))
    return v, m


def run(env, mutate=None):
    v, m = model()
    if mutate:
        mutate(v, m)
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        return v, m, G.apply(v, m)
    finally:
        for k, x in old.items():
            os.environ.pop(k, None) if x is None else os.environ.__setitem__(k, x)


ALL = dict(OT_SPLIT_COLL_BLK_DIV='1', OT_SPLIT_UCIE_PHY_CLK='1', OT_SPLIT_CORE_FEED_XY='16848.0,12096.0',
           OT_SPLIT_FWD_BUMP_FEED='1')


def test_default_is_noop():
    v, m, r = run({k: '' for k in ('OT_SPLIT_COLL_BLK_DIV', 'OT_SPLIT_UCIE_PHY_CLK', 'OT_SPLIT_CORE_FEED_XY')})
    assert r is None and 'g5_clocking' not in m


def test_all_three_structural_sources():
    v, m, r = run(ALL)
    b = {x[0]: x for x in m['buses']}
    assert b['clk_coll_blk'][3][0] == ('ckdiv_coll_blk', 'ck_o')
    assert ('ckdiv_coll_blk', 'ck') in b['clk_coll'][3] and ('ckdiv_coll_blk', 'rst_n') in b['rst_io'][3]
    assert b['clk_ucie'][3][0] == ('io_ucie', 'lclk') and ('io_ucie', 'clk') in b['clk_ucie'][3]
    assert b['pll_core'][3] == [('ckb_core', 'pll_ck'), ('clk_rx', 'pll_fwd')]
    assert b['pll_fwd'][3] == [('ckb_rom', 'pll_ck')]
    # no receiver output is a non-stream clock any more
    assert not [e for x in m['buses'] for e in x[3] if e in (('clk_rx', 'pll_coll_blk'), ('clk_rx', 'pll_ucie'))]
    by = {i.name: i for i in m['insts']}
    d = by['ckdiv_coll_blk']
    assert abs(d.x - 1563.816) < 200 and abs(d.y - 2179.2) < 200            # beside the blk_ck pins
    assert 'qfd_ckdiv6' in v.masters(m) and set(v.masters(m)['qfd_ckdiv6'].ports) == {'ck', 'rst_n', 'ck_o'}
    assert r['core_feed']['xy'] == [16848.0, 12096.0]
    # the Codex hop-0 bump feed validator accepts the core-feed topology
    assert source_clock(m, 'lnk_fwd_epoch', [('bump_fwd_epoch', 'o'), ('d2d_rom', 'fwd_epoch')]) == 'pll_fwd'


@pytest.mark.parametrize('bad', ['lattice', 'overlap', 'no_bump_feed', 'no_lclk', 'stale_coll_blk', 'two_resets'])
def test_fails_closed(bad):
    env = dict(ALL)
    mut = None
    if bad == 'lattice':
        env['OT_SPLIT_CORE_FEED_XY'] = '16850.0,12096.0'
    if bad == 'overlap':
        env['OT_SPLIT_CORE_FEED_XY'] = '1123.2,21384.0'
    if bad == 'no_bump_feed':
        env['OT_SPLIT_FWD_BUMP_FEED'] = '0'
    if bad == 'no_lclk':
        def mut(v, m):
            M = v.masters(m)
            M['ot_qfd_ucie_x64_phy'].ports.pop('lclk')
            v.masters = lambda m_, k=1: dict(M)
    if bad == 'stale_coll_blk':
        def mut(v, m):
            m['buses'][0] = ('clk_coll_blk', 'clock_trunk', 1, [('other', 'q'), ('io_collective', 'blk_ck0')])
    if bad == 'two_resets':
        def mut(v, m):
            m['buses'].append(('rst_x', 'reset', 1, [('a', 'b'), ('io_collective', 'rst_n')]))
    with pytest.raises(ValueError):
        run(env, mut)


def test_core_feed_validator_rejects_receiver_on_link_feed():
    v, m, r = run(ALL)
    j = next(k for k, x in enumerate(m['buses']) if x[0] == 'pll_fwd')
    m['buses'][j] = ('pll_fwd', 'clock_trunk', 1, [('ckb_rom', 'pll_ck'), ('clk_rx', 'pll_fwd')])
    with pytest.raises(ValueError):
        source_clock(m, 'lnk_fwd_epoch', [('bump_fwd_epoch', 'o'), ('d2d_rom', 'fwd_epoch')])
