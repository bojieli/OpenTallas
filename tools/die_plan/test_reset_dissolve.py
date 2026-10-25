"""Reset ancestry must expose structural wrappers without opening physical cores."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reset_dissolve as R
import bind_elab as E


def test_ancestor_stops_at_other_hard_cores_and_skips_unrelated():
    graph = {'top': {'parent', 'other'}, 'parent': {'core'}, 'other': {'foreign'},
             'core': set(), 'foreign': {'core'}}
    assert R.ancestors(graph, {'core'}, {'core', 'foreign'}) == {'top', 'parent'}


def test_two_paths_expose_both_parents_but_never_reset_core_itself():
    graph = {'a': {'core'}, 'b': {'c'}, 'c': {'core'}, 'core': {'private'}}
    assert R.ancestors(graph, {'core'}, {'core'}) == {'a', 'b', 'c'}


def test_string_parameter_staging_preserves_defaults_and_original(tmp_path):
    f = tmp_path/'src.sv'
    original = 'module foo #(parameter string LABEL="abc", parameter N=7)();\nlocalparam string X="001";\nendmodule\n'
    f.write_text(original)
    files, rec = E.string_parameter_compat([str(f)], tmp_path/'stage')
    assert f.read_text() == original
    text = Path(files[0]).read_text()
    assert 'parameter LABEL="abc"' in text and 'localparam X="001"' in text
    assert len(rec) == 1 and rec[0]['original'] == str(f)
    unchanged = tmp_path/'plain.sv'; unchanged.write_text('module bar; endmodule\n')
    assert E.string_parameter_compat([str(unchanged)], tmp_path/'stage') == ([str(unchanged)], [])


def test_wavefront_reset_matches_entire_nested_instance_suffix(tmp_path):
    import pytest
    from types import SimpleNamespace
    import bind
    from test_bind_wavefront import emitter, plan
    raw = plan()
    raw['partition_types']['src']['hard_cores'] = [dict(inst='u_r0.u_e0', module='real_core',
        origin_um=[50, 50], outline_um=[200, 300],
        pins=[dict(name='rst_n', layer='M4', xy=[0, 150])])]
    b = emitter(raw)
    part = next(p for p in b.parts if b.parts[p]['type'] == 'src')
    c = SimpleNamespace(path='die.frame.u_r0.u_e0', ports={'rst_n': [1]}, module='real_core', params={})
    b.F.cells = [c]
    b.G.dirs = {0: {'rst_n': 'input'}}
    b.G.kind = ['leaf']
    b.members[part] = [0]
    b.sinks = {(0, 'rst_n', 0): ('rst', 'low')}
    b.rel_of = lambda ci: 'u_e0'
    text, _ = b.emit_type('src', part)
    import reset_tree as RT
    target, = RT.for_type(b.wavefront_plan(), 'src')['core_resets']
    assert f'.rst_n(rst_n_t{target["tap"]})' in text
    # A second frame with the same nested suffix cannot choose one arbitrarily.
    b.F.cells.append(SimpleNamespace(path='die.other.u_r0.u_e0', ports={'rst_n':[2]},module='real_core',params={}))
    b.G.dirs[1] = {'rst_n': 'input'}
    b.sinks[(1,'rst_n',0)] = ('rst','low')
    b.members[part].append(1)
    with pytest.raises(bind.BindError, match='expected one bound leaf, found 2'):
        b.emit_type('src', part)
