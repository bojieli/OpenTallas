"""ROOTSCR_1101 (OWNER 2026-11-01 19:0x): epyc2's root disk is a SECOND scratch root (/srv/opentallas-scratch3, a bind
mount of /home/ubuntu/scratch-root).  It takes OT_SCRATCH and new run dirs only when every separate scratch disk is
below SCRATCH_DISK_FLOOR_GB, or when a build pins it (OT_RUN_SCRATCH_ROOT), and keeps ROOT_SCRATCH_FLOOR_GB (500 GB)
free on the root fs.  Other root-fs roots stay excluded (v13)."""
import base64
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ot_run_scratch_disk import fake_bin, load  # noqa: E402

m = load()
S3 = '/srv/opentallas-scratch3'


def probe_out(s2, root_free, pct=2):
    return ('OT_SCRATCH_FREE /srv/opentallas-scratch %d 1\nOT_SCRATCH_FREE /srv/opentallas-scratch2 %d 0\n'
            'OT_SCRATCH_FREE %s %d 1\nOT_ROOTFS %d %d\nOT_DIR_ONROOT 0\n' % (root_free, s2, S3, root_free, pct, root_free))


class ProbeRows(unittest.TestCase):
    D = '/srv/opentallas-scratch2/claude/lane/run'

    def test_disk_above_floor_keeps_scratch2(self):
        row = m.scratch_disk({'disk_gb': 835}, self.D, probe_out(835, 3276))
        self.assertEqual((row['scratch_disk'], row['disk_gb']), ('/srv/opentallas-scratch2', 835))
        self.assertNotIn('scratch_second', row)
        self.assertEqual(m.host_refusal(row), '')

    def test_disk_below_floor_uses_second_root_minus_root_floor(self):
        row = m.scratch_disk({'disk_gb': 40}, self.D, probe_out(40, 3276))
        self.assertEqual(row['scratch_disk'], S3)
        self.assertEqual(row['scratch_disk_gb'], 3276 - m.ROOT_SCRATCH_FLOOR_GB)
        self.assertTrue(row['scratch_second'])
        self.assertEqual(row['disk_gb'], 3276 - m.ROOT_SCRATCH_FLOOR_GB)
        self.assertEqual(m.host_refusal(row), '')

    def test_root_floor_kept_refuses_when_both_low(self):
        row = m.scratch_disk({'disk_gb': 40}, self.D, probe_out(40, m.ROOT_SCRATCH_FLOOR_GB + 20))
        self.assertIn('floor', m.host_refusal(row))

    def test_pin_takes_second_root_even_with_disk_above_floor(self):
        with mock.patch.object(m, 'SCRATCH_PIN', S3):
            row = m.scratch_disk({'disk_gb': 835}, self.D, probe_out(835, 3276))
        self.assertEqual(row['scratch_disk'], S3)

    def test_host_without_second_root_unchanged(self):
        out = probe_out(40, 3276).replace('OT_SCRATCH_FREE %s 3276 1\n' % S3, '')
        row = m.scratch_disk({'disk_gb': 40}, self.D, out)
        self.assertEqual(row['scratch_disk'], '/srv/opentallas-scratch2')
        self.assertIn('floor', m.host_refusal(row))


class RemoteShell(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix='otrootscr-')
        self.addCleanup(t.cleanup)
        self.base = pathlib.Path(t.name)
        self.s = [self.base / ('srv/opentallas-scratch' + x) for x in ('', '2', '3')]
        for d in self.s:
            (d / 'claude').mkdir(parents=True)

    def env(self, s2, root, pct=2):
        return fake_bin(self.base, {str(self.s[0]): 1, str(self.s[1]): 2, str(self.s[2]): 1},
                        {str(self.s[0]): root, str(self.s[1]): s2, str(self.s[2]): root, '/': root}, pct)

    def sh(self, snippet, env):
        snippet = snippet.replace('/srv/opentallas-scratch', str(self.base) + '/srv/opentallas-scratch')
        return subprocess.run(['bash', '-c', snippet], capture_output=True, text=True, env=env)

    def test_ot_scratch_falls_back_to_second_root_only_below_floor(self):
        self.assertEqual(self.sh(m.SCRATCH_ENV + 'echo "$OT_SCRATCH"', self.env(835, 3276)).stdout.strip(), str(self.s[1]))
        self.assertEqual(self.sh(m.SCRATCH_ENV + 'echo "$OT_SCRATCH"', self.env(40, 3276)).stdout.strip(), str(self.s[2]))
        self.assertEqual(self.sh(m.SCRATCH_ENV + 'echo "$OT_SCRATCH"', self.env(40, 520)).stdout.strip(), str(self.s[1]))

    def test_disk_guard_keeps_root_floor_for_second_root(self):
        pre = 'OT_SCRATCH=/srv/opentallas-scratch3; '
        r = self.sh(pre + m.disk_guard_sh('T1') + 'echo ADMITTED', self.env(40, 3276))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, 'ADMITTED'), r.stderr)
        r = self.sh(pre + m.disk_guard_sh('T2') + 'echo ADMITTED', self.env(40, m.ROOT_SCRATCH_FLOOR_GB + 20))
        self.assertEqual(r.returncode, 98)
        self.assertIn('OT_RUN_SCRATCHLOW T2', r.stderr)


class Placement(unittest.TestCase):
    """SCRATCH_PLACE_PY in-process with st_dev / statvfs faked: s1 + s3 on the root fs (dev 1), s2 a disk (dev 2)."""

    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix='otrootplace-')
        self.addCleanup(t.cleanup)
        self.base = str(pathlib.Path(t.name))
        self.r = [self.base + '/srv/opentallas-scratch' + x for x in ('', '2', '3')]
        for d in self.r:
            os.makedirs(d + '/claude/lane')

    def place(self, s2_gb, root_gb, pin=''):
        dev = {self.r[0]: 1, self.r[1]: 2, self.r[2]: 1, '/': 1}
        gb = {self.r[0]: root_gb, self.r[1]: s2_gb, self.r[2]: root_gb}
        real_stat, real_vfs = os.stat, os.statvfs

        def root_of(p):
            p = str(p)
            return next((r for r in sorted(dev, key=len, reverse=True) if p == r or p.startswith(r + '/')), None)

        def fstat(p, *a, **k):
            st = real_stat(p, *a, **k)
            r = root_of(p) if str(p) != '/' else '/'
            if r is None:
                return st
            t = list(st)
            t[2] = dev[r]
            return os.stat_result(t)

        def fvfs(p):
            r = root_of(p)
            v = real_vfs(p)
            if r is None:
                return v
            t = list(v)
            t[0] = t[1] = 1 << 20      # f_bsize, f_frsize
            t[4] = (gb[r] << 30) >> 20  # f_bavail
            return os.statvfs_result(t)

        nxt = self.r[1] + '/claude/lane/newrun'
        cmd = ['bash', '-c', f'mkdir -p {nxt} && touch {nxt}/x']
        code = m.SCRATCH_PLACE_PY.replace('/srv/opentallas-scratch', self.base + '/srv/opentallas-scratch')
        env = dict(OT_RUN_PLACE_ROOTS=' '.join(self.r), OT_RUN_PLACE_SECOND=self.r[2], OT_RUN_PLACE_RFLOOR='500',
                   OT_RUN_PLACE_PIN=pin, OT_RUN_SCRATCH_DISK_FLOOR_GB='50')
        argv = ['x', self.r[1] + '/claude/lane', base64.b64encode(json.dumps(cmd).encode()).decode()]
        err = io.StringIO()
        with mock.patch.dict(os.environ, env), mock.patch.object(os, 'stat', fstat), \
                mock.patch.object(os, 'statvfs', fvfs), mock.patch.object(sys, 'argv', argv), \
                contextlib.redirect_stderr(err):
            try:
                exec(compile(code, 'place', 'exec'), {'__name__': '__main__'})
            except SystemExit as e:
                return e.code, nxt, err.getvalue()
        return 0, nxt, err.getvalue()

    def test_disk_above_floor_places_nothing(self):
        rc, nxt, err = self.place(835, 3276)
        self.assertEqual(rc, 0, err)
        self.assertFalse(os.path.lexists(nxt), err)

    def test_disk_below_floor_places_new_dir_on_second_root(self):
        rc, nxt, err = self.place(40, 3276)
        self.assertEqual(rc, 0, err)
        self.assertTrue(os.path.islink(nxt), err)
        self.assertEqual(os.readlink(nxt), self.r[2] + '/claude/lane/newrun')

    def test_pin_places_on_second_root(self):
        rc, nxt, err = self.place(835, 3276, pin=self.r[2])
        self.assertTrue(os.path.islink(nxt), err)

    def test_second_root_below_root_floor_not_used(self):
        rc, nxt, err = self.place(40, 520)
        self.assertFalse(os.path.islink(nxt), err)


class Client(unittest.TestCase):
    def test_place_snippet_passes_roots_floor_and_pin(self):
        sh = m.scratch_place_sh('/srv/opentallas-scratch2/claude/l', ['true'])
        for k in ('OT_RUN_PLACE_ROOTS=', S3, 'OT_RUN_PLACE_RFLOOR=500', 'OT_RUN_PLACE_PIN='):
            self.assertIn(k, sh)
        self.assertIn(S3, m.SCRATCH_FREE_SH)


if __name__ == '__main__':
    unittest.main()
