import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import h4_hbm_service_source_closure as S

def test_all_archives_resolve_without_git(monkeypatch):
    def forbidden(*a,**k):raise AssertionError('Git disabled')
    monkeypatch.setattr(S.subprocess,'run',forbidden)
    inputs=S.ExactInputs(archive_only=True);inputs.validate()
    assert inputs.git_reads==0 and inputs.archive_reads==30

def test_hash_mismatch_rejects(tmp_path):
    m=json.loads((S.ARCHIVE/'manifest.json').read_text());r=m['inputs'][0]
    (tmp_path/'inputs').mkdir();(tmp_path/'manifest.json').write_text(json.dumps(m))
    (tmp_path/r['archive']).write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='hash mismatch'):S.ExactInputs(tmp_path,archive_only=True)(r['commit'],r['path'])

def test_git_mismatch_is_not_hidden_by_good_archive(monkeypatch):
    class Wrong:
        returncode=0;stdout=b'wrong Git bytes'
    monkeypatch.setattr(S.subprocess,'run',lambda *a,**k:Wrong())
    i=S.ExactInputs();r=i.manifest['inputs'][0]
    with pytest.raises(ValueError,match='hash mismatch'):i(r['commit'],r['path'])

def test_missing_git_uses_verified_archive(monkeypatch):
    class Absent:
        returncode=128
    monkeypatch.setattr(S.subprocess,'run',lambda *a,**k:Absent())
    i=S.ExactInputs();r=i.manifest['inputs'][0]
    assert S.digest(i(r['commit'],r['path']))==r['sha256']
    assert i.archive_reads==1 and i.git_reads==0

def test_unlisted_input_rejected():
    with pytest.raises(ValueError,match='unarchived'):S.ExactInputs(archive_only=True)('new','unknown')

def test_adapter_restores_original_loader(monkeypatch):
    before=S.V.pinned
    def fail():raise ValueError('endpoint gate remains blocked')
    monkeypatch.setattr(S.C,'build',fail)
    with pytest.raises(ValueError,match='endpoint gate'):S.replay('context',archive_only=True)
    assert S.V.pinned is before

def test_source_constraints_keep_implementation_and_cost_admission_blocked():
    r=json.loads((S.ARCHIVE/'Dewey_Sagan_source_constraints.json').read_text())
    m=S.ROOT/'results/uarch/h4_hbm_service_context_g0_20261002/final/model.json'
    assert r['model_receipt_sha256']==S.digest(m.read_bytes())
    assert r['historical_inputs_manifest_sha256']==S.digest((S.ARCHIVE/'manifest.json').read_bytes())
    assert r['hardware_admission']=='FAIL_PHYSICAL_SOURCE_BINDING'
    assert not r['implementation_authorized_by_this_record']
    assert all(not s['source_bound_gateway_present'] for s in r['source_constraints'])
    c=r['Dewey_cost_export']
    assert not c['automatic_delta_enabled'] and c['mode']=='RECONCILE_EXISTING_INTERVAL_ONLY'
    assert c['whole_token_ns'] is None and c['receipt_id']==r['model_receipt_sha256']
