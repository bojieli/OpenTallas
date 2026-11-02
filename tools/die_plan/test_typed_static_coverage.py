import copy
import pytest
from typed_static_coverage import classify, trace, native_inputs, native_cells


def fixture():
    cells = {
        'capture': {'master': 'DFFHQNx1_ASAP7_75t_R', 'ports': {'D': 'n', 'CLK': 'clk', 'QN': 'q'}},
        'buf': {'master': 'BUFx3_ASAP7_75t_R', 'ports': {'A': 'strap[0]', 'Y': 'n'}},
    }
    return cells, {'n': [('buf', 'Y')], 'q': [('capture', 'QN')]}


def test_off_is_inert_even_without_any_input_file():
    assert classify('/does/not/exist', 'none')['status'] == 'DISABLED'


def test_exact_strap_buffer_cone_is_classified():
    cells, drivers = fixture()
    assert trace(cells, drivers, 'capture', 'strap[0]')['buffer_path'] == ['buf']


@pytest.mark.parametrize('change', ['wrongpin', 'dynamic', 'sequential', 'extraenable', 'multiple', 'cycle', 'open'])
def test_other_cones_are_not_declared_static_straps(change):
    cells, drivers = fixture()
    if change == 'wrongpin': cells['buf']['ports']['A'] = 'strap[1]'
    elif change == 'dynamic': cells['buf']['ports']['A'] = 'data[0]'
    elif change == 'sequential': cells['buf']['master'] = 'DFFHQNx1_ASAP7_75t_R'
    elif change == 'extraenable': cells['buf']['ports']['B'] = 'enable'
    elif change == 'multiple': drivers['n'].append(('capture', 'QN'))
    elif change == 'cycle': cells['buf']['ports']['A'] = 'n'
    else: cells['capture']['ports']['D'] = ''
    with pytest.raises(ValueError): trace(cells, drivers, 'capture', 'strap[0]')


def test_wrong_input_manifest_digest_rejects_before_source_use(tmp_path):
    p = tmp_path/'input.json';p.write_text('{}')
    with pytest.raises(ValueError, match='manifest differs'):
        classify(p, '0'*64, enabled=True)


def test_native_wrong_direction_is_not_an_input():
    source='module top (strap);\n output [1:0] strap;\nendmodule\n'
    assert not native_inputs(source, 'top')
    assert native_inputs(source.replace('output', 'input'), 'top') == {'strap[0]', 'strap[1]'}


@pytest.mark.parametrize('lhs', ['strap', 'strap[0]', 'strap[1:0]', '{strap[0],other}'])
def test_behavioral_assign_is_a_driver_even_on_declared_input(lhs):
    source='module top (strap);\n input [1:0] strap;\n assign '+lhs+' = dynamic;\nendmodule\n'
    _, drivers=native_cells(source,'top')
    assert drivers['strap[0]'] == [('@behavioral_assign', 'Y')]
