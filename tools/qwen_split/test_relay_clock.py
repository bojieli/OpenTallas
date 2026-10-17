import copy
import pytest
from qwen_split.relay_clock import assigned_clock


def fixture():
    return dict(relay_clock_by_bus={'serdes0_rxv': 'clk_ucie'}, buses=[
        ('clk_ucie', 'clock_trunk', 1, [('clk_rx', 'pll_ucie'),
         ('io_collective', 'fdi_ck'), ('io_serdes', 'clk')])])


def test_retained_native_serdes_relay_uses_actual_fdi_root():
    assert assigned_clock(fixture(), 'serdes0_rxv', 'coll_fdi') == 'clk_ucie'
    assert assigned_clock(fixture(), 'ordinary_serial_bus', 'sequencer') is None


@pytest.mark.parametrize('change', ['absent', 'duplicate', 'data', 'root', 'sink', 'alias'])
def test_stale_or_invented_clock_is_rejected(change):
    m = copy.deepcopy(fixture())
    if change == 'absent': m['buses'] = []
    if change == 'duplicate': m['buses'] *= 2
    if change == 'data': m['buses'][0] = ('clk_ucie', 'data', 1, m['buses'][0][3])
    if change == 'root': m['buses'][0][3].remove(('clk_rx', 'pll_ucie'))
    if change == 'sink': m['buses'][0][3].remove(('io_collective', 'fdi_ck'))
    if change == 'alias': m['relay_clock_by_bus']['serdes0_rxv'] = 'clk_coll'
    with pytest.raises(ValueError): assigned_clock(m, 'serdes0_rxv', 'coll_fdi')


def test_explicit_fdi_clock_cannot_reclock_serial_logic():
    with pytest.raises(ValueError): assigned_clock(fixture(), 'serdes0_rxv', 'sequencer')


from qwen_split.relay_clock import collective_core_clock


def core_fixture():
    return dict(buses=[('clk_coll', 'clock_trunk', 1, [('clk_rx', 'pll_coll'), ('io_collective', 'clk'),
                                                        ('io_collective', 'face_ck0')])])


def test_collective_fault_relay_uses_core_trunk():
    eps = [('io_collective', 'fault'), ('sys_face', 'io_fault')]
    assert collective_core_clock(core_fixture(), 'sf_io_fault', 'spine_local', eps) == 'clk_coll'
    eps = [('bump_pkg_s0', 'o'), ('io_collective', 'pkg_s__0_0')]
    assert collective_core_clock(core_fixture(), 'sf_strap_bump_pkg_s0', 'spine_local', eps) == 'clk_coll'


@pytest.mark.parametrize('change', ['no_coll', 'fdi_port', 'fdi_cls', 'absent', 'root', 'sink'])
def test_collective_core_clock_fails_closed(change):
    m = core_fixture(); eps = [('io_collective', 'fault'), ('sys_face', 'io_fault')]; cls = 'spine_local'
    if change == 'no_coll': eps = [('seq_su', 'x'), ('sys_face', 'y')]
    if change == 'fdi_port': eps = [('io_collective', 'shared_tx'), ('io_ucie', 'tx_flit')]
    if change == 'fdi_cls': cls = 'coll_fdi'
    if change == 'absent': m['buses'] = []
    if change == 'root': m['buses'][0][3].remove(('clk_rx', 'pll_coll'))
    if change == 'sink': m['buses'][0][3].remove(('io_collective', 'clk'))
    with pytest.raises(ValueError): collective_core_clock(m, 'b', cls, eps)
