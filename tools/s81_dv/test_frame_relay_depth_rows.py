"""S81-D8E-LAT 11-18: relay_depth rows on a master's band types are visible to the frame schedule check."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'layer_prog')]
import frame_schedule_asb as F


def plan():
    parts = [dict(name=f'{f}{k}', type=f'col_h9_r{k}__t{f}') for f in ('a', 'b') for k in range(3)]
    types = {p['type']: {} for p in parts}
    types['col_h9_r2__ta']['relay_depth'] = [dict(inst='u_y_rt_20a_3', port='o', D=2)]
    types['col_h9_r1__tb']['relay_depth'] = [dict(inst='u_e3', port='xs_a', side='sink', bits=[0, 31], D=1)]
    types['col_h10_r0__tz'] = dict(relay_depth=[dict(inst='u_y_rt_1', port='o', D=1)])
    return dict(partitions=parts, partition_types=types)


def test_master_rows_only():
    rows = F.relay_depth_rows(plan(), 'col_h9')
    assert [(t, r['D']) for t, r in rows] == [('col_h9_r1__tb', 1), ('col_h9_r2__ta', 2)]
    assert F.relay_depth_rows(plan(), 'col_h10') == [('col_h10_r0__tz', plan()['partition_types']['col_h10_r0__tz']['relay_depth'][0])]


def test_frame_instance_rows():
    assert [t for t, _ in F.relay_depth_rows(plan(), 'col_h9', {'a0', 'a1', 'a2'})] == ['col_h9_r2__ta']
    assert F.relay_depth_rows(dict(partitions=plan()['partitions'], partition_types={}), 'col_h9') == []


def test_main_reports_unscheduled_rows():
    src = (HERE / 'frame_schedule_asb.py').read_text()
    assert 'RELAY_DEPTH_UNSCHEDULED' in src and "relay_depth_rows=len(rd_rows)" in src


def _frame():
    """u_cf.xa[0] -> relay u_y_a (1 flop) -> node n3.a;  u_cf.xa[1] -> station u_t0 (1 flop) -> n3.b, and -> u_o (1 flop) -> n4.a"""
    ff = lambda d, q: dict(type='$dff', port_directions=dict(D='input', Q='output', CLK='input'), connections=dict(D=[d], Q=[q], CLK=[9]))
    bb = lambda typ, ins, outs: dict(type=typ, port_directions={**{k: 'input' for k in ins}, **{k: 'output' for k in outs}},
                                     connections={**ins, **outs})
    cells = {'u_r0.u_cf': bb('dsfd_cfifo_crs4', dict(ri=[8]), dict(xa=[2, 3])),
             'u_r0.u_y_a.r': ff(2, 4), 'u_r0.u_t0__payload.r': ff(3, 5), 'u_r0.u_o.r': ff(3, 6),
             'u_r0.u_n3': bb('dsfd_node_NNfu', dict(a=[4], b=[5]), dict(o=[10])),
             'u_r0.u_n4': bb('dsfd_node_NNfu', dict(a=[6]), dict(o=[11]))}
    nets = {'u_r0.u_y_a.o': dict(bits=[4]), 'u_r0.u_t0__payload.i': dict(bits=[3]), 'u_r0.u_cf.xa': dict(bits=[2, 3])}
    return dict(modules=dict(top=dict(cells=cells, netnames=nets, ports=dict(clk=dict(direction='input', bits=[9])))))


def test_schedule_relay_depth_rows_as_stages():
    """--schedule-relay-depth: a relay row delays the relay output, a station sink row only that station's loads, an end-point
    sink row that pin; leaf names with or without the content instance; rows that differ between types are refused"""
    m0 = F.measure(_frame(), 'top')
    assert m0['nodes'] == {'n3': {'a': [('cf.xa', 1)], 'b': [('cf.xa', 1)]}, 'n4': {'a': [('cf.xa', 1)]}}
    rows = [('col_h9_r0__ta', dict(inst='u_r0_u_y_a', port='o', D=2)),
            ('col_h9_r0__ta', dict(inst='u_r0_u_t0_payload', port='i', side='sink', bits=[0, 0], D=1)),
            ('col_h9_r0__tb', dict(inst='u_y_a', port='o', D=2)),
            ('col_h9_r0__tb', dict(inst='u_t0_payload', port='i', side='sink', bits=[0, 0], D=1))]
    ex = F.relay_depth_extra(rows, 'col_h9')
    assert ex == {'u_r0': {('u_y_a', 'o', 'relay', 0, None): 2, ('u_t0_payload', 'i', 'sink', 0, 0): 1}}
    m1 = F.measure(_frame(), 'top', None, ex)
    assert m1['nodes'] == {'n3': {'a': [('cf.xa', 3)], 'b': [('cf.xa', 2)]}, 'n4': {'a': [('cf.xa', 1)]}}
    ex2 = F.relay_depth_extra([('col_h9_r0__ta', dict(inst='u_n3', port='b', side='sink', bits=[0, 0], D=1))], 'col_h9')
    assert F.measure(_frame(), 'top', None, ex2)['nodes']['n3'] == {'a': [('cf.xa', 1)], 'b': [('cf.xa', 2)]}
    assert F.measure(_frame(), 'top')['nodes'] == m0['nodes']                   # nothing left behind
    import pytest
    with pytest.raises(ValueError, match='differ between its types'):
        F.relay_depth_extra(rows[:2] + [('col_h9_r0__tb', dict(inst='u_y_a', port='o', D=1))], 'col_h9')
    with pytest.raises(ValueError, match='no such instance'):
        F.measure(_frame(), 'top', None, F.relay_depth_extra([('col_h9_r0__ta', dict(inst='u_nope', port='o', D=1))], 'col_h9'))
