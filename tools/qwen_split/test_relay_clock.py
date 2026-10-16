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
