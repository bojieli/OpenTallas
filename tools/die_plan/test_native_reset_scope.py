"""Selected reset scope retains selected/global native freshness checks."""
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_topology as K


def fixture(tmp_path):
    raw = dict(partition_types={
        'selected':dict(clock=dict(taps=[dict(x=1,y=2)]), reset=dict(depth=3), buses=[]),
        'other':dict(clock=dict(taps=[dict(x=5,y=6)]), reset=dict(depth=2), buses=[]),
    }, reset=dict(root='r'), lanes=[], ports=[])
    plan=tmp_path/'producer.json'; plan.write_text(json.dumps(raw))
    ab=tmp_path/'asbuilt.json'; ab.write_text('{}')
    out=tmp_path/'bind'; out.mkdir()
    K.write_bind_receipt(raw,out,str(ab),plan_path=plan)
    (out/'provenance_bind.json').write_text(json.dumps(dict(provenance=dict(plan=str(plan)))))
    return raw,plan,ab,out


def test_scope_default_off(tmp_path,monkeypatch):
    raw,plan,ab,out=fixture(tmp_path)
    raw['partition_types']['other']['clock']['taps'][0]['x']=99
    monkeypatch.delenv('OT_NATIVE_RESET_SCOPE',raising=False)
    assert not K.bind_matches(raw,'selected',out,str(ab),plan)
    monkeypatch.setenv('OT_NATIVE_RESET_SCOPE','selected')
    assert K.bind_matches(raw,'selected',out,str(ab),plan)


def test_scope_rejects_selected_global_transport_and_asbuilt_mutants(tmp_path,monkeypatch):
    raw,plan,ab,out=fixture(tmp_path)
    monkeypatch.setenv('OT_NATIVE_RESET_SCOPE','selected')
    raw['partition_types']['other']['clock']['taps'][0]['x']=99
    assert K.bind_matches(raw,'selected',out,str(ab),plan)
    for mutate in (
        lambda r:r['partition_types']['selected']['clock']['taps'][0].update(x=100),
        lambda r:r['partition_types']['selected']['reset'].update(depth=4),
        lambda r:r['reset'].update(root='wrong'),
        lambda r:r['ports'].append(dict(id='new',src='a',dst='b',width=4,kind='data')),
    ):
        mutant=copy.deepcopy(raw); mutate(mutant)
        assert not K.bind_matches(mutant,'selected',out,str(ab),plan)
    ab.write_text('{"changed":1}')
    assert not K.bind_matches(raw,'selected',out,str(ab),plan)


def test_scope_requires_unchanged_producer_context(tmp_path,monkeypatch):
    raw,plan,ab,out=fixture(tmp_path)
    monkeypatch.setenv('OT_NATIVE_RESET_SCOPE','selected')
    raw['partition_types']['other']['clock']['taps'][0]['x']=99
    plan.write_text(json.dumps(raw))
    assert not K.bind_matches(raw,'selected',out,str(ab),plan)
    plan.unlink()
    assert not K.bind_matches(raw,'selected',out,str(ab),plan)


def test_portable_exact_capture_and_full_producer_mutant(tmp_path,monkeypatch):
    raw,plan,ab,out=fixture(tmp_path)
    capture=tmp_path/'captured_producer.json'; capture.write_bytes(plan.read_bytes())
    plan.unlink()
    current=copy.deepcopy(raw); current['partition_types']['other']['clock']['taps'][0]['x']=99
    monkeypatch.setenv('OT_NATIVE_RESET_SCOPE','selected')
    assert not K.bind_matches(current,'selected',out,str(ab),plan)
    monkeypatch.setenv('OT_NATIVE_PRODUCER_CONTEXT',str(capture))
    assert K.bind_matches(current,'selected',out,str(ab),plan)
    mutant=copy.deepcopy(raw)
    mutant['partition_types']['other']['buses'].append(dict(name='wrong',dir='in',width=4,kind='data'))
    capture.write_text(json.dumps(mutant))
    assert not K.bind_matches(current,'selected',out,str(ab),plan)
