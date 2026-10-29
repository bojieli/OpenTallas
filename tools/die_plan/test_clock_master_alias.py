"""Actual ctree output assigns must retain every clock path master."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_sta_related as D

INV = 'CKINVDCx16_ASAP7_75t_R'
BUF = 'BUFx24_ASAP7_75t_R'


def netlist(tmp_path, assign='assign t_b = pad;', master=BUF):
    (tmp_path / 'ctree.v').write_text('\n'.join([
        'module ctree (root, t_a, t_b);', 'input root;', 'output t_a;', 'output t_b;',
        f'  {INV} b0 (.A(root), .Y(n0));',
        f'  {INV} b1 (.A(n0), .Y(n1));',
        f'  {master} p1_t_b_0 (.A(n1), .Y(pad));',
        '  assign t_a = n1;', assign, 'endmodule']) + '\n')


def test_generated_ctree_assigns_retain_buffer_master(tmp_path):
    netlist(tmp_path)
    assert D.netlist_tap_masters(tmp_path) == {'t_a': [INV], 't_b': sorted([INV, BUF])}
    taps = {'t_b': dict(late_ps=100., early_ps=80.)}
    _, scaled = D.apply_clock_cal({}, taps, 'TT', 'inv', 'spice_cell', proof=tmp_path)
    assert scaled['t_b']['late_ps'] == pytest.approx(100*max(D.SPICE_CLOCK_CAL_CELL[m]['TT']['rise_late']
                                                         for m in (INV, BUF)))
    assert scaled['t_b']['late_ps'] != pytest.approx(100*D.SPICE_CLOCK_CAL_CELL[INV]['TT']['rise_late'])


def test_chained_alias_in_cell_input_is_traced(tmp_path):
    netlist(tmp_path, 'assign alias0 = pad;\nassign t_b = alias0;')
    p = tmp_path / 'ctree.v'
    p.write_text(p.read_text().replace('.A(n1), .Y(pad)', '.A(parent_alias), .Y(pad)')
                 .replace('endmodule', 'assign parent_alias = n1;\nendmodule'))
    assert D.netlist_tap_masters(tmp_path)['t_b'] == sorted([INV, BUF])


def test_unknown_master_behind_assign_never_defaults_to_inverter(tmp_path):
    netlist(tmp_path, master='UNMEASURED_CLK')
    with pytest.raises(D.ClockMasterUncalibrated, match='no spice factor'):
        D.apply_clock_cal({}, {'t_b': dict(late_ps=100., early_ps=80.)}, 'TT', 'inv', 'spice_cell', proof=tmp_path)


@pytest.mark.parametrize('assign', ['assign t_b = absent;', 'assign t_b = alias0;\nassign alias0 = t_b;'])
def test_unresolved_or_cyclic_alias_fails_closed(tmp_path, assign):
    netlist(tmp_path, assign)
    with pytest.raises(D.ClockMasterUncalibrated):
        D.netlist_tap_masters(tmp_path)
