import sys
from pathlib import Path

import pytest

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import die_sta_libs as D


def test_actual_divider_and_phy_output_directions_required(tmp_path):
    die = tmp_path/'die.v'
    die.write_text('module die();\nwire a,b;\nqfd_ckdiv6 div (.blk_o(a));\n'
                   'ot_qfd_ucie_x64_phy phy (.lclk(b));\nendmodule\n')
    dirs = {'qfd_ckdiv6': {'blk_o':'output'}, 'ot_qfd_ucie_x64_phy': {'lclk':'output'}}
    drivers, _, _ = D.clock_connections(die, dirs, {})
    assert drivers == {'a':['div/blk_o'], 'b':['phy/lclk']}
    D.validate_clock_drivers(drivers, {'a','b'})
    dirs['qfd_ckdiv6']['blk_o'] = 'input'
    with pytest.raises(ValueError, match='actual output'): D.clock_connections(die, dirs, {})


@pytest.mark.parametrize('expr', ["1'b0", '', 'unknown', 'a[1:0]'])
def test_clock_source_scalar_declared_net_required(tmp_path, expr):
    die = tmp_path/'die.v'
    die.write_text(f'module die();\nwire [1:0] a;\nqfd_ckdiv6 div (.blk_o({expr}));\nendmodule\n')
    with pytest.raises(ValueError):
        D.clock_connections(die, {'qfd_ckdiv6': {'blk_o':'output'}}, {})


@pytest.mark.parametrize('drivers', [{}, {'a':[]}, {'a':['x/p','y/p']}, {'a':['x/p','x/p']}])
def test_unknown_or_multi_source_clock_refused(drivers):
    with pytest.raises(ValueError, match='unknown or multiple'): D.validate_clock_drivers(drivers, {'a'})


def test_real_unrecognized_data_output_cannot_share_clock_source(tmp_path):
    die = tmp_path/'die.v'
    die.write_text('module die();\nwire a;\nqfd_ckdiv6 div (.blk_o(a));\ndata other (.payload(a));\nendmodule\n')
    with pytest.raises(ValueError, match='actual output drivers'):
        D.clock_connections(die, {'qfd_ckdiv6': {'blk_o':'output'}, 'data': {'payload':'output'}}, {})
