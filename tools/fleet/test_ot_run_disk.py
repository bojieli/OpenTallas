"""Disk declarations must reserve real scope budgets without hiding safe hosts."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest import mock

loader = importlib.machinery.SourceFileLoader('ot_run_disk', str(Path(__file__).with_name('ot-run')))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


class DiskReservation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.jobs = Path(self.tmp.name)
        self.jobs_patch = mock.patch.object(m, 'DAEMON_JOBS', str(self.jobs))
        self.jobs_patch.start()
        self.addCleanup(self.jobs_patch.stop)

    def reserved(self, output, rc=0):
        with mock.patch.object(m.subprocess, 'run', return_value=types.SimpleNamespace(returncode=rc, stdout=output)):
            return m.die_disk_reserved('gold1')

    def test_declarations_unknown_and_duplicate_scope(self):
        self.assertEqual(self.reserved('DIEDISK oth-a.scope 16\nDIEDISK oth-b.scope unknown\n'
                                       'DIEDISK oth-a.scope 16\nDIEDISK_DONE\n'), 76)

    def test_duplicate_scope_uses_larger_budget(self):
        self.assertEqual(self.reserved('DIEDISK oth-a.scope 16\nDIEDISK oth-a.scope 100\nDIEDISK_DONE\n'), 100)

    def test_probe_failure_and_partial_output_do_not_zero_reservations(self):
        self.assertIsNone(self.reserved('DIEDISK oth-a.scope 16\n'))
        self.assertIsNone(self.reserved('DIEDISK_DONE\n', rc=1))
        self.assertIsNone(self.reserved('DIEDISK bad\nDIEDISK_DONE\n'))

    def test_standalone_daemon_remains_reserved_but_scope_job_counted_once(self):
        for name, root in [('die-gen-a', '/run/a'), ('die-gen-b', '/run/b')]:
            (self.jobs / (name + '.json')).write_text(json.dumps(dict(host='gold1', status='RUNNING', run=root)))
        output = 'DIEDISK oth-a.scope 16\nDIEDIR oth-a.scope /run/a/work\nDIEDISK_DONE\n'
        self.assertEqual(self.reserved(output), 76)
        # A sibling name is not evidence that a daemon job belongs to this scope.
        self.assertEqual(self.reserved(output.replace('/run/a/work', '/run/aa/work')), 136)

    def test_gold1_many_small_gen_scopes_admit_physical_follower(self):
        output = ''.join(f'DIEDISK oth-{i}.scope 16\n' for i in range(17)) + 'DIEDISK_DONE\n'
        reserve = self.reserved(output)
        rows = {'gold1': dict(disk_gb=1029)}
        with mock.patch.object(m, 'die_disk_reserved', return_value=reserve):
            self.assertEqual(m.drop_low_disk(rows, True, 100), rows)
        with mock.patch.object(m, 'die_disk_reserved', return_value=1020):
            self.assertEqual(m.drop_low_disk(rows, True, 100), {})

    def test_low_disk_still_refuses_and_legacy_probe_failure_keeps_count_budget(self):
        with mock.patch.object(m, 'die_disk_reserved', return_value=None), mock.patch.object(m, 'die_running', return_value=2):
            self.assertEqual(m.drop_low_disk({'h': dict(disk_gb=200)}, True, 100), {})
        with mock.patch.object(m, 'die_disk_reserved', return_value=100):
            self.assertEqual(m.drop_low_disk({'h': dict(disk_gb=150)}, True, 60), {})

    def test_tile_and_large_scratch_paths_unchanged(self):
        rows = {'h': dict(disk_gb=3000)}
        with mock.patch.object(m, 'die_disk_reserved', side_effect=AssertionError('unexpected query')):
            self.assertEqual(m.drop_low_disk(rows, True, 100), rows)
            self.assertEqual(m.drop_low_disk(rows, False, 100), rows)

    def test_real_shell_reads_environment_and_legacy_annotations(self):
        root = self.jobs
        tool = root / 'systemctl'
        tool.write_text('#!/bin/sh\ncase "$*" in\n*list-units*) printf "oth-a.scope active\\noth-b.scope active\\noth-c.scope active\\noth-d.scope active\\n";;\n*show*) case "$*" in *oth-a*) echo /a;; *oth-b*) echo /b;; *oth-c*) echo /c;; *oth-d*) echo /d;; esac;;\nesac\n')
        tool.chmod(0o755)
        pgrep = root / 'pgrep'
        pgrep.write_text('#!/bin/sh\nexit 1\n')
        pgrep.chmod(0o755)
        for i, (key, env) in enumerate([('a', b'OT_HEAVY_PRIO=die\0OT_HEAVY_DISK_GB=16\0'),
                                       ('b', b'OT_HEAVY_PRIO=die\0'), ('c', b'OT_HEAVY_PRIO=die\0'),
                                       ('d', b'OTHER=value\0')], 1):
            cg = root / 'cgroup' / key
            cg.mkdir(parents=True)
            (cg / 'cgroup.procs').write_text(str(i))
            proc = root / 'proc' / str(i)
            proc.mkdir(parents=True)
            (proc / 'environ').write_bytes(env)
            (proc / 'cwd').symlink_to('/run/' + key)
        meta = root / 'meta'
        meta.mkdir()
        (meta / 'disk.oth-b').write_text('8\n')
        script = m.DIE_DISK_UNITS_SH.replace('/sys/fs/cgroup', str(root / 'cgroup')).replace('/proc/', str(root / 'proc') + '/').replace('/var/tmp/ot-heavy', str(meta))
        r = subprocess.run(['bash', '-c', script], env=dict(os.environ, PATH=str(root) + ':' + os.environ['PATH']), text=True, capture_output=True, check=True)
        self.assertIn('DIEDISK oth-a.scope 16', r.stdout)
        self.assertIn('DIEDISK oth-b.scope 8', r.stdout)
        self.assertIn('DIEDISK oth-c.scope unknown', r.stdout)
        self.assertNotIn('DIEDISK oth-d.scope', r.stdout)
        self.assertEqual(self.reserved(r.stdout), 84)

    def test_queued_launchers_are_reserved_and_active_pid_is_not_charged_twice(self):
        root = self.jobs
        tool = root / 'systemctl'
        tool.write_text('#!/bin/sh\ncase "$*" in\n*list-units*) echo "oth-ubuntu-12-123.scope active";;\n*show*) echo /active;;\nesac\n')
        tool.chmod(0o755)
        tool = root / 'pgrep'
        tool.write_text('#!/bin/sh\nprintf "10\\n11\\n12\\n13\\n14\\n"\n')
        tool.chmod(0o755)
        cg = root / 'cgroup' / 'active'
        cg.mkdir(parents=True)
        (cg / 'cgroup.procs').write_text('12')
        for pid, env in [(10, b'OT_HEAVY_PRIO=die\0'),
                         (11, b'OT_HEAVY_PRIO=die\0OT_HEAVY_DISK_GB=100\0'),
                         (12, b'OT_HEAVY_PRIO=die\0OT_HEAVY_DISK_GB=16\0'),
                         (13, b'OT_HEAVY_PRIO=die\0OT_HEAVY_DISK_GB=8\0'),
                         (14, b'OTHER=value\0')]:
            proc = root / 'proc' / str(pid)
            proc.mkdir(parents=True)
            (proc / 'environ').write_bytes(env)
            (proc / 'cwd').symlink_to('/run/' + str(pid))
            # A nested independent waiter is still inside its parent's scope.
            (proc / 'cgroup').write_text('0::/active')
        script = m.DIE_DISK_UNITS_SH.replace('/sys/fs/cgroup', str(root / 'cgroup')).replace('/proc/', str(root / 'proc') + '/')
        r = subprocess.run(['bash', '-c', script], env=dict(os.environ, PATH=str(root) + ':' + os.environ['PATH']), text=True, capture_output=True, check=True)
        self.assertIn('DIEDISK waiter-10 unknown', r.stdout)
        self.assertIn('DIEDISK waiter-11 100', r.stdout)
        self.assertIn('DIEDISK waiter-13 8', r.stdout)
        self.assertNotIn('DIEDISK waiter-12 ', r.stdout)
        self.assertNotIn('DIEDISK waiter-14 ', r.stdout)
        self.assertLess(script.index('waiters=$(pgrep'), script.index('units=$(systemctl'))
        self.assertEqual(self.reserved(r.stdout), 184)
        # Without the queued 100 GB commitment, this would incorrectly admit.
        with mock.patch.object(m, 'die_disk_reserved', return_value=self.reserved(r.stdout)):
            self.assertEqual(m.drop_low_disk({'gold1': dict(disk_gb=250)}, True, 100), {})



class WrapperAndDisplay(unittest.TestCase):
    def test_remote_wrapper_carries_explicit_declared_disk(self):
        class Captured(Exception):
            pass
        def capture(args, **kwargs):
            self.assertIn('OT_HEAVY_DISK_GB=8 /usr/local/bin/ot-heavy', args[-1])
            raise Captured()
        with mock.patch.object(m.subprocess, 'Popen', side_effect=capture), mock.patch.dict(os.environ, {'OT_RUN_PRIO_ENV': 'OT_HEAVY_PRIO=die ', 'OT_RUN_NO_SCRATCH2': '1'}):
            with self.assertRaises(Captured):
                m.run('h', 40, ['true'], disk=8)

    def test_spill_keeps_disk_declaration(self):
        # The copy need is placement-only; the running command retains --disk.
        class Captured(Exception):
            pass
        with mock.patch.object(m, 'spill_copy_fwd', return_value=types.SimpleNamespace(returncode=0, stderr='', sent=0)), \
             mock.patch.object(m, 'pending_write'), mock.patch.object(m, 'log_signal'), \
             mock.patch.object(m, 'run', side_effect=Captured()) as run:
            with self.assertRaises(Captured):
                m.spill_run('a', 'b', ['/lane'], 20, 40, ['true'], '/lane', None, lambda s: None, disk=8)
            self.assertEqual(run.call_args.kwargs['disk'], 8)

    def test_status_distinguishes_growth_reserve_from_fresh_start(self):
        self.assertEqual(m.memory_charge_note(dict(growth_gb=158, inv_terms=dict(reserve=0.0, fresh=157.2, peak_gap=109.4))), 'reserve 0, fresh 157.2, peak 109.4')
        self.assertEqual(m.memory_charge_note(dict(growth_gb=158)), 'growth 158')


if __name__ == '__main__':
    unittest.main()
