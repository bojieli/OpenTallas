"""Process timeout and persistent-output tests; no hardware launch."""
from pathlib import Path
import json
import subprocess
import sys
from types import SimpleNamespace
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import run_abi3_physical_persistent as P


def fake_driver(tmp_path, main):
    source = tmp_path / 'driver.py'; source.write_text('# immutable source\n')
    return SimpleNamespace(__file__=str(source), main=main,
        run=lambda args, timeout=0.001: subprocess.run(args, timeout=timeout, check=False),
        flow_timeout_seconds=lambda: 0.001, synth_timeout_seconds=lambda: 0.001)


def test_actual_subprocess_outlives_old_timeout_and_workdir_survives(tmp_path):
    work = tmp_path / 'work'; receipt = tmp_path / 'receipt.json'
    def main(args):
        assert args == ['--view', 'asap7', '--keep-workdir', str(work)]
        assert d.flow_timeout_seconds() is None and d.synth_timeout_seconds() is None
        assert d.run([sys.executable, '-c', 'import time; time.sleep(.05)'], timeout=.001).returncode == 0
        (work / 'terminal.odb').write_bytes(b'preserved output')
        return 7  # Driver engineering verdict is not replaced by a success.
    d = fake_driver(tmp_path, main); original = d.run; before = P.digest(d.__file__)
    assert P.launch(d, ['--view', 'asap7'], workdir=work, receipt=receipt) == 7
    r = json.loads(receipt.read_text())
    assert r['exit_code'] == 7 and r['status'] == 'DRIVER_RETURNED'
    assert r['driver_sha256_after'] == before and not r['hardware_admitted_by_launcher']
    assert (work / 'terminal.odb').read_bytes() == b'preserved output'
    assert d.run is original and d.flow_timeout_seconds() == .001


def test_exception_preserves_outputs_and_restores_driver(tmp_path):
    work = tmp_path / 'work'; receipt = tmp_path / 'receipt.json'
    def main(args):
        (work / 'partial.odb').write_bytes(b'partial')
        raise RuntimeError('retained failure')
    d = fake_driver(tmp_path, main); original = d.run
    with pytest.raises(RuntimeError, match='retained failure'):
        P.launch(d, [], workdir=work, receipt=receipt)
    assert (work / 'partial.odb').read_bytes() == b'partial'
    assert json.loads(receipt.read_text())['status'] == 'EXCEPTION_WORKDIR_PRESERVED'
    assert d.run is original


@pytest.mark.parametrize('kind', ['work', 'receipt', 'override', 'relative'])
def test_reuse_and_workdir_substitution_refused_before_driver(tmp_path, kind):
    work = tmp_path / 'work'; receipt = tmp_path / 'receipt.json'; args = []
    if kind == 'work': work.mkdir()
    if kind == 'receipt': receipt.write_text('keep')
    if kind == 'override': args = ['--keep-workdir=/other']
    if kind == 'relative': work = Path('relative')
    d = fake_driver(tmp_path, lambda args: pytest.fail('driver must not run'))
    with pytest.raises(ValueError): P.launch(d, args, workdir=work, receipt=receipt)
    if kind == 'receipt': assert receipt.read_text() == 'keep'


def test_finite_inherited_hard_cap_refused(monkeypatch):
    monkeypatch.setattr(P.resource, 'getrlimit', lambda kind: (10, 10))
    with pytest.raises(ValueError, match='finite inherited hard limit'):
        P.remove_inherited_runtime_caps()
