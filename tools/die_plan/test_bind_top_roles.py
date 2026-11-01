"""Explicit die controls use physical delivery; undeclared data stays an obligation."""
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace as N
import sys

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind
import reset_tree as RT
from test_bind_wavefront import emitter, plan


def graph(roles, ports=None):
    flat = N(cells=[], const_drivers={}, top_ports=ports or {
        'native_required_ctrl_rst_n': ('input', [1]),
        'programme_words': ('input', [2]), 'package_clk': ('input', [3])})
    return bind.Graph(flat, bind.Rules(roles), [])


def test_declared_top_reset_and_clock_keep_data_external():
    g = graph({'resets': [{'pin': r'@die\.native_required_.*_rst_n', 'polarity': 'low'}],
               'clocks': [{'pin': r'@die\.package_clk', 'domain': 'core'}]})
    assert g.source(1) == ('reset', 'low', 0)
    assert g.source(3) == ('clock', 'core')
    assert g.source(2) == ('top', 'programme_words', 0, 0)


def test_missing_role_mutant_retains_unresolved_reset():
    # Removing the role must be detected; it cannot silently produce a reset.
    assert graph({}).source(1) == ('top', 'native_required_ctrl_rst_n', 0, 0)
    assert graph({}).source(1) != graph({'resets': [
        {'pin': r'@die\.native_required_.*_rst_n', 'polarity': 'low'}]}).source(1)


@pytest.mark.parametrize('roles,ports,error', [
    ({'resets': [{'pin': r'@die\.x'}], 'clocks': [{'pin': r'@die\.x'}]},
     {'x': ('input', [1])}, 'TOP_ROLE_CONFLICT'),
    ({'resets': [{'pin': r'@die\.x'}]}, {'x': ('input', [1, 2])}, 'TOP_ROLE_WIDTH'),
    ({'resets': [{'pin': r'@die\.x', 'polarity': 'other'}]},
     {'x': ('input', [1])}, 'TOP_RESET_POLARITY'),
])
def test_invalid_top_control_roles_fail_closed(roles, ports, error):
    with pytest.raises(bind.BindError, match=error):
        graph(roles, ports).source(1)


def test_native_reset_role_reaches_the_existing_planned_core_tap():
    raw = plan()
    raw['partition_types']['src']['hard_cores'] = [dict(inst='u_hc', module='actual_core',
        origin_um=[50, 50], outline_um=[200, 300],
        pins=[dict(name='rst_n', layer='M4', xy=[0, 150])])]
    b = emitter(raw)
    part = next(p for p in b.parts if b.parts[p]['type'] == 'src')
    c = N(path='controller', module='actual_core', ports={'rst_n': [1]},
          dirs={'rst_n': 'input'}, params={}, kind='leaf')
    b.F = N(cells=[c], const_drivers={},
            top_ports={'native_required_ctrl_rst_n': ('input', [1])})
    b.G = bind.Graph(b.F, bind.Rules({'resets': [
        {'pin': r'@die\.native_required_.*_rst_n', 'polarity': 'low'}]}), [])
    b.members[part] = [0]
    b.rel_of = lambda ci: 'u_hc'
    b.reset_age = defaultdict(list)
    b.sinks = {(0, 'rst_n', 0): b._classify(part, 0, 'rst_n', 0,
                                        b.G.source(1), defaultdict(int))}
    text, _ = b.emit_type('src', part)
    target, = RT.for_type(b.wavefront_plan(), 'src')['core_resets']
    assert f'.rst_n(rst_n_t{target["tap"]})' in text
    assert 'io_native_required_ctrl_rst_n' not in text
