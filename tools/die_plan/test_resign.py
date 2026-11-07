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
    _with_clock_family(env)
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


def _with_clock_family(env, text='# clock family at tag\n'):
    repo = Path(env['repo'])
    (repo / 'physical' / 'common_flow').mkdir(parents=True)
    (repo / 'physical' / 'common_flow' / 'clock_family.tcl').write_text(text)
    g(repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'add', '.')
    g(repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'clock family')
    g(repo, 'tag', '-f', TAG)


def _run_dry(env):
    return resign.main(['run', '--kit', env['kit'], '--tag', TAG, '--repo', env['repo'], '--tools', env['tools'],
                        '--out', env['d'] + '_run', '--dry-run'])


def test_run_exports_clock_family_from_the_tag(env, capsys):
    # DIE-HEAD-44 10-30: 'git archive TAG tools' lacks physical/common_flow/clock_family.tcl -> tag sign-off failed
    _with_clock_family(env)
    assert _run_dry(env) == 0
    assert Path(env['tools'], 'clock_family.tcl').read_text() == '# clock family at tag\n'
    assert _run_dry(env) == 0          # second run: the exported copy is byte-checked, not rewritten


def test_run_fails_clearly_without_clock_family_at_the_tag(env, capsys):
    assert _run_dry(env) == 1
    assert 'has no tools/die_plan/clock_family.tcl or physical/common_flow/clock_family.tcl' in capsys.readouterr().err
    assert not Path(env['tools'], 'clock_family.tcl').exists()


def test_run_refuses_a_different_clock_family_in_place(env, capsys):
    _with_clock_family(env)
    Path(env['tools'], 'clock_family.tcl').write_text('# hand-copied other version\n')
    assert _run_dry(env) == 1
    assert 'differs from %s clock_family.tcl' % TAG in capsys.readouterr().err


# ---------------------------------------------------------------- auto form (FLOW-29 11-04): unattended, stricter
GATES = {k: {'verdict': 'PASS'} for k in ('setup_tt', 'hold_ff', 'drv', 'clock', 'drc', 'antenna', 'pg')}


def _auto_ready(env, verdict='SIGNED', **so):
    rec = {'name': 'hc_x', 'verdict': verdict, 'local_verdict': 'SIGNED', 'inputs': {'odb': env['odb']}, 'checks': GATES}
    rec.update(so)
    Path(env['d'], 'signoff', 'signoff.json').write_text(json.dumps(rec))
    Path(env['d'], 'lec', 'lec.json').write_text(json.dumps({'verdict': 'EQUIVALENT', 'superset_vec': {'all_shown': True}}))


def _manifest(env, tmp_path):
    m = tmp_path / 'tag_manifest.json'
    files = {'tools/die_plan/' + n: resign.sha256(os.path.join(env['repo'], 'tools', 'die_plan', n)) for n in resign.TOOLS}
    m.write_text(json.dumps({'schema': resign.MANIFEST_SCHEMA, 'tag': TAG, 'commit': env['commit'], 'files': files}))
    return str(m)


def test_auto_accepts_needs_parent_only(env):
    _auto_ready(env, 'LOCAL_PASS_NEEDS_PARENT', reasons=['io_hold_parent: NEEDS_PARENT; receipt missing'])
    r = resign.build_record(env['d'], env['kit'], TAG, repo=env['repo'], tools=env['tools'], auto=True)
    assert r['verdict'] == 'SIGNED' and 'LOCAL_PASS_NEEDS_PARENT' in r['verdict_basis']


def test_hand_form_still_refuses_needs_parent(env):
    _auto_ready(env, 'LOCAL_PASS_NEEDS_PARENT', reasons=['io_hold_parent: NEEDS_PARENT'])
    with pytest.raises(resign.ResignError):
        resign.build_record(env['d'], env['kit'], TAG, repo=env['repo'], tools=env['tools'])


@pytest.mark.parametrize('case', ['other_reason', 'local_fail', 'gate_fail', 'gate_missing', 'not_shown', 'no_superset'])
def test_auto_is_stricter(env, case):
    _auto_ready(env)
    so = Path(env['d'], 'signoff', 'signoff.json')
    rec = json.loads(so.read_text())
    if case == 'other_reason':
        rec.update(verdict='LOCAL_PASS_NEEDS_PARENT', reasons=['io_hold_parent: NEEDS_PARENT', 'drc: 3'])
    elif case == 'local_fail':
        rec.update(verdict='LOCAL_PASS_NEEDS_PARENT', local_verdict='NOT SIGNED', reasons=['io_hold_parent: x'])
    elif case == 'gate_fail':
        rec['checks'] = dict(GATES, hold_ff={'verdict': 'FAIL'})
    elif case == 'gate_missing':
        rec['checks'] = {k: v for k, v in GATES.items() if k != 'pg'}
    so.write_text(json.dumps(rec))
    lec = Path(env['d'], 'lec', 'lec.json')
    if case == 'not_shown':
        lec.write_text(json.dumps({'verdict': 'EQUIVALENT', 'superset_vec': {'all_shown': False}}))
    elif case == 'no_superset':
        lec.write_text(json.dumps({'verdict': 'EQUIVALENT'}))
    with pytest.raises(resign.ResignError):
        resign.build_record(env['d'], env['kit'], TAG, repo=env['repo'], tools=env['tools'], auto=True)


def test_manifest_stands_in_for_the_repo_and_catches_drift(env, tmp_path):
    _auto_ready(env)
    m = _manifest(env, tmp_path)
    r = resign.build_record(env['d'], env['kit'], TAG, repo=m, tools=env['tools'], auto=True)
    assert r['src_commit'] == env['commit']
    Path(env['tools'], resign.TOOLS[0]).write_text('# drifted\n')
    with pytest.raises(resign.ResignError):
        resign.build_record(env['d'], env['kit'], TAG, repo=m, tools=env['tools'], auto=True)


def test_manifest_of_another_tag_refused(env, tmp_path):
    _auto_ready(env)
    m = json.loads(Path(_manifest(env, tmp_path)).read_text())
    m['tag'] = 'flow-20261030-b-kv'
    p = tmp_path / 'other.json'
    p.write_text(json.dumps(m))
    with pytest.raises(resign.ResignError):
        resign.build_record(env['d'], env['kit'], TAG, repo=str(p), tools=env['tools'], auto=True)


def test_mark_keep_adds_to_an_existing_keep(env):
    Path(env['kit'], '.keep').write_text('lane note\n')
    rec = dict(routed_db=env['odb'], flow_tag=TAG, lane='AUTO-RESIGN', created='now')
    resign.mark_keep(rec, env['d'], env['kit'])
    assert Path(env['kit'], '.keep').read_text().startswith('lane note\nsigned DB ')
    assert env['odb'] in Path(env['d'], '.keep').read_text()


def test_auto_run_superset_env_set_and_raw_base_not(env):
    cmds = resign.run_cmds(env['kit'], env['kit'] + '/run', env['tools'], env['d'], 'img', 'hc_x', superset=True)
    text = ' '.join(' '.join(c) for c in cmds)
    assert 'OT_LEC_SUPERSET_VEC=1' in text and 'OT_LEC_RAW_BASE_STEPS' not in text


def test_build_commit_from_freeze_repo_rev(env):
    """S81-COLLE-4 11-06: a kit whose only commit record is freeze.json repo_rev (abbreviated) still gets its record."""
    kit = Path(env['kit'])
    (kit / 'PROVENANCE.json').unlink()
    (kit / 'freeze.json').write_text(json.dumps({'schema': 'partition_freeze', 'repo_rev': env['commit'][:11]}))
    assert resign.kit_build_commit(env['kit']) is None                      # no repo: cannot resolve a short rev
    assert resign.kit_build_commit(env['kit'], env['repo']) == env['commit']
    assert resign.main(args(env)) == 0
    rec = json.loads((Path(env['d']) / 'PROVENANCE.json').read_text())
    assert rec['build_commit'] == env['commit']


def test_freeze_repo_rev_unknown_commit_still_refused(env):
    kit = Path(env['kit'])
    (kit / 'PROVENANCE.json').unlink()
    (kit / 'freeze.json').write_text(json.dumps({'repo_rev': 'deadbeef123'}))
    assert resign.kit_build_commit(env['kit'], env['repo']) is None
    assert resign.main(args(env)) != 0
    assert not (Path(env['d']) / 'PROVENANCE.json').exists()
