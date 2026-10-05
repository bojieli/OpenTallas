"""Explicit runner selection; legacy remains default, no silent fallback."""
import hashlib
import importlib
from pathlib import Path


def select_checkpoint_helper(selection='legacy_v1', *, expected_sha256=None):
    names={'legacy_v1':'ds_producer_checkpoint_resume',
           'quiescent_v2':'ds_producer_checkpoint_resume_v2'}
    if selection not in names:raise ValueError('explicit known checkpoint helper required')
    if selection=='quiescent_v2' and not expected_sha256:
        raise ValueError('successor source pin required')
    path=Path(__file__).with_name(names[selection]+'.py')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if expected_sha256 is not None and digest!=expected_sha256:
        raise ValueError('selected checkpoint helper source mismatch')
    module=importlib.import_module(names[selection])
    if Path(module.__file__).resolve()!=path.resolve():raise ValueError('selected helper module origin mismatch')
    for name in ('project_checkpoint','capture_quiescent','verify_checkpoint','restore_quiescent'):
        if not callable(getattr(module,name,None)):raise ValueError('selected checkpoint API missing')
    return module
