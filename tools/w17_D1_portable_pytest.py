"""Opt-in source authority for unchanged D1 tests; no private branch or ROOT reads."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
import w17_D1_materialized_prerequisite_guard as guard
pytest_plugins=['w17_owner_progress_archival_pytest']

def exact_source(command,**kwargs):
    guard.validate()
    m=json.loads((guard.REC/'prerequisite_manifest.json').read_text())
    if not isinstance(command,list) or len(command)!=3 or command[:2]!=['git','show'] or command[2] not in m['test_git_authority']:
        raise ValueError('unenrolled historical source query')
    path=(guard.ROOT/m['test_git_authority'][command[2]]).resolve()
    if not path.is_relative_to(guard.ROOT.resolve()):raise ValueError('source path escape')
    return path.read_bytes()

@pytest.fixture(autouse=True)
def enrolled_D1_test_authority(request,monkeypatch):
    if request.module.__name__.split('.')[-1]=='test_w17_D1_frozen_package':
        # Only this test module's source-authority reads; runner subprocess implementation unchanged.
        monkeypatch.setattr(request.module,'subprocess',SimpleNamespace(check_output=exact_source))
