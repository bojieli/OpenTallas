import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from row_sites import graph_digest, transport


def fixture(tmp_path):
    spec = dict(instances=[dict(name='rf0000_k00_00_l0', master='hbfd_rly_48_WE', slot='actual_driver->actual_sink',
                               note='equal-age pad 1/1; lane row rf0000_k00_00 0/1 WE; site (0.0, 0.0) um')],
                clocks=[dict(inst='rf0000_k00_00_l0', port='ck', domain='stream', kind='clock'),
                        dict(inst='rf0000_k00_00_l0', port='rs', domain='stream', kind='reset')],
                edges=[dict(src=['actual_driver', 'data'], dst=['rf0000_k00_00_l0', 'i'], bits=48)],
                straps=[], relay_splice_v2=[{'stage_order': ['rf0000_k00_00_l0']}])
    source = tmp_path / 'source.json'
    source.write_text('immutable actual input')
    inputs = {'contract': str(source)}
    plan = tmp_path / 'plan.json'
    transport(spec, inputs, export=plan)
    return spec, inputs, plan


def mutate(path, fn):
    doc = json.loads(path.read_text()); fn(doc); path.write_text(json.dumps(doc))


def test_only_position_changes_and_all_clocks_resets_edges_stages_stay(tmp_path):
    spec, inputs, plan = fixture(tmp_path)
    original = copy.deepcopy(spec)
    mutate(plan, lambda d: d['rows']['rf0000_k00_00'].update(xy=[130.0, 250.0]))
    receipt = transport(spec, inputs, plan=plan)
    assert 'site (130.0, 250.0)' in spec['instances'][0]['note']
    assert graph_digest(spec) == graph_digest(original) == receipt['graph_sha256']
    assert spec['clocks'] == original['clocks'] and spec['edges'] == original['edges']
    assert spec['relay_splice_v2'] == original['relay_splice_v2']
    assert receipt['geometry_qualified'] is False


@pytest.mark.parametrize('field,value', [('instances', ['wrong_stage']), ('master', 'wrong_master'),
                                         ('tiles', 2), ('direction', 'NS'), ('slot', 'other_sink')])
def test_changed_ordered_stage_identity_refused(tmp_path, field, value):
    spec, inputs, plan = fixture(tmp_path)
    mutate(plan, lambda d: d['rows']['rf0000_k00_00'].update({field: value}))
    with pytest.raises(ValueError, match='stage identity differs'):
        transport(spec, inputs, plan=plan)


def test_missing_stage_refused(tmp_path):
    spec, inputs, plan = fixture(tmp_path)
    mutate(plan, lambda d: d.update(rows={}))
    with pytest.raises(ValueError, match='missing/extra'):
        transport(spec, inputs, plan=plan)


def test_foreign_source_refused(tmp_path):
    spec, inputs, plan = fixture(tmp_path)
    Path(inputs['contract']).write_text('changed input')
    with pytest.raises(ValueError, match='source/graph binding differs'):
        transport(spec, inputs, plan=plan)


@pytest.mark.parametrize('change', ['clock', 'reset', 'edge', 'stage_order'])
def test_changed_actual_graph_refused(tmp_path, change):
    spec, inputs, plan = fixture(tmp_path)
    if change == 'clock': spec['clocks'][0]['domain'] = 'other'
    if change == 'reset': spec['clocks'][1]['port'] = 'wrong_reset'
    if change == 'edge': spec['edges'][0]['bits'] = 47
    if change == 'stage_order': spec['relay_splice_v2'][0]['stage_order'] = ['wrong']
    with pytest.raises(ValueError, match='source/graph binding differs'):
        transport(spec, inputs, plan=plan)
