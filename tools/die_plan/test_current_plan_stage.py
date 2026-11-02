"""Current CI selection must preserve registry staging, aliases and source pinning."""
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import current_plan_stage as C


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', '-C', str(repo), 'init', '-q'], check=True)
    subprocess.run(['git', '-C', str(repo), '-c', 'user.name=T', '-c', 'user.email=t@t',
                    'commit', '--allow-empty', '-qm', 'source'], check=True)
    sha = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    registry = tmp_path / 'registry.py'
    registry.write_text('# current registry\n')
    calls = []
    def materialize(root, plan_dir, src, overlays):
        calls.append(('plan', plan_dir, src, overlays))
        p = root / 'physical/die_plan' / plan_dir / 'por__source.json'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"partition_types": {}}')
        return p
    reg = SimpleNamespace(PLANS=[('s81_head', 's81_head', 'results/head/source.json', ('../../results/head/sidecars',)),
                                ('hbm', 'hbm/por', 'physical/die_plan/hbm/por/source.json.gz', ('hbm/base',))],
                          PIN_ALIASES={'s81_head': {'core.json': ('results/head/core.json', 'abc')}},
                          plan_archive_paths=lambda plans: ['tools'] + [p[2] for p in plans],
                          materialize_plan=materialize,
                          fetch_results_refs=lambda root, path, rev: calls.append(('refs', rev)) or ['results/ref.json'],
                          materialize_pin_aliases=lambda path, aliases, rev: calls.append(('aliases', aliases, rev)) or ['core.json'])
    monkeypatch.setattr(C, 'load_registry', lambda path: reg)
    return repo, registry, sha, reg, calls


def test_exact_selected_registry_paths_overlays_aliases_and_sha(inputs, tmp_path):
    repo, registry, sha, reg, calls = inputs
    seen = []
    out = tmp_path / 'stage'
    rec = C.stage(repo, 'HEAD', registry, out, 's81_head',
                  archive_fn=lambda *args: seen.append(args))
    assert list(rec['plans']) == ['s81_head']
    assert seen[0][1] == sha
    assert seen[0][2] == ['tools', 'results/head/source.json']
    assert ('plan', 's81_head', 'results/head/source.json', ('../../results/head/sidecars',)) in calls
    assert ('aliases', reg.PIN_ALIASES['s81_head'], sha) in calls
    assert ('refs', sha) in calls
    argv = rec['ci_static_argv']
    assert argv[argv.index('--g2') + 1] == 'none'
    assert argv[argv.index('--sta') + 1] == 'none'
    assert '--plan' in argv and 'die_plan.json' not in argv[-1]
    assert json.loads((out / 'current_plans.json').read_text())['sha'] == sha


def test_unknown_die_fails_before_extract(inputs, tmp_path):
    repo, registry, _, _, _ = inputs
    with pytest.raises(ValueError, match='unknown current die'):
        C.stage(repo, 'HEAD', registry, tmp_path / 'bad', 'old_b2l',
                archive_fn=lambda *args: pytest.fail('must not extract'))


def test_missing_alias_fails_without_manifest(inputs, tmp_path):
    repo, registry, _, reg, _ = inputs
    def bad(*a, **kw):
        raise RuntimeError('pin alias missing')
    reg.materialize_pin_aliases = bad
    out = tmp_path / 'failed'
    with pytest.raises(RuntimeError, match='pin alias missing'):
        C.stage(repo, 'HEAD', registry, out, 's81_head', archive_fn=lambda *a: None)
    assert not (out / 'current_plans.json').exists()


def test_never_overwrite_an_existing_stage(inputs, tmp_path):
    repo, registry, _, _, _ = inputs
    out = tmp_path / 'keep'
    out.mkdir()
    keep = out / 'original'
    keep.write_text('preserved')
    with pytest.raises(ValueError, match='absent or empty'):
        C.stage(repo, 'HEAD', registry, out, archive_fn=lambda *a: pytest.fail('must not extract'))
    assert keep.read_text() == 'preserved'


def test_invalid_rev_fails_before_extract(inputs, tmp_path):
    repo, registry, _, _, _ = inputs
    with pytest.raises(subprocess.CalledProcessError):
        C.stage(repo, 'missing-source', registry, tmp_path / 'bad',
                archive_fn=lambda *a: pytest.fail('must not extract'))
