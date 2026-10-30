"""Post-compose cut bridges must create drivers before Graph reads the netlist."""
import sys
import types
import pytest
import bind as B


class GraphReached(Exception):
    pass


def test_post_compose_bridge_driver_visible_at_graph(tmp_path, monkeypatch):
    events = []
    def compose(binder, descriptor):
        events.append('compose')
        binder.created_cut_net = binder.F.new(1)
    def bridge(binder, descriptor, base):
        events.append('bridge')
        assert descriptor == ['exact-native-source'] and base == str(tmp_path)
        binder.F.const_drivers[binder.created_cut_net] = ('0', 'source_bridge.y')
        return [{'expanded': 'native_cut'}]
    def graph(flat, rules, errors):
        events.append('graph')
        assert flat.const_drivers == {0: ('0', 'source_bridge.y')}
        raise GraphReached
    monkeypatch.setitem(sys.modules, 'bind_compose', types.SimpleNamespace(apply=compose))
    monkeypatch.setitem(sys.modules, 'structural_bridge', types.SimpleNamespace(apply=bridge))
    monkeypatch.setattr(B, 'Graph', graph)
    plan = {'asbuilt': {'top': 'top', 'compose': 'cut-plan',
                        'structural_bridges': ['exact-native-source']}}
    netlist = {'modules': {'top': {'ports': {}, 'cells': {}, 'netnames': {}}}}
    with pytest.raises(GraphReached):
        B.Binder(plan, netlist, tmp_path, base=str(tmp_path))
    assert events == ['compose', 'bridge', 'graph']


def test_default_never_loads_or_expands_bridges(tmp_path, monkeypatch):
    def forbidden(*args):
        raise AssertionError('default binding invoked structural bridge')
    monkeypatch.setitem(sys.modules, 'structural_bridge', types.SimpleNamespace(apply=forbidden))
    def graph(flat, rules, errors):
        assert flat.const_drivers == {} and flat.cells == []
        raise GraphReached
    monkeypatch.setattr(B, 'Graph', graph)
    plan = {'asbuilt': {'top': 'top'}}
    netlist = {'modules': {'top': {'ports': {}, 'cells': {}, 'netnames': {}}}}
    with pytest.raises(GraphReached):
        B.Binder(plan, netlist, tmp_path, base=str(tmp_path))
