"""Planning must preserve disconnected demand and identify the actual cut users."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hub_compact_screen as screen


def test_disconnected_route_is_not_zero_length_success():
    grid = (0, 3, 3)
    wall = {(1, y) for y in range(3)}
    assert screen.astar((0, 1), (2, 1), grid, wall, {}, 10) is None
    assert screen.astar((0, 1), (0, 1), grid, wall, {}, 10) == []
    assert len(screen.astar((0, 0), (2, 0), grid, set(), {}, 10)) == 2


def test_cut_report_keeps_incident_flow_and_unrouted_demand(monkeypatch):
    rects = {'a': (100, 100, 100, 100), 'b': (900, 100, 100, 100)}
    row = dict(a='a', b='b', bits=500, len_um=800, faces=['E', 'W'])
    monkeypatch.setattr(screen, 'astar', lambda *a: None)
    result, _, _ = screen.congestion(rects, [row], [], [0, 2000], {})
    assert not result['routing_complete']
    assert result['unrouted_bits'] == 500
    assert result['unrouted_bundles'] == 2
    assert result['unrouted'][0]['flow'] == 'a->b'
    monkeypatch.setattr(screen, 'astar', lambda *a: [(1, 1, 'h')])
    result, _, _ = screen.congestion(rects, [row], [], [0, 2000], {})
    assert result['routing_complete']
    assert result['hot_edges'][0]['bits'] == 500
    assert result['hot_edges'][0]['contributors'] == [dict(flow='a->b', bits=500)]


def test_source_census_does_not_drop_unknown_or_multiterminal_demand():
    def inst(n, kind='hub'):
        return [n, 'master', kind, '', '', 0, 0, 100, 100, 'R0']
    model = dict(insts=[inst('a'), inst('b'), inst('c'), inst('r', 'stn')], buses=[
        ['clk', 'clock', 1, [['a', 'ck'], ['b', 'ck']]],
        ['unknown', 'hub', 13, [['a', 'x'], ['missing', 'y']]],
        ['ab', 'hub', 5, [['a', 'x'], ['b', 'y']]],
        ['ar', 'hub', 7, [['a', 'x'], ['r', 'i']]],
        ['rb', 'hub', 7, [['r', 'o'], ['b', 'y']]],
        ['rc', 'hub', 7, [['r', 'o'], ['c', 'y']]],
    ])
    coverage = {}
    screen.flows_of(model, coverage)
    assert coverage['source_buses'] == 6
    assert coverage['excluded_nondatapath_buses'] == 1
    assert coverage['missing_endpoint_buses'][0]['bits'] == 13
    assert coverage['eligible_buses'] == 4
    assert sum(coverage[k] for k in ('transport_buses', 'direct_hub_buses', 'direct_other_buses')) == 4
    assert coverage['unsupported_hub_components'][0]['hubs'] == ['a', 'b', 'c']
