#!/usr/bin/env python3
"""COUNT-SCAN-1 2026-11-07: the SIGNED scan on a loaded host, and credit when it cannot finish. Run: python3 -m pytest -q"""
import json, os, pathlib, subprocess, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_tree_plan as R


def rec(root, rel, verdict='SIGNED', name='dp_x'):
    p = pathlib.Path(root) / rel / 'signoff' / 'signoff.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(verdict=verdict, name=name, src_commit='abc', flow_tag='flow-20261106-a-s81')))
    return str(p)


def scan(monkeypatch, roots, known=()):
    monkeypatch.setattr(R, 'SCAN_ROOTS', roots)
    R.PARTIAL.clear()
    return R.scan_host('local', known)


def test_walk_finds_records_and_skips_unsigned(tmp_path, monkeypatch):
    a = rec(tmp_path, 'k1'); rec(tmp_path, 'k2', verdict='FAIL')
    got = scan(monkeypatch, str(tmp_path))
    assert [r['path'] for r in got] == [a] and got[0]['scan_host'] == 'local' and got[0]['versioned']
    assert not R.PARTIAL


def test_same_root_is_walked_once_first_name_wins(tmp_path, monkeypatch):
    """bind mount of scratch-root at scratch3 on every host: same dev:inode.  A symlink root is a root of its own, as before."""
    a = rec(tmp_path / 'r', 'k1')
    cmd = R.scan_cmd(roots='%s %s/ %s/../r' % (tmp_path / 'r', tmp_path / 'r', tmp_path / 'r'), walk_s=30)
    r = subprocess.run(['bash', '-c', cmd], input='', capture_output=True, text=True, timeout=60)
    assert [x['path'] for x in json.loads(r.stdout.strip().splitlines()[-1])] == [a]


def test_pruned_trees_are_not_walked_but_a_known_record_there_is_read(tmp_path, monkeypatch):
    keep = rec(tmp_path, 'physical/die_plan/s81/views/k1')
    pruned = rec(tmp_path, 'wt/rtl/k2')
    assert [r['path'] for r in scan(monkeypatch, str(tmp_path))] == [keep]
    assert sorted(r['path'] for r in scan(monkeypatch, str(tmp_path), [pruned])) == sorted([keep, pruned])


def test_legacy_specs_views_are_walked(tmp_path, monkeypatch):
    """167 records live below physical/die_plan/s81/cores/legacy/specs: a first prune list held 'specs' and missed new ones"""
    a = rec(tmp_path, 'physical/die_plan/s81/cores/legacy/specs/x_vA/views/x')
    assert [r['path'] for r in scan(monkeypatch, str(tmp_path))] == [a]


def test_duplicate_root_reaches_find_once(tmp_path, monkeypatch):
    """SCAN_PY also drops duplicates, so look at what find itself was asked to walk"""
    (tmp_path / 'r').mkdir()
    log = tmp_path / 'args'
    fake_find(tmp_path, monkeypatch, 'echo "$@" > %s' % log)
    scan(monkeypatch, '%s %s/../r %s' % (tmp_path / 'r', tmp_path / 'r', tmp_path / 'gone'))
    assert log.read_text().split()[:2] == [str(tmp_path / 'r'), '-xdev']


def test_missing_roots_do_not_walk_the_cwd(tmp_path):
    rec(tmp_path, 'k1')
    r = subprocess.run(['bash', '-c', R.scan_cmd(roots=str(tmp_path / 'gone'), walk_s=30)], input='', capture_output=True,
                       text=True, timeout=60, cwd=tmp_path)
    assert json.loads(r.stdout.strip().splitlines()[-1]) == []


def test_known_path_is_read_once_and_alias_adds_nothing(tmp_path, monkeypatch):
    a = rec(tmp_path / 'r', 'k1')
    (tmp_path / 'alias').symlink_to(tmp_path / 'r')
    alias = str(tmp_path / 'alias' / 'k1' / 'signoff' / 'signoff.json')
    assert [r['path'] for r in scan(monkeypatch, str(tmp_path / 'r'), [alias, a])] == [a]


def test_hard_linked_record_in_another_kit_stays(tmp_path, monkeypatch):
    a = rec(tmp_path, 'k1')
    b = tmp_path / 'k2' / 'signoff' / 'signoff.json'; b.parent.mkdir(parents=True); os.link(a, b)
    assert sorted(r['path'] for r in scan(monkeypatch, str(tmp_path))) == sorted([a, str(b)])


def fake_find(tmp_path, monkeypatch, body):
    d = tmp_path / 'bin'; d.mkdir(exist_ok=True)
    (d / 'find').write_text('#!/bin/bash\n' + body + '\n'); (d / 'find').chmod(0o755)
    monkeypatch.setenv('PATH', '%s:%s' % (d, os.environ['PATH']))


def test_cut_walk_keeps_known_records_and_drops_a_gone_one(tmp_path, monkeypatch):
    """the walk hits its budget: a known record still counts because it was read; a known file that is gone is a real change"""
    a = rec(tmp_path / 'r', 'k1')
    new = rec(tmp_path / 'r', 'k2')
    fake_find(tmp_path, monkeypatch, 'echo %s; exec sleep 60' % new)
    monkeypatch.setattr(R, 'SCAN_WALK_S', 1)
    t0 = time.time()
    got = scan(monkeypatch, str(tmp_path / 'r'), [a, str(tmp_path / 'gone' / 'signoff.json')])
    assert time.time() - t0 < 30
    assert R.PARTIAL == {'local'}
    assert sorted(r['path'] for r in got) == sorted([a, new])


def test_find_error_rc_is_a_full_walk(tmp_path, monkeypatch):
    a = rec(tmp_path, 'k1')
    fake_find(tmp_path, monkeypatch, 'echo %s; exit 1' % a)   # rc 1 = a directory vanished under a running delete
    assert [r['path'] for r in scan(monkeypatch, str(tmp_path))] == [a] and not R.PARTIAL


def test_scan_timeout_is_not_retried_and_counts_as_down(monkeypatch):
    calls = []

    def boom(cmd, timeout, **kw):
        calls.append(timeout); raise subprocess.TimeoutExpired(cmd, timeout)
    monkeypatch.setattr(R, 'sh', boom)
    try:
        R.scan_host('epyc4')
        assert False
    except subprocess.TimeoutExpired:
        pass
    assert calls == [R.SCAN_SSH_S]


def test_known_paths_from_records_and_carried_refs():
    old = dict(signed_records=[dict(scan_host='epyc4', path='/a/signoff.json'), dict(scan_host='intel1', path='/b/signoff.json')],
               plans={'p': dict(signed_types={'t': ['epyc4:/c/signoff.json src 1 flow f RE-SIGN build 2 db /d.odb', 'results/x.json src 1']},
                                signed_designs={'d': ['epyc4:/e/signoff.json src 1 flow f DESIGN-MATCH pins [host-unreachable, last verified x]']})})
    assert R.known_paths(old, 'epyc4') == ['/a/signoff.json', '/c/signoff.json', '/e/signoff.json']
    assert R.known_paths(None, 'epyc4') == []


def _plan(**kw):
    return dict(die='s81', plan_types={'t1': 'mt1', 't2': 'mt2', 't3': 'mt3', 't4': 'mt4'}, designs={}, signed_designs={}, signed_types={}, **kw)


def test_carry_keeps_types_of_a_down_host():
    """the 194 -> 192 drop: slice_station__t46, __t7__cl945bc067, hd_spn_wshim_tx were types on epyc4"""
    old = dict(generated=0, plans={'p': dict(_plan(), signed_types={
        't1': ['epyc4:/x/t1/signoff.json src 1 flow f'],                                  # only on the down host: carried
        't2': ['epyc4:/x/t2/signoff.json src 1 flow f', 'intel1:/x/t2/signoff.json src 1 flow f'],   # other host read, gone there
        't3': ['epyc4:/x/t3/signoff.json src 1 flow f'],                                  # retired by path
        't4': ['epyc4:/x/t4/signoff.json src 1 flow f'],                                  # retired by name, after verification
        'old': ['epyc4:/x/o/signoff.json src 1 flow f']})})                               # no longer in the plan
    new = dict(unreachable_hosts=['epyc4'], plans={'p': dict(_plan(), unversioned_types={'t1': ['epyc4:/u']})})
    out = R.carry_unreachable(new, old, retired={'epyc4:/x/t3/signoff.json': 'r'}, names={('s81', 'mt4'): (10, 'why')})
    st = out['plans']['p']['signed_types']
    assert list(st) == ['t1'] and R.UNREACH_TAG in st['t1'][0]
    assert out['plans']['p']['unversioned_types'] == {}
    assert out['carried_unreachable'][0]['type'] == 't1' and out['carried_unreachable'][0]['hosts'] == ['epyc4']
    # a second failed refresh keeps the first verification time
    again = R.carry_unreachable(dict(unreachable_hosts=['epyc4'], plans={'p': _plan()}), dict(out, generated=10 ** 9), retired={}, names={})
    assert again['plans']['p']['signed_types']['t1'] == st['t1']
    # host read again and the record gone: not carried
    assert R.carry_unreachable(dict(unreachable_hosts=[], plans={'p': _plan()}), old)['plans']['p']['signed_types'] == {}


def test_carry_with_no_designs_in_old_still_carries_types():
    old = dict(generated=0, plans={'p': dict(_plan(), signed_types={'t1': ['epyc4:/x signoff']}, signed_designs={})})
    out = R.carry_unreachable(dict(unreachable_hosts=['epyc4'], plans={'p': _plan()}), old, retired={}, names={})
    assert 't1' in out['plans']['p']['signed_types']
