"""WAVE-OPS-1 nightly wave-source rebuild tests. Run: python3 -I lanes/wave-ops-1/test_wave_src.py"""
import importlib.util, json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + '.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
R = load('wave_src_remote')
N = load('nightly_wave_src')


def sh(*a, cwd=None):
    return subprocess.run(a, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def repo(t):
    r = os.path.join(t, 'repo'); os.makedirs(r)
    g = lambda *a: sh('git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a, cwd=r)
    g('init', '-q', '-b', 'main')
    def write(p, s):
        os.makedirs(os.path.dirname(os.path.join(r, p)) or r, exist_ok=True)
        open(os.path.join(r, p), 'w').write(s)
    for p in ('a.txt', 'b.txt', 'c.txt', 'd.txt', 'tools/x.py'):
        write(p, 'l1\nl2\nl3\nl4\nl5\n' + p + '\n')
    g('add', '-A'); g('commit', '-qm', 'base'); base = g('rev-parse', 'HEAD')
    write('a.txt', 'l1 main\nl2\nl3\nl4\nl5\na.txt\n')            # main changes a, c, deletes d, adds e
    write('c.txt', 'l1 main\nl2\nl3\nl4\nl5\nc.txt\n')
    os.unlink(os.path.join(r, 'd.txt')); write('e.txt', 'new\n')
    g('add', '-A'); g('commit', '-qm', 'main'); main = g('rev-parse', 'HEAD')
    g('checkout', '-q', '-b', 'ov', base)                          # an overlay branch: adds f, edits x
    write('f.txt', 'ov\n'); write('tools/x.py', 'l1\nl2\nl3\nl4\nl5 ov\ntools/x.py\n')
    g('add', '-A'); g('commit', '-qm', 'ov'); ov = g('rev-parse', 'HEAD')
    g('checkout', '-q', '-b', 'bad', base)                         # conflicts with main on a.txt line 1
    write('a.txt', 'l1 bad\nl2\nl3\nl4\nl5\na.txt\n'); g('add', '-A'); g('commit', '-qm', 'bad'); bad = g('rev-parse', 'HEAD')
    g('checkout', '-q', 'main')
    return r, base, main, ov, bad


def test_manifest_matches_git():
    with tempfile.TemporaryDirectory() as t:
        r, base, main, ov, bad = repo(t)
        m = R.manifest(r)
        for p in ('a.txt', 'tools/x.py', 'e.txt'):
            assert m[p][1] == sh('git', 'hash-object', p, cwd=r)
        cache = os.path.join(t, 'c.tsv')
        assert R.manifest(r, cache) == m and R.manifest(r, cache) == m and os.path.getsize(cache) > 0
        os.symlink('a.txt', os.path.join(r, 'ln'))
        assert R.manifest(r)['ln'][0] == R.MODE_L


def test_compose_and_classify_materialize_verify():
    with tempfile.TemporaryDirectory() as t:
        r, base, main, ov, bad = repo(t)
        spec = dict(main=main, overlays=[dict(name='ov', sha=ov[:12]), dict(name='bad', sha=bad),
                                         dict(name='old', sha=base), dict(name='gone', sha='deadbeef' * 5)],
                    dies=dict(d1=base), branch_prefix='refs/wave-src/t', worktree=os.path.join(t, 'wt'))
        res = R.compose(r, spec)
        st = {o['name']: o['status'] for o in res['overlays']}
        assert st == {'ov': 'merged', 'bad': 'conflict (not applied)', 'old': 'on main',
                      'gone': 'missing (not fetched)'}, st
        new = res['dies']['d1']['sha']
        assert res['dies']['d1']['die_branch'] == 'on main/overlays' and not os.path.exists(spec['worktree'])
        # the live tree = base checkout + a live overlay on b, a live-only file, a live edit of c (main edited c too,
        # other line), and results/ absent (sparse)
        live = os.path.join(t, 'live'); os.makedirs(live)
        sh('git', '-C', r, 'archive', '-o', os.path.join(t, 'b.tar'), base); sh('tar', '-xf', os.path.join(t, 'b.tar'), '-C', live)
        open(os.path.join(live, 'b.txt'), 'w').write('l1\nl2\nl3\nl4\nl5 live\nb.txt\n')
        open(os.path.join(live, 'only_live.json'), 'w').write('{}\n')
        open(os.path.join(live, 'c.txt'), 'w').write('l1\nl2\nl3\nl4\nl5 live\nc.txt\n')
        os.chmod(live, 0o555)                                       # read-only live tree: never written
        lm = R.manifest(live)
        rb = lambda p: open(os.path.join(live, p), 'rb').read()
        c = R.classify(lm, R.ls_tree(r, base), R.ls_tree(r, new), rb, r)
        ops = {a['path']: a['op'] for a in c['actions']}
        assert ops == {'a.txt': 'write', 'd.txt': 'delete', 'e.txt': 'write', 'f.txt': 'write', 'tools/x.py': 'write',
                       'c.txt': 'text'}, ops
        assert sorted(c['carried']) == ['b.txt', 'only_live.json'] and c['merged'] == ['c.txt'] and not c['conflicts']
        tar = os.path.join(t, 'p.tar'); R.pack(r, c['actions'], tar)
        newt = os.path.join(t, 'out', 'd1')
        R.materialize(live, newt, c['actions'], tar)
        exp = R.expected_manifest(lm, c['actions'])
        v = R.verify(newt, exp)
        assert v['ok'], v
        assert open(os.path.join(newt, 'c.txt')).read() == 'l1 main\nl2\nl3\nl4\nl5 live\nc.txt\n'
        assert open(os.path.join(live, 'a.txt')).read().startswith('l1\n')     # live untouched
        assert os.stat(os.path.join(newt, 'b.txt')).st_ino == os.stat(os.path.join(live, 'b.txt')).st_ino
        assert os.stat(os.path.join(newt, 'a.txt')).st_ino != os.stat(os.path.join(live, 'a.txt')).st_ino
        try:
            R.materialize(live, newt, c['actions'], tar); assert False
        except RuntimeError:
            pass                                                    # never overwrites an existing tree
        os.chmod(live, 0o755)


def test_classify_conflict_kept_live():
    L = {'x': ('100644', 'l')}; B = {'x': ('100644', 'b')}; Nn = {'x': ('100644', 'n')}
    c = R.classify(L, B, Nn)                       # no bytes reader -> conflict, live kept (no action)
    assert c['conflicts'] == ['x'] and not c['actions']
    c = R.classify({}, {'results/big': ('100644', 'b')}, {'results/big': ('100644', 'n')})
    assert not c['actions'] and c['counts'] == {'sparse (absent live, kept absent)': 1}
    c = R.classify({}, {'tools/x.py': ('100644', 'b')}, {'tools/x.py': ('100644', 'n')})
    assert [a['op'] for a in c['actions']] == ['write'] and c['counts'] == {'restored (in the commit, absent live)': 1}


def test_unmerged_die_branch_keeps_its_changes():
    S_ = {'d': ('100644', 'dd'), 'm': ('100644', 'm0'), 'x': ('100644', 'x1')}     # die branch tip
    M_ = {'m': ('100644', 'm0'), 'x': ('100644', 'x0')}                            # merge-base: d added, x changed by die
    N_ = {'m': ('100644', 'm1'), 'x': ('100644', 'x0')}                            # main changed m only
    c = R.classify(dict(S_), S_, N_, mbase=M_)
    assert {a['path']: a['op'] for a in c['actions']} == {'m': 'write'}
    assert sorted(c['carried']) == ['d', 'x'] and not c['conflicts']


def test_parse_train_and_kw44():
    q = ('- 11-10 18:14 ROOT-MERGE-57 UNLANDED (approved, not on main; main=a8a7f27eb031), in landing order: land-reserve '
         'f99ba4416be1 (gate met); n4x overlay 135427e515e5; stm-dupq 161d17842f04 + 577fce65b7b9; ft-hop-lockup '
         'bc6a24d60785. Out of stack under the owner rule (test fail by name): he-epc b4525acb6f, waiting. Held: q3bc-cf2 '
         '4b05cf2eb7 (inputs). Refused: idxface 31a9f700ca0.\n')
    tr = N.parse_train(q)
    assert [(o['name'], o['sha']) for o in tr['overlays']] == [
        ('land-reserve', 'f99ba4416be1'), ('n4x overlay', '135427e515e5'), ('stm-dupq', '161d17842f04'),
        ('stm-dupq', '577fce65b7b9'), ('ft-hop-lockup', 'bc6a24d60785')]
    assert [x['sha'] for x in tr['excluded']] == ['b4525acb6f', '4b05cf2eb7', '31a9f700ca0']
    assert tr['main'] == 'a8a7f27eb031'
    k = ('## [KW44-READY-EARLY-GRID-1110] KW-FIX-44 2026-11-10 18:24 PST: GRT-EARLY READY\n'
         '1. READY for ROOT-MERGE-57: GRT-EARLY on branch claude/kw-fix-44-grt-early-1110 @ b6d8a28df457 (child).\n'
         '   - LIVE ~18:15: grt183_make.sh in every die src\n'
         '- 2026-11-10 18:30 PST STATE [OTHER -> COORD] claude/other-1110 @ 0123456789ab\n')
    ks = N.parse_kw44(k, now_s=N.ts('2026-11-10 20:00'))
    assert [(o['name'], o['sha']) for o in ks] == [('claude/kw-fix-44-grt-early-1110', 'b6d8a28df457')]
    assert N.parse_kw44(k, now_s=N.ts('2026-11-14 20:00')) == []          # older than the window


def test_rebind_cmd_and_asbuilt():
    d = dict(plan='/p/plan.json', kit_rtl=dict(mode='bind', asbuilt='/a/asb.json', bind_out='/b/old'))
    c = N.bind_job('qwen_kvsys', d, '/new/tree', '/out/bind')
    assert c['asbuilt'] == '/a/asb.json' and c['plan'] == '/p/plan.json'
    assert 'tools/die_plan/bind.py all /p/plan.json --out /out/bind --asbuilt /a/asb.json --strict --mem 32' in c['cmd']
    assert '--memory 64g' in c['cmd'] and '-v /srv/opentallas-scratch2:/srv/opentallas-scratch2:ro' in c['cmd']
    s = N.bind_job('s81', dict(plan='/p', kit_rtl=dict(mode='script', script='/s.sh')), '/n', '/o',
                   script_text='export S81_BIND_OUT=/x/bind8\nS81_ASBUILT=/y/asb.json\n')
    assert s['old_bind'] == '/x/bind8' and s['asbuilt'] == '/y/asb.json'
    h = N.bind_job('s81_head', dict(plan='/p', kit_rtl=dict(mode='script', script='/h.sh')), '/n', '/o', script_text='')
    assert h['cmd'] is None and 'no strict bind' in h['why']


def test_stale_old_git_copy_takes_commit():
    # COORD 11-10 HBM recipes.json: the live file is an OLD git version (on main history), main == die branch:
    # it used to be carried as a live overlay; now the commit wins.  A real live-only edit is still carried.
    with tempfile.TemporaryDirectory() as t:
        r, base, main, ov, bad = repo(t)
        live = os.path.join(t, 'live'); os.makedirs(live)
        sh('git', '-C', r, 'archive', '-o', os.path.join(t, 'm.tar'), main); sh('tar', '-xf', os.path.join(t, 'm.tar'), '-C', live)
        open(os.path.join(live, 'a.txt'), 'w').write('l1\nl2\nl3\nl4\nl5\na.txt\n')        # base-era copy of a
        open(os.path.join(live, 'b.txt'), 'w').write('l1\nl2\nl3\nl4\nl5 hand\nb.txt\n')    # hand edit (not in git)
        open(os.path.join(live, 'd.txt'), 'w').write('l1\nl2\nl3\nl4\nl5\nd.txt\n')         # deleted on main, old copy
        lm = R.manifest(live)
        bv = nv = R.ls_tree(r, main)
        hist = R.path_history(r, [main, main], R.lag_candidates(lm, bv, nv))
        c = R.classify(lm, bv, nv, None, r, None, hist)
        ops = {a['path']: a['op'] for a in c['actions']}
        assert ops == {'a.txt': 'write', 'd.txt': 'delete'}, ops
        assert sorted(c['lag']) == ['a.txt', 'd.txt'] and c['carried'] == ['b.txt'], c
        c0 = R.classify(lm, bv, nv, None, r, None, None)                     # old behaviour without history
        assert sorted(c0['carried']) == ['a.txt', 'b.txt', 'd.txt'], c0['carried']


def test_src_check_categories():
    with tempfile.TemporaryDirectory() as t:
        r, base, main, ov, bad = repo(t)
        live = os.path.join(t, 'live'); os.makedirs(live)
        sh('git', '-C', r, 'archive', '-o', os.path.join(t, 'm.tar'), main); sh('tar', '-xf', os.path.join(t, 'm.tar'), '-C', live)
        open(os.path.join(live, 'a.txt'), 'w').write('l1\nl2\nl3\nl4\nl5\na.txt\n')        # old git copy
        open(os.path.join(live, 'b.txt'), 'w').write('hand\n')                                 # modified, not in git
        open(os.path.join(live, 'run.json'), 'w').write('{}\n')                               # live-only
        os.unlink(os.path.join(live, 'e.txt'))                                                 # missing
        lm = R.manifest(live); bv = R.ls_tree(r, main)
        c = R.src_check(lm, bv, bv, R.path_history(r, [main], sorted(lm)))
        assert c == dict(stale=['a.txt'], modified=['b.txt'], live_only=['run.json'], missing=1), c


def test_switch_checks():
    # COORD 11-10 21:22 standing SWITCH-OK: (a) tests + KEPT LIVE owners, (b) re-bind, (c) running kits, (e) provenance
    calls = []
    def fake_ssh(host, cmd, timeout=600, check=True, input=None):
        calls.append(cmd)
        if ' owners ' in cmd:
            return '{"tools/x.py": "KW-FIX-44", "tools/y.py": ""}\n'
        if 'ls-remote' in cmd:
            return 'abc123 refs/heads/wave-src/d/s81\n'
        return ''
    o_ssh, o_tag, o_hand = N.ssh, N.flow_tag_for, N.hand_owners
    try:
        N.ssh = fake_ssh; N.flow_tag_for = lambda sha, die: 'flow-20261111-a-s81'
        N.hand_owners = lambda: {('s81', 'tools/y.py'): 'S81-SVCRS-3'}
        r = dict(conflicts=['tools/x.py', 'tools/y.py'], src='/l', new_sha='abc123', bind_state='ok', rebound=['t1'])
        cfg = {'dies': {'s81': {'retry': ['a@1', 'b@2']}}}
        st = {'items': {'k': {'die': 's81', 'item': 'b', 'attempt': 3, 'status': 'RUNNING'}}}
        ok, cl, owner = N.switch_checks('d', 's81', r, cfg, st, (True, '8 passed'))
        assert ok and owner is None, cl
        assert r['kept_live_owners'] == {'tools/x.py': 'KW-FIX-44', 'tools/y.py': 'S81-SVCRS-3'}
        assert any('KW-FIX-43 re-bind batch' in c for c in cl)
        st['items']['k']['attempt'] = 2                    # a retry entry names a live attempt -> (c) fails
        ok, cl, owner = N.switch_checks('d', 's81', r, cfg, st, (True, '8 passed'))
        assert not ok and owner == 'KW-FIX-43', cl
        N.hand_owners = lambda: {}                          # an unowned KEPT LIVE file -> (a) fails first
        st['items']['k']['attempt'] = 3
        ok, cl, owner = N.switch_checks('d', 's81', r, cfg, st, (True, '8 passed'))
        assert not ok and owner == 'COORD' and any('no owner for tools/y.py' in c for c in cl), cl
        N.flow_tag_for = lambda sha, die: ''
        N.hand_owners = lambda: {('s81', 'tools/y.py'): 'X-1'}
        ok, cl, owner = N.switch_checks('d', 's81', r, cfg, st, (True, '8 passed'))
        assert not ok and owner == 'ROOT-MERGE-57', cl
        r['bind_state'] = 'failed'
        ok, cl, owner = N.switch_checks('d', 's81', r, cfg, st, (True, '8 passed'))
        assert not ok and owner == 'S81 die owner', cl
    finally:
        N.ssh, N.flow_tag_for, N.hand_owners = o_ssh, o_tag, o_hand


def test_kept_owner_tags():
    with tempfile.TemporaryDirectory() as t:
        r, base, main, ov, bad = repo(t)
        live = os.path.join(t, 'live'); os.makedirs(os.path.join(live, 'tools'))
        open(os.path.join(live, 'tools/x.py'), 'w').write('l1\n# KW-FIX-44 11-10 hand fix\nx = 1  # KW-FIX-44\n# DIE-KV-97 note\n')
        o = R.kept_owners(r, live, main, ['tools/x.py', 'tools/none.py'])
        assert o['tools/x.py']['owner'] == 'KW-FIX-44' and o['tools/none.py']['owner'] == '', o


if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f(); n += 1
    print('%d passed' % n)
