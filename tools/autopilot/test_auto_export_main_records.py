"""CLEAN-AGGR-R3 11-22: sign-off records committed to main count as exported in the guard ledger."""
import hashlib, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'die_plan'))
import auto_export as AE  # noqa: E402


def test_main_records_join_guard_ledger_clean_aggr_r3(tmp_path, monkeypatch):
    w = tmp_path / 'w'
    (w / 'physical/ref_tile/a/views/b').mkdir(parents=True)
    (w / 'results/x').mkdir(parents=True)
    a = b'{"verdict": "SIGNED"}\n'
    b = b'{"verdict": "SIGNED", "n": 2}\n'
    (w / 'physical/ref_tile/a/views/b/signoff.json').write_bytes(a)
    (w / 'results/x/top.signoff.json').write_bytes(b)
    (w / 'results/x/notes.json').write_bytes(b'{}')
    env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@t')
    for c in (['init', '-q', '-b', 'main'], ['add', '.'], ['commit', '-q', '-m', 'x']):
        subprocess.run(['git', '-C', str(w)] + c, check=True, env=env)
    want = {hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest()}
    assert AE.main_record_shas(str(w / '.git')) == want
    assert AE.main_record_shas(str(tmp_path / 'nogit')) == set()
    monkeypatch.setattr(AE, 'HOME', str(tmp_path / 'home'))
    AE.write_guard_exported({'units': {}}, [], [], push=False, git_dir=str(w / '.git'))
    got = open(tmp_path / 'home/.local/state/ot-delete-guard/exported_records.txt').read().split()
    assert want <= set(got)
