"""NOMCAP-MAP (FLOW-OPS-R2 11-21): the child-flop clock coverage maps the r708 /nomcap container libraries to the
host nomcap_dir() (sha-bound), and refresh-coverage re-derives a finished record's coverage from its own receipts."""
import hashlib
import json
from pathlib import Path

import signoff
from test_clock_model_coverage import library
from test_signoff import record


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _setup(tmp_path, monkeypatch, sha_ok=True):
    ncd = tmp_path / 'nomcap_libs'
    ncd.mkdir()
    seq = ncd / 'asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib'
    seq.write_text('library(seq) { time_unit : "1ps"; cell("DFFHQNx1_ASAP7_75t_R") { } }')
    kit = tmp_path / 'kit'
    (kit / 'macros').mkdir(parents=True)
    child = library(kit / 'macros' / 'child_tt.lib')
    monkeypatch.setattr(signoff, 'nomcap_dir', lambda: ncd)
    rows = [{'path': '/nomcap/' + seq.name, 'sha256': _sha(seq) if sha_ok else 'bad'},
            {'path': '/work/macros/child_tt.lib', 'sha256': _sha(child)}]
    return kit, rows


def _receipt(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'status': 'LOADED', 'libraries': rows}))
    return path


def test_nomcap_container_path_maps_to_host_nomcap_dir(tmp_path, monkeypatch):
    kit, rows = _setup(tmp_path, monkeypatch)
    rec = _receipt(tmp_path / 'libraries.json', rows)
    found = signoff.consumed_clock_model_coverage(rec, {'kit': str(kit)}, ['child', 'DFFHQNx1_ASAP7_75t_R'])
    assert found['status'] == 'UNEXPANDED_CHILD_ETM', found      # mapped and read: the child marker is seen
    assert found['models'][0]['consumed_liberty'] == '/work/macros/child_tt.lib'
    only = signoff.consumed_clock_model_coverage(_receipt(tmp_path / 'n.json', rows[:1]), {'kit': str(kit)},
                                                 ['DFFHQNx1_ASAP7_75t_R'])
    assert only['status'] == 'NO_UNEXPANDED_CHILD_ETM' and only['verdict'] == 'PASS', only


def test_nomcap_mapping_stays_fail_closed(tmp_path, monkeypatch):
    kit, rows = _setup(tmp_path, monkeypatch, sha_ok=False)
    bad = signoff.consumed_clock_model_coverage(_receipt(tmp_path / 'l.json', rows), {'kit': str(kit)}, ['child'])
    assert bad['status'] == 'UNAVAILABLE' and 'hash mismatch' in bad['reason']
    monkeypatch.setattr(signoff, 'nomcap_dir', lambda: None)      # OT_NOMCAP=0 run cannot consume /nomcap
    off = signoff.consumed_clock_model_coverage(_receipt(tmp_path / 'o.json', rows), {'kit': str(kit)}, ['child'])
    assert off['status'] == 'UNAVAILABLE' and 'OT_NOMCAP off' in off['reason']
    esc = [{'path': '/nomcap/../etc/x.lib', 'sha256': 'x'}]
    assert signoff.consumed_clock_model_coverage(_receipt(tmp_path / 'e.json', esc), {'kit': str(kit)},
                                                 ['child'])['status'] == 'UNAVAILABLE'
    other = [{'path': '/elsewhere/x.lib', 'sha256': 'x'}]
    assert signoff.consumed_clock_model_coverage(_receipt(tmp_path / 'x.json', other), {'kit': str(kit)},
                                                 ['child'])['status'] == 'UNAVAILABLE'


def test_refresh_coverage_rederives_finished_record(tmp_path, monkeypatch):
    kit, rows = _setup(tmp_path, monkeypatch)
    out = tmp_path / 'resign' / 'signoff'
    rec = record()
    rec['inputs'] = {'kit': str(kit)}
    stale = dict(schema='opentallas.clock_endpoint_coverage.v1', status='UNAVAILABLE', verdict='NOT RUN', models=[],
                 reason='consumed non-PDK Liberty host mapping unavailable: /nomcap/x')
    for c in ('tt', 'ff'):
        rec['corners'][c]['clock_endpoint_masters'] = ['DFFHQNx1_ASAP7_75t_R']
        rec['corners'][c]['clock_endpoint_mapping_errors'] = 0
        rec['corners'][c]['clock_endpoint_coverage'] = dict(stale)
        _receipt(out / c / 'libraries.json', rows[:1])
        (out / c / 'corner.json').write_text(json.dumps({'clock_endpoint_coverage': stale}))
    signoff.evaluate(rec)
    assert rec['checks']['clock']['verdict'] == 'NOT RUN'
    path = out / 'signoff.json'
    path.write_text(json.dumps(rec))
    dry, changed = signoff.refresh_clock_coverage(path)
    assert changed['tt']['before'] == 'UNAVAILABLE' and changed['tt']['after'] == 'NO_UNEXPANDED_CHILD_ETM'
    assert dry['checks']['clock']['verdict'] == 'PASS'
    assert json.loads(path.read_text())['checks']['clock']['verdict'] == 'NOT RUN'   # dry run writes nothing
    assert signoff.main(['refresh-coverage', str(path), '--write']) == (0 if dry['verdict'] == 'SIGNED' else 1)
    new = json.loads(path.read_text())
    assert new['checks']['clock']['verdict'] == 'PASS' and new['clock_coverage_refresh']['clock_before'] == 'NOT RUN'
    assert json.loads((out / 'signoff.json.pre_cov_refresh').read_text())['checks']['clock']['verdict'] == 'NOT RUN'
    assert json.loads((out / 'ff' / 'corner.json').read_text())['clock_endpoint_coverage']['verdict'] == 'PASS'
