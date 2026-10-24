"""v13 SCRATCH-DISK + DISK GUARD (FLEET-DISK 2026-10-24, owner: never use root disks for work).

On a host with a separate scratch disk (intel1/intel2/epyc2: /srv/opentallas-scratch2), OT_SCRATCH and new run dirs go
ONLY to that disk, even when the root fs has more space; below its floor the job is NOT RUN (no root fallback).
Hosts with only the root fs (localhost/epyc3 md0) keep the most-free rule.  A host whose root fs is > 85 % full admits
no job.  The shell snippets run for real against fake `stat`/`df` binaries.
"""
import base64
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent


def load():
    loader = importlib.machinery.SourceFileLoader('ot_run_scratch_disk', str(HERE / 'ot-run'))
    spec = importlib.util.spec_from_loader('ot_run_scratch_disk', loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


m = load()
EPYC2 = ('OT_SCRATCH_FREE /srv/opentallas-scratch 3000 1\nOT_SCRATCH_FREE /srv/opentallas-scratch2 835 0\n'
         'OT_ROOTFS 9 3000\nOT_DIR_ONROOT 1\n')
MD0 = 'OT_SCRATCH_FREE /srv/opentallas-scratch 6500 1\nOT_ROOTFS 6 6500\nOT_DIR_ONROOT 1\n'


class ProbeRows(unittest.TestCase):
    def test_separate_disk_counts_only_the_disk_even_when_root_is_emptier(self):
        row = m.scratch_disk({'disk_gb': 3000}, '/srv/opentallas-scratch/claude/lane/run', EPYC2)
        self.assertEqual(row['disk_gb'], 835)
        self.assertEqual(row['scratch_disk'], '/srv/opentallas-scratch2')
        self.assertEqual(m.host_refusal(row), '')

    def test_scratch_disk_below_floor_refuses_host_no_root_fallback(self):
        out = EPYC2.replace('scratch2 835', 'scratch2 %d' % (m.SCRATCH_DISK_FLOOR_GB - 1))
        row = m.scratch_disk({'disk_gb': 3000}, '/srv/opentallas-scratch/claude/lane/run', out)
        self.assertLess(row['disk_gb'], 3000)
        self.assertIn('floor', m.host_refusal(row))

    def test_root_fs_over_85_percent_refuses_any_host(self):
        for out in (EPYC2.replace('OT_ROOTFS 9', 'OT_ROOTFS 87'), MD0.replace('OT_ROOTFS 6', 'OT_ROOTFS 86')):
            row = m.scratch_disk({'disk_gb': 100}, None, out)
            self.assertIn('ROOT FS', m.host_refusal(row))
        self.assertEqual(m.host_refusal(m.scratch_disk({'disk_gb': 100}, None, MD0.replace('OT_ROOTFS 6', 'OT_ROOTFS 85'))), '')

    def test_md0_host_keeps_root_scratch(self):
        row = m.scratch_disk({'disk_gb': 6500}, '/srv/opentallas-scratch/claude/lane/run', MD0)
        self.assertNotIn('scratch_disk', row)
        self.assertEqual(row['disk_gb'], 6500)
        self.assertEqual(m.host_refusal(row), '')

    def test_old_probe_rows_are_not_refused(self):
        self.assertEqual(m.host_refusal({'disk_gb': 100, 'free_gb': 10}), '')

    def test_refused_pinned_host_is_a_loud_not_run(self):
        row = dict(free_gb=500, admit_gb=500, avail_gb=600, growth_gb=0, headroom_gb=10, waiting=0, waiting_gb=0,
                   running=0, ncpu=112, cpu_load1=1, disk_gb=3000)
        def probe(h, d, spill_ok=False):
            return h, m.scratch_disk(dict(row), d, EPYC2.replace('OT_ROOTFS 9', 'OT_ROOTFS 87'))
        err = io.StringIO()
        argv = ['ot-run', '--mem', '8', '--hosts', 'intel1', '--', 'true']
        with mock.patch.object(m, 'probe', side_effect=probe), mock.patch.object(m, 'trigger_sweep', lambda: None), \
                mock.patch.object(m, 'held_hosts', return_value={}), mock.patch.object(sys, 'argv', argv), \
                contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            m.main()
        self.assertIn('NOT RUN', str(cm.exception))
        self.assertIn('ROOT FS 87%', str(cm.exception))


def fake_bin(base, devs, avail, pcent):
    """fake stat/df: devs maps path prefix -> device, avail path prefix -> GB, pcent = root use %"""
    b = base / 'bin'
    b.mkdir(exist_ok=True)
    dev_cases = ''.join(f'  {p}|{p}/*) echo {d}; exit 0;;\n' for p, d in sorted(devs.items(), key=lambda x: -len(x[0])))
    av_cases = ''.join(f'  {p}|{p}/*) a={g};;\n' for p, g in sorted(avail.items(), key=lambda x: -len(x[0])))
    (b / 'stat').write_text('#!/bin/bash\np="${@: -1}"\ncase "$p" in\n' + dev_cases + '  /) echo 1; exit 0;;\nesac\nexit 1\n')
    (b / 'df').write_text('#!/bin/bash\np="${@: -1}"\nif [[ "$*" == *pcent* ]]; then echo Use; echo " ' + str(pcent)
                          + '%"; exit 0; fi\na=1\ncase "$p" in\n' + av_cases + 'esac\necho Avail; echo " ${a}G"\n')
    for f in ('stat', 'df'):
        (b / f).chmod(0o755)
    return dict(os.environ, PATH=f'{b}:{os.environ["PATH"]}')


class RemoteShell(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='otscratchdisk-')
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        self.s1, self.s2 = self.base / 'srv/opentallas-scratch', self.base / 'srv/opentallas-scratch2'

    def sh(self, snippet, env, roots=True):
        if roots:
            snippet = snippet.replace('/srv/opentallas-scratch', str(self.base) + '/srv/opentallas-scratch')
        return subprocess.run(['bash', '-c', snippet], capture_output=True, text=True, env=env)

    def test_ot_scratch_is_the_disk_on_epyc2_and_most_free_on_md0(self):
        (self.s1 / 'claude').mkdir(parents=True)
        (self.s2 / 'claude').mkdir(parents=True)
        env = fake_bin(self.base, {str(self.s1): 1, str(self.s2): 2}, {str(self.s1): 3000, str(self.s2): 835}, 9)
        r = self.sh(m.SCRATCH_ENV + 'echo "$OT_SCRATCH"', env)
        self.assertEqual(r.stdout.strip(), str(self.s2), r.stderr)
        env = fake_bin(self.base, {str(self.s1): 1, str(self.s2): 1}, {str(self.s1): 3000, str(self.s2): 835}, 9)
        self.assertEqual(self.sh(m.SCRATCH_ENV + 'echo "$OT_SCRATCH"', env).stdout.strip(), str(self.s1))

    def test_disk_guard_refuses_full_root_and_low_scratch_disk(self):
        (self.s2 / 'claude').mkdir(parents=True)
        pre = f'OT_SCRATCH={self.s2}; '
        env = fake_bin(self.base, {str(self.s2): 2}, {str(self.s2): 835}, 87)
        r = self.sh(pre + m.disk_guard_sh('T1') + 'echo ADMITTED', env, roots=False)
        self.assertEqual(r.returncode, 97)
        self.assertIn('OT_RUN_ROOTFULL T1', r.stderr)
        self.assertNotIn('ADMITTED', r.stdout)
        env = fake_bin(self.base, {str(self.s2): 2}, {str(self.s2): 10}, 40)
        r = self.sh(pre + m.disk_guard_sh('T2') + 'echo ADMITTED', env, roots=False)
        self.assertEqual(r.returncode, 98)
        self.assertIn('OT_RUN_SCRATCHLOW T2', r.stderr)
        env = fake_bin(self.base, {str(self.s2): 1}, {str(self.s2): 10}, 40)     # md0: scratch on root, no floor
        r = self.sh(pre + m.disk_guard_sh('T3') + 'echo ADMITTED', env, roots=False)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, 'ADMITTED'), r.stderr)

    def test_run_reports_refusal_as_not_run(self):
        env = fake_bin(self.base, {}, {}, 90)
        real_popen = subprocess.Popen

        def popen(args, **kw):
            return real_popen(['bash', '-c', args[-1]], env=env, **kw)
        err = io.StringIO()
        with mock.patch.object(m.subprocess, 'Popen', side_effect=popen), contextlib.redirect_stderr(err):
            rc, ran = m.run('intel1', 1, ['true'])
        self.assertEqual((rc, ran), (97, False))
        self.assertIn('NOT RUN on intel1: root fs above 85% (DISK GUARD)', err.getvalue())


class Placer(unittest.TestCase):
    """SCRATCH_PLACE_PY with /srv/opentallas-scratch on the root device (1) and scratch2 on its own disk (2)"""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='otplacer-')
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        self.roots = [self.base / 'srv/opentallas-scratch', self.base / 'srv/opentallas-scratch2']
        for r in self.roots:
            (r / 'claude').mkdir(parents=True)
        self.lane = self.roots[0] / 'claude/lane'
        self.lane.mkdir()

    def place(self, command, free2_gb, devs=(1, 2)):
        code = m.SCRATCH_PLACE_PY.replace('/srv/opentallas-scratch', str(self.base) + '/srv/opentallas-scratch')
        real_stat = os.stat

        def stat(path, *a, **kw):
            p = pathlib.Path(path)
            if str(p) == '/':
                return types.SimpleNamespace(st_dev=1, st_mode=0o40755)
            p = p.parent if p.name == 'claude' else p
            if p in self.roots:
                return types.SimpleNamespace(st_dev=devs[self.roots.index(p)], st_mode=0o40755)
            return real_stat(path, *a, **kw)

        def statvfs(path):
            p = pathlib.Path(path)
            p = p.parent if p.name == 'claude' else p
            return types.SimpleNamespace(f_bavail=(3000 if p == self.roots[0] else free2_gb) << 30, f_frsize=1)
        argv = ['scratch-place', str(self.lane), base64.b64encode(json.dumps(command).encode()).decode()]
        err = io.StringIO()
        with mock.patch.object(os, 'stat', side_effect=stat), mock.patch.object(os, 'statvfs', side_effect=statvfs), \
                mock.patch.object(sys, 'argv', argv), contextlib.redirect_stderr(err):
            try:
                exec(compile(code, 'scratch-place', 'exec'), {})
            except SystemExit as e:
                return e.code, err.getvalue()
        return 0, err.getvalue()

    def test_new_run_dir_goes_to_scratch_disk_even_with_less_space(self):
        run = self.lane / 'fresh'
        rc, _ = self.place(['bash', '-c', f'mkdir -p {run}/out'], 835)
        self.assertEqual(rc, 0)
        self.assertTrue(run.is_symlink())
        self.assertEqual(os.readlink(run), str(self.roots[1] / 'claude/lane/fresh'))

    def test_scratch_disk_below_floor_fails_loudly_and_creates_nothing_on_root(self):
        run = self.lane / 'fresh'
        rc, err = self.place(['bash', '-c', f'mkdir -p {run}/out'], 10)
        self.assertEqual(rc, 3)
        self.assertIn('NOT RUN', err)
        self.assertFalse(os.path.lexists(run))

    def test_existing_run_dir_is_never_moved(self):
        run = self.lane / 'old'
        run.mkdir()
        rc, _ = self.place(['bash', '-c', f'mkdir -p {run}/out'], 10)
        self.assertEqual(rc, 0)
        self.assertFalse(run.is_symlink())

    def test_md0_host_places_nothing(self):
        run = self.lane / 'fresh'
        rc, _ = self.place(['bash', '-c', f'mkdir -p {run}/out'], 835, devs=(1, 1))
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.lexists(run))

    def test_place_snippet_turns_exit_3_into_scratchlow(self):
        b = self.base / 'bin'
        b.mkdir()
        (b / 'timeout').write_text('#!/bin/sh\necho "ot-run: SCRATCH2: NOT RUN: test" >&2\nexit 3\n')
        (b / 'timeout').chmod(0o755)
        env = dict(os.environ, PATH=f'{b}:{os.environ["PATH"]}')
        sh = m.scratch_place_sh('/x', ['true'], tag='TAG')
        r = subprocess.run(['bash', '-c', sh + 'echo LAUNCHED'], capture_output=True, text=True, env=env)
        self.assertNotIn('LAUNCHED', r.stdout)
        self.assertIn('SCRATCH2: NOT RUN', r.stderr)
        self.assertEqual(r.returncode, 98)
        self.assertIn('OT_RUN_SCRATCHLOW TAG', r.stderr)


if __name__ == '__main__':
    unittest.main()
