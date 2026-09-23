"""Interrupted physical-result publication must not destroy existing evidence."""
import errno
import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('physical', Path(__file__).resolve().parents[1]/'tools/run_abi3_physical.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

@pytest.mark.parametrize('existing', [False, True])
@pytest.mark.parametrize('failure', ['write', 'fsync', 'replace'])
def test_failed_publication_preserves_destination(tmp_path, monkeypatch, existing, failure):
    path = tmp_path/'record.json'
    if existing:
        path.write_text('previous evidence\n')
    def fail(*args, **kwargs):
        raise OSError(errno.ENOSPC, 'No space left on device')
    if failure == 'write':
        original = runner.tempfile.NamedTemporaryFile
        class BrokenStream:
            def __init__(self, stream): self.stream = stream; self.name = stream.name
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def write(self, text):
                self.stream.write(text[:5]); self.stream.flush(); fail()
        monkeypatch.setattr(runner.tempfile, 'NamedTemporaryFile', lambda **kw: BrokenStream(original(**kw)))
    else:
        monkeypatch.setattr(runner.os, failure, fail)
    with pytest.raises(OSError):
        runner.canonical_dump({'status':'pass'},path)
    assert path.exists() == existing
    if existing: assert path.read_text() == 'previous evidence\n'
    assert list(tmp_path.iterdir()) == ([path] if existing else [])


def test_complete_record_replaces_atomically(tmp_path):
    path = tmp_path/'record.json'; path.write_text('old')
    runner.canonical_dump({'z':1,'a':'é'},path)
    assert json.loads(path.read_text()) == {'z':1,'a':'é'}
    assert path.read_text() == '{\n  "a": "é",\n  "z": 1\n}\n'
    assert list(tmp_path.iterdir()) == [path]
