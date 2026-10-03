"""Synthetic control fixtures test refusal logic, never workload acceptance evidence."""
import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/v41_dspark_onpolicy'))
import qualified_terminal as T


def fixtures(tmp_path):
    runs, manifests = [], []
    for batch in range(2):
        run = tmp_path / f'run{batch}'; run.mkdir()
        item = dict(workload='coding_humaneval', prompt_id=f'fixture{batch}', n_prompt=2, ids=[10, 11])
        manifest = tmp_path / f'prompts{batch}.json'; manifest.write_text(json.dumps(dict(items=[item])))
        traces = [dict(item=item, mode=mode, L=2, tokens=[10, 11, 12, 13, 14, 15, 16, 17, 18],
                       **({'drafts': {str(p): [13, 14, 15, 16, 17] for p in range(2, 8)}} if mode == 'greedy' else
                          {'q_tok': {str(p): [.2] * 5 for p in range(2, 8)}, 'p_tok': [.5] * 7}))
                  for mode in ('greedy', 't1')]
        for name in ('run.sh', 'gen.log', 'draft.log', 'gen_out.pt'):
            (run / name).write_text('CONTROL_FIXTURE_NOT_GPU_EVIDENCE')
        (run / 'status').write_text('GENDONE\nDRAFTDONE\n')
        (run / 'drafts.json').write_text(json.dumps(traces))
        runs.append(run); manifests.append(manifest)
    return runs, manifests


def mutate(run, callback):
    path = run / 'drafts.json'; rows = json.loads(path.read_text())
    callback(rows); path.write_text(json.dumps(rows))


def test_complete_actual_identity_schema(tmp_path):
    runs, manifests = fixtures(tmp_path)
    inventory, rows = T.terminal_inputs(runs, manifests)
    assert len(rows) == 4 and len(inventory) == 14


def test_both_runs_must_be_terminal_before_any_payload_read(tmp_path, monkeypatch):
    runs, manifests = fixtures(tmp_path)
    (runs[1] / 'status').unlink()
    monkeypatch.setattr(T, 'sha', lambda _: pytest.fail('read payload before both terminals'))
    with pytest.raises(T.NotTerminal):
        T.terminal_inputs(runs, manifests)


def test_fail_not_promoted_by_later_done_marker(tmp_path):
    runs, manifests = fixtures(tmp_path)
    (runs[0] / 'status').write_text('GENFAIL\nGENDONE\nDRAFTDONE\n')
    with pytest.raises(ValueError, match='preserved failure'):
        T.terminal_inputs(runs, manifests)


@pytest.mark.parametrize('change', [
    lambda rows: rows.pop(),
    lambda rows: rows.append(copy.deepcopy(rows[0])),
    lambda rows: rows[0]['drafts'].pop('3'),
    lambda rows: rows[0]['drafts'].update({'999': [1] * 5}),
    lambda rows: rows[0]['drafts'].update({'2': [1] * 4}),
    lambda rows: rows[1]['q_tok'].update({'2': [float('nan')] * 5}),
    lambda rows: rows[1]['q_tok'].update({'2': [1.1] * 5}),
    lambda rows: rows[1]['p_tok'].pop(),
    lambda rows: rows[1]['p_tok'].__setitem__(0, 0),
    lambda rows: rows[0]['tokens'].__setitem__(0, 999),
    lambda rows: rows[0]['tokens'].extend([1] * 200),
])
def test_partial_stale_or_invalid_actual_traces_refused(tmp_path, change):
    runs, manifests = fixtures(tmp_path)
    mutate(runs[0], change)
    with pytest.raises(ValueError):
        T.terminal_inputs(runs, manifests)


def test_missing_terminal_artifact_refused(tmp_path):
    runs, manifests = fixtures(tmp_path)
    (runs[0] / 'gen_out.pt').unlink()
    with pytest.raises(ValueError, match='missing terminal artifact'):
        T.terminal_inputs(runs, manifests)


def test_published_values_remain_verify_windows_and_model_specific():
    assert T.B.PUBLISHED == {'a_chat': ('Arena-Hard', 3.78), 'b_reasoning': ('GSM8K', 5.24),
                             'h_creative': ('Poetry', 2.91)}
    assert 'V4-Flash (not V4.1)' in T.B.LMSYS_LABEL
    assert 'verify window' in T.B.LMSYS_LABEL
    assert T.B.WEIGHTS['equal (default)'] == {c: 1/8 for c in T.B.CLASSES}
    assert sum(T.B.WEIGHTS['measured-only equal (c-g)'].values()) == 1


def test_waiting_closure_does_not_compute_or_publish(tmp_path, monkeypatch):
    runs, manifests = fixtures(tmp_path)
    monkeypatch.setattr(T.B, 'main', lambda *_: pytest.fail('computed before existing chain closure'))
    out = tmp_path / 'actual.json'
    with pytest.raises(T.NotTerminal):
        T.close(runs, manifests, out)
    assert not out.exists()


def test_closure_cannot_write_inside_preserved_run(tmp_path):
    runs, manifests = fixtures(tmp_path)
    with pytest.raises(ValueError, match='outside preserved'):
        T.close(runs, manifests, runs[0] / 'new.json')
    assert not (runs[0] / 'new.json').exists()
