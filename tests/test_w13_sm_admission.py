import json
import sys
from pathlib import Path
from unittest.mock import Mock

from tools import w13_chain_successor as chain
from tools.w13_floorplan_receipt import admission, cpu_admission


def test_old_lease_cannot_admit_insufficient_peak():
    assert not admission(59 * 1048576, 55, 60)['passed']
    assert admission(60 * 1048576, 55, 60)['passed']


def test_cpu_fit_is_required_even_when_memory_fits():
    assert admission(142 * 1048576, 60, 60)['passed']
    assert not cpu_admission(127.91, 28)['passed']
    assert not cpu_admission(206.25, 28)['passed']
    assert not cpu_admission(28, 28)['passed']
    assert not cpu_admission(float('nan'), 28)['passed']
    assert cpu_admission(1.22, 28)['passed']


def test_guarded_dispatch_checks_worker_memory_before_synthesis(tmp_path, monkeypatch):
    dest = tmp_path / 'dest'
    receipt = tmp_path / 'w13_floorplan_receipt.py'
    gate = tmp_path / 'w13_column_corner_gate.py'
    receipt.write_text('receipt')
    gate.write_text('gate')
    branch = dict(name='q', handles=[], columns=[], destination=str(dest), sm='ot_gpu_sm_q',
                  sm_sources=[], remote_work='/home/ubuntu/w13work/test_only',
                  budget='budget.json', log=str(tmp_path / 'log'), minimum_gib=60, validated_peak_gib=60)
    config = dict(repository=str(tmp_path), base='historical-pin', config_sha256='config-pin',
                  receipt_tool=str(receipt), gate_tool=str(gate), bundle_pins={str(receipt): chain.digest(receipt)},
                  exclude='existing-exclusions', remote_gate='existing-gate')
    monkeypatch.setattr(chain, 'parked', lambda c: None)
    monkeypatch.setattr(chain, 'event', lambda *a, **k: None)
    monkeypatch.setattr(chain, 'audits', lambda *a: [])
    monkeypatch.setattr(chain, 'qualify', lambda *a: {'passed': True})
    monkeypatch.setattr(chain, 'identity', lambda pid: {'pid': pid})
    def run(args, **kwargs):
        if 'worktree' in args:
            (dest / 'tools').mkdir(parents=True)
        return Mock(returncode=0)
    monkeypatch.setattr(chain.subprocess, 'run', run)
    def output(args, **kwargs):
        if args[0] == 'python3':
            return '60.0\n'
        if 'rev-parse' in args:
            return 'pinned-dispatch-head\n'
        return ''
    monkeypatch.setattr(chain.subprocess, 'check_output', output)
    launched = []
    def popen(args, **kwargs):
        launched.append((args, kwargs))
        return Mock(pid=99, wait=lambda: 0)
    monkeypatch.setattr(chain.subprocess, 'Popen', popen)
    assert chain.run_branch(config, branch)
    args, kwargs = launched[0]
    assert kwargs['env']['OT_GATE_MIN_GB'] == '60'
    cmd = args[-1]
    assert cmd.index('--local-memory') < cmd.index('--phase synth')
    assert '--lease-floor-gib 60' in cmd
    assert ' && ' in cmd
    assert 'ot_gpu_sm_q_admission.json' in cmd
