"""Legacy observer must not turn stale/shared-path evidence into acceptance."""
import importlib.util
import os
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('watch', Path(__file__).resolve().parents[1] / 'tools/qwen_dietop_watch.py')
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)
CID = 'b' * 64


def container(case, running=False):
    return dict(Id=CID, Mounts=[dict(Type='bind', Source=str(case), Destination='/work')],
                command=['openroad', '/work/run.tcl'], State=dict(
                    Status='running' if running else 'exited', Running=running,
                    OOMKilled=False, ExitCode=0, StartedAt='2026-10-07T05:00:00Z',
                    FinishedAt='2026-10-07T06:00:00Z'))


def artifacts(case):
    for name, text in [('run.log', 'OT_LEGAL instances=17729 overlaps=0 outside=0\nOT_ASSERT PASS\nOT_PA DONE'),
                       ('floorplan.odb', 'test database'), ('case.done', 'done')]:
        p = case / name
        p.write_text(text)
        t = watch.epoch('2026-10-07T05:30:00Z')
        os.utime(p, (t, t))


def fake_commands(monkeypatch):
    calls = []
    def command(argv):
        calls.append(argv)
        assert argv[:2] in (['docker', 'ps'], ['docker', 'top'], ['docker', 'events'])
        return dict(argv=argv, returncode=0, stdout='', stderr='')
    monkeypatch.setattr(watch, 'command', command)
    return calls


def test_missing_exact_id_does_not_follow_reused_name(tmp_path, monkeypatch):
    artifacts(tmp_path)
    calls = fake_commands(monkeypatch)
    monkeypatch.setattr(watch, 'inspect', lambda cid: (None, {'returncode': 1}))
    r = watch.observe(tmp_path, CID, 'placement')
    assert r['physical']['status'] == 'NOT_HARVESTED'
    assert 'DO_NOT_FOLLOW_REUSED_NAME' in r['next_step']
    assert not r['continuation_allowed']
    assert not any(c[1] == 'top' for c in calls)


def test_live_with_stale_done_and_artifact_is_not_terminal(tmp_path, monkeypatch):
    artifacts(tmp_path)
    fake_commands(monkeypatch)
    monkeypatch.setattr(watch, 'inspect', lambda cid: (container(tmp_path, True), None))
    r = watch.observe(tmp_path, CID, 'placement')
    assert r['physical']['status'] == 'NO_SUCCESSFUL_CONTAINER_TERMINAL'
    assert r['next_step'] == 'PRESERVE_LIVE_RUN'
    assert not r['continuation_allowed']


def test_physical_success_does_not_certify_source(tmp_path, monkeypatch):
    artifacts(tmp_path)
    fake_commands(monkeypatch)
    monkeypatch.setattr(watch, 'inspect', lambda cid: (container(tmp_path), None))
    r = watch.observe(tmp_path, CID, 'placement')
    assert r['physical']['status'] == 'PHYSICAL_PASS_SOURCE_UNVERIFIED'
    assert len(r['physical']['sha256']) == 2
    assert not r['source_verified'] and not r['continuation_allowed'] and not r['drt_complete']


@pytest.mark.parametrize('change', ['oom', 'exit', 'stale', 'future', 'missing', 'failure', 'no_marker'])
def test_terminal_failures(tmp_path, change):
    artifacts(tmp_path)
    data = container(tmp_path)
    if change == 'oom': data['State']['OOMKilled'] = True
    if change == 'exit': data['State']['ExitCode'] = 137
    if change in ('stale', 'future'):
        t = watch.epoch('2026-10-07T04:00:00Z' if change == 'stale' else '2026-10-07T07:00:00Z')
        os.utime(tmp_path/'floorplan.odb', (t, t))
    if change == 'missing': (tmp_path/'floorplan.odb').unlink()
    if change in ('failure', 'no_marker'):
        p = tmp_path/'run.log'
        p.write_text(p.read_text()+'\nOT_PA FAIL bad' if change == 'failure' else 'empty')
        t = watch.epoch('2026-10-07T05:30:00Z')
        os.utime(p, (t, t))
    assert watch.physical(tmp_path, 'placement', data)['status'] != 'PHYSICAL_PASS_SOURCE_UNVERIFIED'


def test_disappearance_during_harvest_invalidates_result(tmp_path, monkeypatch):
    artifacts(tmp_path)
    fake_commands(monkeypatch)
    states = iter([(container(tmp_path), None), (None, {'returncode': 1})])
    monkeypatch.setattr(watch, 'inspect', lambda cid: next(states))
    assert watch.observe(tmp_path, CID, 'placement')['physical']['status'] == 'CONTAINER_CHANGED_DURING_OBSERVATION'


def test_wrong_case_mount_is_not_harvested(tmp_path, monkeypatch):
    artifacts(tmp_path)
    fake_commands(monkeypatch)
    data = container(tmp_path / 'different')
    monkeypatch.setattr(watch, 'inspect', lambda cid: (data, None))
    assert watch.observe(tmp_path, CID, 'placement')['physical']['status'] == 'CASE_OR_PHASE_IDENTITY_MISMATCH'
