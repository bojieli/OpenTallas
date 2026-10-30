"""resign.py writes the kind:resign PROVENANCE.json only for a SIGNED + LEC EQUIVALENT re-sign at a flow tag."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import resign

TAG = 'flow-20261030-a-kv'
RESIGN_KEYS = ('src_commit', 'flow_tag', 'routed_db', 'build_commit', 'lec')  # coord release_tree_plan.RESIGN_KEYS
BUILD = 'ab' * 20


def g(repo, *a):
    return subprocess.run(['git', '-C', str(repo)] + list(a), check=True, capture_output=True).stdout.decode().strip()


@pytest.fixture
def env(tmp_path):
    repo = tmp_path / 'repo'
    (repo / 'tools' / 'die_plan').mkdir(parents=True)
    for n in resign.TOOLS:
        (repo / 'tools' / 'die_plan' / n).write_text('# %s at tag\n' % n)
    g(tmp_path, 'init', '-q', str(repo))
    g(repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'add', '.')
    g(repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'tag tools')
    g(repo, 'tag', TAG)
    tools = tmp_path / 'tools'
    tools.mkdir()
    for n in resign.TOOLS:
        (tools / n).write_bytes((repo / 'tools' / 'die_plan' / n).read_bytes())
    kit = tmp_path / 'kit'
    base = kit / 'run' / 'results' / 'asap7' / 'hc_x' / 'base'
    base.mkdir(parents=True)
    (base / '6_final.odb').write_bytes(b'odb')
    (base / '6_final.v').write_text('module x; endmodule\n')
    (kit / 'PROVENANCE.json').write_text(json.dumps({'schema': 'kit_provenance.v1', 'provenance': {'commit': BUILD}}))
    d = kit / 'tag'
    (d / 'signoff').mkdir(parents=True)
    (d / 'lec').mkdir()
    (d / 'signoff' / 'signoff.json').write_text(json.dumps(
        {'name': 'hc_x', 'verdict': 'SIGNED', 'inputs': {'odb': str(base / '6_final.odb')}}))
    (d / 'lec' / 'lec.json').write_text(json.dumps({'verdict': 'EQUIVALENT'}))
    return dict(repo=str(repo), tools=str(tools), kit=str(kit), d=str(d), odb=str(base / '6_final.odb'),
                commit=g(repo, 'rev-parse', 'HEAD'))


def args(e, *extra):
    return ['provenance', '--kit', e['kit'], '--tag', TAG, '--dir', e['d'], '--repo', e['repo'],
            '--tools', e['tools']] + list(extra)


def test_writes_counter_record(env):
    assert resign.main(args(env, '--lane', 'T')) == 0
    p = json.loads(Path(env['d'], 'PROVENANCE.json').read_text())
    assert p['kind'] == 'resign' and p['verdict'] == 'SIGNED'
    assert all(p.get(k) for k in RESIGN_KEYS)
    assert p['src_commit'] == env['commit'] and p['flow_tag'] == TAG
    assert p['build_commit'] == BUILD and p['routed_db'] == env['odb']
    assert json.loads(Path(p['lec']).read_text())['verdict'] == 'EQUIVALENT'
    assert p['tag_tools']['sha256']['signoff.py'] and p['routed_db_sha256']


@pytest.mark.parametrize('mutate', ['not_signed', 'lec_fail', 'no_lec', 'db_missing', 'tool_drift', 'bad_tag',
                                    'other_db', 'no_build'])
def test_fails_closed(env, mutate):
    extra = []
    tag = TAG
    if mutate == 'not_signed':
        Path(env['d'], 'signoff', 'signoff.json').write_text(json.dumps({'verdict': 'NOT SIGNED', 'inputs': {'odb': env['odb']}}))
    elif mutate == 'lec_fail':
        Path(env['d'], 'lec', 'lec.json').write_text(json.dumps({'verdict': 'NOT_EQUIVALENT'}))
    elif mutate == 'no_lec':
        os.remove(os.path.join(env['d'], 'lec', 'lec.json'))
    elif mutate == 'db_missing':
        os.remove(env['odb'])
    elif mutate == 'tool_drift':
        Path(env['tools'], 'lec.py').write_text('# local edit\n')
    elif mutate == 'bad_tag':
        tag = 'flow-20261030-z-kv'  # well formed, not in the repo
    elif mutate == 'other_db':
        extra = ['--routed-db', os.path.join(env['kit'], 'other.odb')]
    elif mutate == 'no_build':
        os.remove(os.path.join(env['kit'], 'PROVENANCE.json'))
    a = args(env, *extra)
    a[a.index(TAG)] = tag
    assert resign.main(a) == 1
    assert not Path(env['d'], 'PROVENANCE.json').exists()


def test_tag_name_must_be_release_tag(env):
    with pytest.raises(resign.ResignError):
        resign.tag_commit(env['repo'], 'HEAD')


def test_explicit_build_commit_and_no_tools(env):
    os.remove(os.path.join(env['kit'], 'PROVENANCE.json'))
    a = ['provenance', '--kit', env['kit'], '--tag', TAG, '--dir', env['d'], '--repo', env['repo'],
         '--build-commit', 'cd' * 20, '--no-db-hash']
    assert resign.main(a) == 0
    p = json.loads(Path(env['d'], 'PROVENANCE.json').read_text())
    assert p['build_commit'] == 'cd' * 20 and 'tag_tools' not in p and 'routed_db_sha256' not in p


def test_run_dry_run_uses_kit_netlist_and_tag_tools(env, capsys):
    out = os.path.join(env['kit'], 'tag2')
    assert resign.main(['run', '--kit', env['kit'], '--tag', TAG, '--repo', env['repo'], '--tools', env['tools'],
                        '--out', out, '--dry-run']) == 0
    so, lec = capsys.readouterr().out.strip().splitlines()
    assert os.path.join(env['tools'], 'signoff.py') in so and '--out %s/signoff' % out in so
    assert '/work/run/results/asap7/hc_x/base/6_final.v' in lec and '/eco/lec' in lec


def test_run_refuses_drifted_tools_before_running(env):
    Path(env['tools'], 'signoff.py').write_text('# local edit\n')
    assert resign.main(['run', '--kit', env['kit'], '--tag', TAG, '--repo', env['repo'], '--tools', env['tools'],
                        '--out', os.path.join(env['kit'], 'tag3'), '--dry-run']) == 1
