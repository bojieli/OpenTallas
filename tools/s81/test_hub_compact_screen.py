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
