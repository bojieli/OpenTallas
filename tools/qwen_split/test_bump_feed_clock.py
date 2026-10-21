import copy
from types import SimpleNamespace as N

import pytest
from qwen_split.bump_feed_clock import bind_source, source_clock


def fixture():
    return dict(insts=[N(name=n, master=m) for n, m in [
        ('bump_fwd_epoch', 'qfd_sigbump'), ('bump_fwd_lrst', 'qfd_sigbump'),
        ('ckb_rom', 'qfd_ckbump'), ('clk_rx', 'qfd_clkrx')]],
        buses=[('pll_fwd', 'clock_trunk', 1, [('ckb_rom', 'pll_ck'), ('clk_rx', 'pll_fwd')])])


@pytest.mark.parametrize('kind,port', [('epoch', 'fwd_epoch'), ('lrst', 'fwd_link_rst_n')])
@pytest.mark.parametrize('suffix', ['', '__fo1'])
def test_only_actual_static_bumps_use_the_incoming_feed(kind, port, suffix):
    lane = dict(bid=f'lnk_fwd_{kind}{suffix}', src_ck='clk_r55')
    assert bind_source(fixture(), lane, [(f'bump_fwd_{kind}', 'o'), ('d2d_rom', port)])
    assert lane['src_ck'] == 'pll_fwd'
    assert lane['source_feed_contract']['physical_qualification_eligible'] is False
    assert len(lane['source_feed_contract']['owed']) == 2


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'width', 'data', 'root', 'sink', 'master', 'reverse'])
def test_stale_or_wrong_feed_fails_closed(change):
    m = fixture()
    eps = [('bump_fwd_epoch', 'o'), ('d2d_rom', 'fwd_epoch')]
    if change == 'missing': m['buses'] = []
    if change == 'duplicate': m['buses'] *= 2
    if change == 'width': m['buses'][0] = ('pll_fwd', 'clock_trunk', 2, m['buses'][0][3])
    if change == 'data': m['buses'][0] = ('pll_fwd', 'data', 1, m['buses'][0][3])
    if change == 'root': m['buses'][0][3][0] = ('other_bump', 'pll_ck')
    if change == 'sink': m['buses'][0][3][1] = ('clk_rx', 'other')
    if change == 'master': m['insts'][0].master = 'stand_in'
    if change == 'reverse': eps.reverse()
    with pytest.raises(ValueError): source_clock(m, 'lnk_fwd_epoch', eps)


def test_other_bumps_unchanged():
    lane = dict(bid='sf_strap_bump_pkg_s0', src_ck='clk_coll')
    prior = copy.deepcopy(lane)
    assert not bind_source(fixture(), lane, [('bump_pkg_s0', 'o'), ('io_collective', 'pkg_s0')])
    assert lane == prior


def test_region_reconstruction_preserves_feed_hop0():
    import qwen_rom_fulldie_b3r2 as G
    m = fixture()
    for i in m['insts']:
        i.x, i.y, i.w, i.h = 10, 10, 10, 10
    m['insts'] += [N(name=n, master='block', x=x, y=10, w=10, h=10)
                   for n, x in [('src', 10), ('dst', 5100), ('h0', 10), ('land', 5100)]]
    m.update(clock_regions=[dict(name='W', rect=[0, 0, 5000, 2000]),
                            dict(name='E', rect=[5000, 0, 10000, 2000])], b3r2={},
             ck_follow={('land', 'ck'): 'dst'})
    m['buses'][0][3].append(('h0', 'ck'))
    m['buses'] += [('clk_r0', 'clock_trunk', 1, [('clk_rx', 'pll_r0'), ('src', 'ck')]),
                   ('clk_r1', 'clock_trunk', 1, [('clk_rx', 'pll_r1'), ('dst', 'ck'), ('land', 'ck')])]
    G._regions_from_placement(m)
    actual = {(i, p): b for b, _, _, es in m['buses'] for i, p in es}
    assert actual['h0', 'ck'] == 'pll_fwd'
    assert actual['land', 'ck'] == actual['dst', 'ck']


def test_epoch_fanout_to_sys_face_anchor():
    # QW-GEN5: lnk_fwd_epoch__fo1 ends on sys_face.fwd_epoch (the run anchor), an actual static-link capture
    lane = dict(bid='lnk_fwd_epoch__fo1', src_ck='clk_r55')
    assert bind_source(fixture(), lane, [('bump_fwd_epoch', 'o'), ('sys_face', 'fwd_epoch')])
    with pytest.raises(ValueError):
        source_clock(fixture(), 'lnk_fwd_lrst', [('bump_fwd_lrst', 'o'), ('sys_face', 'fwd_epoch')])
