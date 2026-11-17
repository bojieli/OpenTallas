#!/usr/bin/env python3
"""RTPTMP_1101: release_tree_plan.py scratch dirs never pile up in /tmp. Run: python3 -m pytest -q"""
import os, pathlib, subprocess, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_tree_plan as R


def mk(root, name, age_s):
    d = root / name
    (d / 'tools').mkdir(parents=True)
    (d / 'tools' / 'x').write_text('x')
    t = time.time() - age_s
    os.utime(d, (t, t))
    return d


def test_sweep_removes_old_dead_or_unnamed_keeps_live_and_young(tmp_path):
    dead = subprocess.Popen(['true']); dead.wait()
    old_dead = mk(tmp_path, '%s%d.abc' % (R.TMP_PREFIX, dead.pid), 3 * 3600)
    old_legacy = mk(tmp_path, R.TMP_PREFIX + 'f9qd__ib', 3 * 3600)
    old_live = mk(tmp_path, '%s%d.def' % (R.TMP_PREFIX, os.getpid()), 3 * 3600)
    young = mk(tmp_path, R.TMP_PREFIX + 'young', 600)
    other = mk(tmp_path, 'something-else', 3 * 3600)
    gone = R.sweep_stale_tmp(tmp_path)
    assert sorted(gone) == sorted([str(old_dead), str(old_legacy)])
    assert old_live.exists() and young.exists() and other.exists()
    assert not old_dead.exists() and not old_legacy.exists()


def test_refresh_removes_its_scratch_dir_even_on_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(R.tempfile, 'tempdir', str(tmp_path))
    monkeypatch.setattr(R, 'plan_archive_paths', lambda: (_ for _ in ()).throw(RuntimeError('boom')))
    monkeypatch.setattr(R, 'sh', lambda *a, **k: subprocess.CompletedProcess(a, 0, 'abc\n', ''))
    res = R.refresh()
    assert any('boom' in e for e in res['errors'])
    assert not list(tmp_path.glob(R.TMP_PREFIX + '*'))


def test_sigterm_unwinds_through_rmtree(tmp_path):
    code = ('import sys, time, pathlib; sys.path.insert(0, %r); import release_tree_plan as R, tempfile; '
            'tempfile.tempdir = %r; R.sh = lambda *a, **k: __import__("subprocess").CompletedProcess(a, 0, "x\\n", ""); '
            'R.plan_archive_paths = lambda: (print("IN", flush=True), time.sleep(60), [])[2]; R.refresh()'
            % (str(pathlib.Path(R.__file__).parent), str(tmp_path)))
    p = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE, text=True)
    assert p.stdout.readline().strip() == 'IN'
    assert list(tmp_path.glob(R.TMP_PREFIX + '%d.*' % p.pid))
    p.terminate()
    assert p.wait(30) == 143
    assert not list(tmp_path.glob(R.TMP_PREFIX + '*'))
