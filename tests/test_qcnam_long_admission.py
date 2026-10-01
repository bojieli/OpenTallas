"""No signals or live jobs in these admission tests."""
import sys
import json
from types import SimpleNamespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
import qcnam_long_admission as A


def hold():
    return dict(supervisor_pid=100, supervisor_start_ticks='10', greedy_waiter_pid=101, greedy_waiter_start_ticks='11')


def supervisor():
    return dict(pid=100, start_ticks='10', argv=['/bin/bash', A.LANE], state='T')


def waiter():
    return dict(pid=101, start_ticks='11', ppid=100, state='Z', exit_code=0)


def test_existing_waiter_identity():
    A.verify_supervisor(supervisor(), hold())
    A.verify_finished_waiter(waiter(), hold())


@pytest.mark.parametrize('key,value', [('start_ticks', '20'), ('pid', 200), ('state', 'S'), ('argv', ['unrelated'])])
def test_no_signal_to_reused_or_running_supervisor(key, value):
    p = supervisor()
    p[key] = value
    with pytest.raises(ValueError):
        A.verify_supervisor(p, hold())


@pytest.mark.parametrize('key,value', [('state', 'R'), ('exit_code', 256), ('ppid', 200), ('start_ticks', '30')])
def test_greedy_must_finish_successfully(key, value):
    p = waiter()
    p[key] = value
    with pytest.raises(ValueError):
        A.verify_finished_waiter(p, hold())


def test_budget_prices_atomic_checkpoint_and_concurrent_writer():
    live = A.budget(5, 3, True, margin=7)
    done = A.budget(5, 3, False, margin=7)
    assert live['long_hidden_bytes'] == 11408506880
    assert live['checkpoint_and_atomic_temporary_bytes'] == 10
    assert live['required_available_bytes'] == 11408506880 + 10 + 3 + 7
    assert live['required_available_bytes'] - done['required_available_bytes'] == 3


@pytest.mark.parametrize('failure', ['greedy_running', 'disk_low', 'missing_pid'])
def test_explicit_release_cannot_bypass_admission(monkeypatch, tmp_path, failure):
    runs = tmp_path / 'runs'
    for n in ['core', 'mmlu1000']:
        p = runs / n / 'work'
        p.mkdir(parents=True)
        (p / 'checkpoint.pt').write_bytes(b'checkpoint')
    (runs / 'core/run.json').write_text('{}')
    gen = runs / 'gen'
    gen.mkdir()
    (gen / 'gen.json').write_text(json.dumps([dict(name=f'gen{i}', ids=[0]*256, prompt_len=128) for i in range(8)]))
    (gen / 'log.txt').write_text('done 123\n')
    h = hold()
    h['core_output_sha256'] = {'run.json': A.G.digest(runs / 'core/run.json')}
    hp = tmp_path / 'hold.json'
    hp.write_text(json.dumps(h))
    obs = tmp_path / 'obs.json'
    obs.write_text(json.dumps(dict(source_sha256={}, snapshot_identity={}, job_sha256={})))
    monkeypatch.setattr(A, 'HOLD', hp)
    monkeypatch.setattr(A.G, 'RUNS', runs)
    monkeypatch.setattr(A.G, 'JOBS', tmp_path / 'jobs')
    monkeypatch.setattr(A.G, 'source_identity', lambda: {})
    monkeypatch.setattr(A.G, 'snapshot_identity', lambda: {})
    monkeypatch.setattr(A.G, 'completed', lambda p: None)
    monkeypatch.setattr(A.G, 'active_jobs', lambda: [])
    def read_proc(pid):
        if failure == 'missing_pid':
            raise FileNotFoundError('old PID absent: inspect namespace')
        p = supervisor() if pid == 100 else waiter()
        if failure == 'greedy_running' and pid == 101:
            p['state'] = 'R'
        return p
    monkeypatch.setattr(A, 'proc', read_proc)
    monkeypatch.setattr(A.os, 'statvfs', lambda p: SimpleNamespace(f_bavail=0 if failure == 'disk_low' else 10**12, f_frsize=1))
    monkeypatch.setattr(A.os, 'pidfd_open', lambda p: pytest.fail('must not signal or open a process handle'))
    monkeypatch.setattr(sys, 'argv', ['admission', '--observation', str(obs), '--release'])
    if failure == 'missing_pid':
        with pytest.raises(FileNotFoundError):
            A.main()
    else:
        assert A.main() == 2
