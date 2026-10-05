"""Control gates for PID reuse, surviving children and raw verdict preservation."""
import base64
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import w12_terminal_collect as C


def bound():
    return dict(endpoint='local', host=dict(hostname='worker', boot_id='boot-a'), roots=[100],
                processes={'100': dict(pid=100, start_ticks=42, argv=['bash', 'job.sh'], state='S', ppid=1),
                           '101': dict(pid=101, start_ticks=43, argv=['sim', '--work', '/job'], state='R', ppid=100)})


@pytest.mark.parametrize('field,value', [('start_ticks', 999), ('argv', ['unrelated'])])
def test_reused_pid_or_changed_argv_is_inconclusive(field, value):
    b = bound()
    s = copy.deepcopy(b)
    s['processes']['100'][field] = value
    r = C.evaluate(b, s)
    assert r['state'] == 'identity_changed' and r['qualification'] == 'inconclusive'


@pytest.mark.parametrize('field,value', [('hostname', 'other-worker'), ('boot_id', 'boot-b')])
def test_changed_host_or_boot_is_inconclusive(field, value):
    b = bound()
    s = copy.deepcopy(b)
    s['host'][field] = value
    assert C.evaluate(b, s)['state'] == 'identity_changed'


def test_changed_endpoint_never_contacts_new_host():
    b = bound()
    assert C.poll(dict(host='different-host'), b)['state'] == 'identity_changed'


def test_wrapper_exit_with_reparented_child_blocks_archive():
    b = bound()
    s = copy.deepcopy(b)
    del s['processes']['100']
    s['processes']['101']['ppid'] = 1
    r = C.evaluate(b, s)
    assert r['state'] == 'children_live' and r['live_pids'] == [101]


def test_exited_roots_with_new_scoped_child_blocks_archive():
    b = bound()
    s = dict(host=b['host'], processes={'202': dict(pid=202, start_ticks=55, argv=['openroad'], state='R', ppid=1)})
    assert C.evaluate(b, s)['state'] == 'children_live'


def test_only_exited_children_allow_intake():
    b = bound()
    assert C.evaluate(b, dict(host=b['host'], processes={}))['state'] == 'eligible_for_intake'
    zombie = copy.deepcopy(b)
    for p in zombie['processes'].values():
        p.update(state='Z', argv=[])
    assert C.evaluate(b, zombie)['state'] == 'eligible_for_intake'


def test_wrapper_rc_is_never_a_verdict(tmp_path):
    rc = tmp_path / 'wrapper.rc'
    rc.write_text('0\n')
    missing = tmp_path / 'verdict.json'
    result = C.intake(dict(record=str(missing), extras=[str(rc)]))
    assert result['raw_status'] is None and result['qualification'] == 'inconclusive'
    rc.write_text('1\n')
    missing.write_text('{"status": "pass"}\n')
    assert C.intake(dict(record=str(missing), extras=[str(rc)]))['raw_status'] == 'pass'


def test_failed_record_bytes_are_preserved(tmp_path):
    p = tmp_path / 'physical.json'
    raw = b'{"status":"error","closed":false}  \n'
    p.write_bytes(raw)
    r = C.intake(dict(record=str(p), extras=[]))
    assert r['raw_status'] == 'error'
    assert base64.b64decode(r['files'][str(p)]['base64']) == raw
    assert p.read_bytes() == raw


def test_child_appearing_during_intake_blocks_return_of_evidence(monkeypatch):
    b = bound()
    ended = dict(host=b['host'], processes={})
    child = dict(host=b['host'], processes={'101': b['processes']['101']})
    snapshots = iter([ended, child])
    monkeypatch.setattr(C, 'capture', lambda *args: next(snapshots))
    monkeypatch.setattr(C, 'intake', lambda *args: dict(raw_status='pass', files={'verdict': 'data'}))
    r = C.remote_probe({}, b, True)
    assert r['state'] == 'children_live' and 'files' not in r


def test_identity_alert_survives_later_pid_disappearance(tmp_path, monkeypatch):
    control, spool = tmp_path / 'control', tmp_path / 'spool'
    control.mkdir()
    (control / 'bindings.json').write_text(json.dumps({'job': bound()}))
    monkeypatch.setattr(C, 'JOBS', [dict(name='job', host=None)])
    monkeypatch.setattr(sys, 'argv', ['collector', '--control', str(control), '--spool', str(spool), '--once'])
    monkeypatch.setattr(C, 'poll', lambda *args: dict(state='identity_changed', qualification='inconclusive', pid=100))
    C.main()
    def forbidden(*args):
        raise AssertionError('Identity alert must not be automatically rebound or cleared')
    monkeypatch.setattr(C, 'poll', forbidden)
    C.main()
    assert json.loads((control / 'state.json').read_text())['jobs']['job']['state'] == 'identity_changed'
    assert list(spool.iterdir()) == []


def test_existing_receipt_is_never_overwritten(tmp_path):
    receipt = tmp_path / 'archive.json'
    C.write_new(receipt, dict(raw_status='fail'))
    original = receipt.read_bytes()
    with pytest.raises(FileExistsError):
        C.write_new(receipt, dict(raw_status='pass'))
    assert receipt.read_bytes() == original
