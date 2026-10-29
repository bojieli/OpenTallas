"""Declared infrastructure clock arcs cannot waive an undeclared data path."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geom_rules as G


def vehicle(tmp_path):
    p = tmp_path / 'geom.tsv'
    p.write_text('D\t0\t0\t100\t100\n'
                 'C\t1\tB\tBUFx24_ASAP7_75t_R\t10\t10\t11\t11\tft0\n'
                 'C\t2\tS\tDFFHQNx1_ASAP7_75t_R\t20\t20\t21\t21\tff\n'
                 'P\t0\tft_ck_i_0\tINPUT\tSIGNAL\tM5\t0\t10\n'
                 'P\t1\tft_ck_o_0\tOUTPUT\tSIGNAL\tM5\t100\t10\n'
                 'P\t2\tdata\tINPUT\tSIGNAL\tM5\t0\t20\n'
                 'N\tSIGNAL\tp0\ti1\n'
                 'N\tSIGNAL\ti1\tp1\n'
                 'N\tSIGNAL\tp2\ti2\n')
    return G.Design(p), {'schema': 'opentallas.ft_interface_model.v1',
                          'arcs': [{'source': 'ft_ck_i_0', 'sink': 'ft_ck_o_0', 'kind': 'clock'}]}


def test_explicit_clock_arc_with_actual_buffer_cone(tmp_path):
    d, spec = vehicle(tmp_path)
    pins = G.clock_feedthrough_pins(d, spec)
    assert pins == {'ft_ck_i_0', 'ft_ck_o_0'}
    before = G.pin_reg_metrics(d, re.compile(r'^strap_'))
    after = G.pin_reg_metrics(d, re.compile(r'^strap_'), pins)
    assert before['pins_unregistered'] == 2 and after['pins_unregistered'] == 0


def test_undeclared_identical_names_remain_signal_pins(tmp_path):
    d, spec = vehicle(tmp_path)
    assert not G.clock_feedthrough_pins(d, {})
    spec['arcs'] = []
    assert not G.clock_feedthrough_pins(d, spec)
    assert G.pin_reg_metrics(d, re.compile(r'^strap_'))['pins_unregistered'] == 2


def test_reset_and_data_arcs_get_no_clock_exemption(tmp_path):
    d, spec = vehicle(tmp_path)
    for kind in ('reset', 'data', None):
        spec['arcs'][0]['kind'] = kind
        assert not G.clock_feedthrough_pins(d, spec)


def test_bad_endpoint_or_direction_is_rejected(tmp_path):
    d, spec = vehicle(tmp_path)
    spec['arcs'][0]['sink'] = 'absent'
    assert not G.clock_feedthrough_pins(d, spec)
    spec['arcs'][0]['sink'] = 'data'
    assert not G.clock_feedthrough_pins(d, spec)


def test_declared_clock_with_logic_or_data_fanout_is_rejected(tmp_path):
    d, spec = vehicle(tmp_path)
    d.nets[1][2].append(('i', 2, False))  # a real data D pin on the same cone
    assert not G.clock_feedthrough_pins(d, spec)
    d.nets[1][2].pop()
    d.cells[1] = ('L',) + d.cells[1][1:]  # arbitrary logic is not a clock repeater
    assert not G.clock_feedthrough_pins(d, spec)


def test_disconnected_and_cyclic_cones_are_rejected(tmp_path):
    d, spec = vehicle(tmp_path)
    d.nets[1][2].clear()
    assert not G.clock_feedthrough_pins(d, spec)
    d.nets[1][2].append(('i', 1, False))
    assert not G.clock_feedthrough_pins(d, spec)


def test_unused_buffer_load_does_not_turn_clock_into_data(tmp_path):
    d, spec = vehicle(tmp_path)
    d.cells[3] = ('B',) + d.cells[1][1:]
    d.cell_in[3] = [(0, False)]
    d.nets[0][2].append(('i', 3, False))
    assert G.clock_feedthrough_pins(d, spec) == {'ft_ck_i_0', 'ft_ck_o_0'}
