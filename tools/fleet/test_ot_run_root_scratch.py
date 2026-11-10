"""ROOTSCR_1101 (OWNER 2026-11-01 19:0x): epyc2's root disk is a SECOND scratch root (/srv/opentallas-scratch3, a bind
mount of /home/ubuntu/scratch-root).  It takes OT_SCRATCH and new run dirs only when every separate scratch disk is
below SCRATCH_DISK_FLOOR_GB, or when a build pins it (OT_RUN_SCRATCH_ROOT), and keeps ROOT_SCRATCH_FLOOR_GB (150 GB, OWNER 11-06)
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

S3 = '/srv/opentallas-scratch3'
_env = {k: v for k, v in os.environ.items() if not k.startswith('OT_RUN_ROOT_SCRATCH')}
with mock.patch.dict(os.environ, _env, clear=True):   # ROOTSCR-INTEL 11-05: on by default, per-host root floors
    m = load()


def probe_out(s2, root_free, pct=2):
    return ('OT_SCRATCH_FREE /srv/opentallas-scratch %d 1\nOT_SCRATCH_FREE /srv/opentallas-scratch2 %d 0\n'
            'OT_SCRATCH_FREE %s %d 1\nOT_ROOTFS %d %d\nOT_DIR_ONROOT 0\n' % (root_free, s2, S3, root_free, pct, root_free))


class OnByDefault(unittest.TestCase):
    def test_default_has_scratch3(self):
        self.assertEqual(m.ROOT_SCRATCH_ROOTS, (S3,))
        self.assertIn(S3, m.SCRATCH_ENV)

    def test_empty_env_turns_it_off(self):
        env = dict(_env, OT_RUN_ROOT_SCRATCH_ROOTS='')
        with mock.patch.dict(os.environ, env, clear=True):
            off = load()
        self.assertEqual(off.ROOT_SCRATCH_ROOTS, ())
        self.assertEqual(off.SCRATCH_ROOTS, ('/srv/opentallas-scratch', '/srv/opentallas-scratch2'))
        self.assertNotIn(S3, off.SCRATCH_ENV)


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
        row = m.scratch_disk({'disk_gb': 40}, self.D, probe_out(40, m.ROOT_SCRATCH_FLOOR_GB + 15))   # usable 15 < second floor 20
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


class PerHostFloor(unittest.TestCase):
    """ROOTSCR-INTEL 11-05 (OWNER 18:5x): intel1/intel2 (= localhost) roots keep 150 GB; epyc2/epyc4 too since OWNER 11-06 22:4x (were 500)."""
    D = '/srv/opentallas-scratch2/claude/lane/run'

    def test_default_table(self):
        self.assertEqual([m.root_floor(h) for h in ('intel1', 'localhost', 'intel2', 'epyc2', 'epyc4', None)],
                         [150, 150, 150, 150, 150, 150])

    def test_env_overrides_table(self):
        env = dict(_env, OT_RUN_ROOT_SCRATCH_FLOOR_GB_HOSTS='intel1=200, epyc2=600', OT_RUN_ROOT_SCRATCH_FLOOR_GB='700')
        with mock.patch.dict(os.environ, env, clear=True):
            o = load()
        self.assertEqual([o.root_floor(h) for h in ('intel1', 'epyc2', 'localhost')], [200, 600, 700])

    def test_intel_uses_second_root_minus_150(self):
        row = m.scratch_disk({'disk_gb': 35}, self.D, probe_out(35, 342, 24), 'localhost')
        self.assertEqual((row['scratch_disk'], row['scratch_disk_gb'], row['disk_gb']), (S3, 192, 192))
        self.assertEqual(m.host_refusal(row), '')

    def test_epyc_refuses_when_root_is_near_150(self):
        row = m.scratch_disk({'disk_gb': 35}, self.D, probe_out(35, 160, 24), 'epyc2')
        self.assertEqual(row['scratch_disk'], '/srv/opentallas-scratch2')
        self.assertIn('floor', m.host_refusal(row))

    def test_intel_refusal_names_150(self):
        row = m.scratch_disk({'disk_gb': 35}, self.D, probe_out(35, 164, 60), 'intel1')
        self.assertIn('floor', m.host_refusal(row))
        row = dict(row, scratch_disk=S3, scratch_disk_gb=10, scratch_second=True, root_floor_gb=150)
        self.assertIn('keeping 150 GB', m.host_refusal(row))

    def test_intel_scratch_disk_above_floor_unchanged(self):
        row = m.scratch_disk({'disk_gb': 92}, self.D, probe_out(92, 406, 9), 'intel1')
        self.assertEqual((row['scratch_disk'], row['disk_gb']), ('/srv/opentallas-scratch2', 92))

    def test_place_snippet_floor_per_host(self):
        self.assertIn('OT_RUN_PLACE_RFLOOR=150', m.scratch_place_sh('/x', ['true'], host='intel1'))
        self.assertIn('OT_RUN_PLACE_RFLOOR=150', m.scratch_place_sh('/x', ['true'], host='epyc4'))


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
        self.assertEqual(self.sh(m.SCRATCH_ENV + 'echo "$OT_SCRATCH"', self.env(40, 515)).stdout.strip(), str(self.s[1]))   # usable 15 < second floor 20 (QUEUE-BAL-2)
        self.assertEqual(self.sh(m.SCRATCH_ENV + 'echo "$OT_SCRATCH"', self.env(40, 520)).stdout.strip(), str(self.s[2]))   # usable 20: was refused at 50

    def test_intel_shell_uses_150_floor(self):
        env = self.env(40, 230)
        self.assertEqual(self.sh(m.scratch_env('intel1') + 'echo "$OT_SCRATCH"', env).stdout.strip(), str(self.s[2]))
        self.assertEqual(self.sh(m.scratch_env('epyc2') + 'echo "$OT_SCRATCH"', env).stdout.strip(), str(self.s[1]))

class SecondFloor(unittest.TestCase):
    """QUEUE-BAL-2 (COORD 21:2x): intel2 21:2x = scratch2 29 GB, root 197 GB free, root floor 150 -> 47 GB usable on
    scratch3; it was REFUSED (47 < 50) though the root floor already reserves the root fs.  Second root needs 20 GB."""
    D = '/srv/opentallas-scratch3/claude/lane/run'
    D2 = '/srv/opentallas-scratch2/claude/lane/run'

    def test_intel2_2120_admits_on_scratch3(self):
        row = m.scratch_disk({'disk_gb': 197}, self.D, probe_out(29, 197), host='localhost')
        self.assertEqual((row['scratch_disk'], row['scratch_disk_gb']), (S3, 47))
        self.assertEqual(m.host_refusal(row), '')
        self.assertEqual(m.dir_disk_full(row), '')

    def test_below_second_floor_still_refused(self):
        row = m.scratch_disk({'disk_gb': 165}, self.D, probe_out(29, 165), host='localhost')
        self.assertNotIn('scratch_second', row)
        self.assertIn('scratch disk', m.host_refusal(row))

    def test_epyc4_root_near_150_stays_refused(self):
        row = m.scratch_disk({'disk_gb': 33}, self.D2, probe_out(33, 160), host='epyc4')
        self.assertIn('scratch disk', m.host_refusal(row))

    def test_dir_on_the_full_disk_is_spill_source_only(self):
        row = m.scratch_disk({'disk_gb': 29}, self.D2, probe_out(29, 197), host='localhost')
        self.assertEqual(m.host_refusal(row), '')
        self.assertTrue(m.dir_disk_full(row).startswith(m.DIR_FULL_NOTE))
        with mock.patch.object(m, 'probe', side_effect=lambda h, d: (h, dict(row, ncpu=112, total_gb=1000, avail_gb=400,
                                                                                admit_gb=300, free_gb=300, headroom_gb=0,
                                                                                waiting=0, waiting_gb=0, running=1))), \
                mock.patch.object(m, 'trigger_reaper', return_value=False), contextlib.redirect_stderr(io.StringIO()):
            ok = m.place(['localhost'], self.D2, 20, 48, quiet=True)
        self.assertEqual(ok, {})
        self.assertEqual(list(m.REFUSED_SRC), ['localhost'])


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
        for k in ('OT_RUN_PLACE_ROOTS=', S3, 'OT_RUN_PLACE_RFLOOR=150', 'OT_RUN_PLACE_PIN='):
            self.assertIn(k, sh)
        self.assertIn(S3, m.SCRATCH_FREE_SH)


if __name__ == '__main__':
    unittest.main()
