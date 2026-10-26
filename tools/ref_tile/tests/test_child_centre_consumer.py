"""Opt-in CCT shipping contract and compatibility of generated CTS hooks."""
import copy
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import clock_entry_constraints as CE
import ref_tile as RT
import test_landed_cluster_kit as K


def test_default_identity_and_hook_order(tmp_path, monkeypatch):
    K.view(tmp_path)
    spec = K.load(tmp_path, K.spec(tmp_path))
    monkeypatch.setattr(RT, 'ROOT', tmp_path)
    plain = RT.gen_hooks(spec, 'kit')
    explicit = copy.deepcopy(spec)
    explicit['child_centre_tap'] = None
    assert RT.gen_hooks(explicit, 'kit') == plain
    assert CE.child_centre_tcl(spec, tmp_path) == []
    assert 'child_centre_tap.tcl' not in plain['pre_cts.tcl']
    child_dir = tmp_path / spec['children'][0]['view']
    insertion = json.loads((child_dir / 'insertion.json').read_text())
    for corner in CE.CORNERS:
        insertion[corner]['boundary'].update(min=30, mean=40, max=50)
    (child_dir / 'insertion.json').write_text(json.dumps(insertion))
    spec['children'][0]['inst'] = 'hard'
    spec['child_centre_tap'] = {'children': ['hard'], 'why': 'Centre real child and soft boundary ranges.'}
    hook = RT.gen_hooks(spec, 'kit')['pre_cts.tcl']
    assert hook.index('clock_entries.tcl') < hook.index('child_centre_tap.tcl')
    assert hook.index('child_centre_tap.tcl') < hook.index('rename clock_tree_synthesis ::ot_ref_cts_boundary_orig')
    assert 'set ::ot_cct_children [dict create {hard} {tt {30 50} ff {30 50} ss {30 50}}]' in hook
    shipped = RT.referenced_paths(spec, 'kit')
    assert 'physical/common_flow/child_centre_tap.tcl' in shipped
    assert 'physical/common_flow/native_pg_binding.tcl' in shipped
    insertion['ff']['boundary'].pop('max')
    (child_dir / 'insertion.json').write_text(json.dumps(insertion))
    with pytest.raises(ValueError, match='ff boundary'):
        CE.child_centre_tcl(spec, tmp_path)


@pytest.mark.parametrize('change', [
    {'clock': 'spine'},
    {'child_centre_tap': {'children': ['unknown'], 'why': 'test'}},
    {'child_centre_tap': {'children': ['hard', 'hard'], 'why': 'test'}},
    {'child_centre_tap': {'children': ['hard'], 'why': ''}},
])
def test_invalid_optin_refused(tmp_path, change):
    spec = {'kind': 'cluster', 'clock': 'multiple_cts_roots', 'children': [],
            'child_centre_tap': {'children': ['hard'], 'why': 'test'}}
    spec.update(change)
    with pytest.raises(ValueError):
        CE.child_centre_tcl(spec, tmp_path)
