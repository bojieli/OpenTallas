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



class PerRootReservation(unittest.TestCase):
    """FLOW-31: a unit is charged only against the root its dir falls on."""
    EPYC4 = ('DIEDISK oth-s2.scope 20\nDIEDIR oth-s2.scope /srv/opentallas-scratch2/claude/a\nDIEDEV oth-s2.scope 66\n'
             'DIEDISK oth-s3.scope 60\nDIEDIR oth-s3.scope /srv/opentallas-scratch3/claude/b\nDIEDEV oth-s3.scope 77\n'
             'DIEDISK waiter-9 40\nDIEDIR waiter-9 /srv/opentallas-scratch2/claude/c\nDIEDEV waiter-9 66\n')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch = mock.patch.object(m, 'DAEMON_JOBS', self.tmp.name)
        patch.start()
        self.addCleanup(patch.stop)

    def reserved(self, output, dev=None, rc=0):
        with mock.patch.object(m.subprocess, 'run', return_value=types.SimpleNamespace(returncode=rc, stdout=output)):
            return m.die_disk_reserved('epyc4', dev)

    def test_each_unit_charges_only_its_own_root(self):
        output = self.EPYC4 + 'DIEDISK_DONE\n'
        self.assertEqual(self.reserved(output, '66'), 60)
        self.assertEqual(self.reserved(output, '77'), 60)
        self.assertEqual(self.reserved(output, '88'), 0)

    def test_unknown_root_of_job_keeps_host_total(self):
        self.assertEqual(self.reserved(self.EPYC4 + 'DIEDISK_DONE\n'), 120)

    def test_unit_without_known_dir_is_charged_everywhere(self):
        for extra in ('DIEDISK oth-n.scope 5\n', 'DIEDISK oth-n.scope 5\nDIEDIR oth-n.scope /home/x\nDIEDEV oth-n.scope unknown\n',
                      'DIEDISK oth-n.scope 5\nDIEDEV oth-n.scope 77\nDIEDEV oth-n.scope unknown\n'):
            self.assertEqual(self.reserved(self.EPYC4 + extra + 'DIEDISK_DONE\n', '66'), 65, extra)

    def test_unit_with_a_dir_on_the_root_is_charged(self):
        extra = 'DIEDISK oth-m.scope 5\nDIEDEV oth-m.scope 77\nDIEDEV oth-m.scope 66\n'
        self.assertEqual(self.reserved(self.EPYC4 + extra + 'DIEDISK_DONE\n', '66'), 65)

    def test_probe_failure_still_none(self):
        self.assertIsNone(self.reserved(self.EPYC4, '66'))
        self.assertIsNone(self.reserved(self.EPYC4 + 'DIEDISK_DONE\n', '66', rc=1))

    def test_standalone_daemon_job_is_charged_on_every_root(self):
        Path(self.tmp.name, 'die-gen-a.json').write_text(json.dumps(dict(host='epyc4', status='RUNNING', run='/run/a')))
        self.assertEqual(self.reserved(self.EPYC4 + 'DIEDISK_DONE\n', '77'), 120)

    def test_daemon_represented_by_a_unit_on_another_root_adds_nothing(self):
        Path(self.tmp.name, 'die-gen-a.json').write_text(json.dumps(
            dict(host='epyc4', status='RUNNING', run='/srv/opentallas-scratch3/claude/b')))
        self.assertEqual(self.reserved(self.EPYC4 + 'DIEDISK_DONE\n', '66'), 60)

    def test_drop_low_disk_passes_root_and_replays_the_blocked_case(self):
        # 07:39 capc5r: scratch2 720 GB free, 900 GB reserved, 180 of it on scratch2 here
        units = ''.join(f'DIEDISK oth-{i}.scope 60\nDIEDEV oth-{i}.scope 77\n' for i in range(12)) \
            + ''.join(f'DIEDISK oth-s{i}.scope 60\nDIEDEV oth-s{i}.scope 66\n' for i in range(3)) + 'DIEDISK_DONE\n'
        said = []
        with mock.patch.object(m.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0, stdout=units)):
            rows = {'epyc4': dict(disk_gb=720, disk_dev='66')}
            self.assertEqual(m.drop_low_disk(rows, True, 20, said.append), rows)
            self.assertEqual(said, [])
            rows = {'epyc4': dict(disk_gb=720)}
            self.assertEqual(m.drop_low_disk(rows, True, 20, said.append), {})
            self.assertIn('720 GB free - 900 GB', said[0])

    def test_root_short_of_its_own_reservations_still_refuses(self):
        units = ''.join(f'DIEDISK oth-{i}.scope 60\nDIEDEV oth-{i}.scope 66\n' for i in range(12)) + 'DIEDISK_DONE\n'
        said = []
        with mock.patch.object(m.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0, stdout=units)):
            self.assertEqual(m.drop_low_disk({'epyc4': dict(disk_gb=725, disk_dev='66')}, True, 60, said.append), {})
        self.assertIn('725 GB free - 720 GB running/queued die reservations on its root < 60 GB', said[0])

    def probe_out(self, *extra):
        return '\n'.join(('OT_SCRATCH_FREE /srv/opentallas-scratch2 700 0', 'OT_SCRATCH_DEV /srv/opentallas-scratch2 66',
                          'OT_SCRATCH_FREE /srv/opentallas-scratch3 2200 1', 'OT_SCRATCH_DEV /srv/opentallas-scratch3 77',
                          'OT_ROOTFS 35 2200') + extra)

    def test_disk_dev_names_the_root_disk_gb_measures(self):
        s2, s3 = '/srv/opentallas-scratch2/claude/l/r', '/srv/opentallas-scratch3/claude/l/r'
        row = m.scratch_disk({'disk_gb': 700}, s2, self.probe_out('OT_DIR_DEV 66', 'OT_DIR_ONROOT 0'))
        self.assertEqual((row['disk_gb'], row['disk_dev']), (700, '66'))
        # A root bind remains on its actual device and is refused without an exception.
        row = m.scratch_disk({'disk_gb': 2200}, s3, self.probe_out('OT_DIR_DEV 77', 'OT_DIR_ONROOT 1'))
        self.assertEqual((row['disk_gb'], row['disk_dev']), (2200, '77'))
        self.assertIn('ROOT filesystem', m.host_refusal(row))
        row = m.scratch_disk({'disk_gb': 100}, s2, self.probe_out('OT_DIR_DEV 88', 'OT_DIR_ONROOT 0'))
        self.assertEqual((row['disk_gb'], row['disk_dev']), (100, '88'))
        row = m.scratch_disk({'disk_gb': 90}, '/home/x', self.probe_out('OT_DIR_DEV 99', 'OT_DIR_ONROOT 1'))
        self.assertEqual((row['disk_gb'], row['disk_dev']), (90, '99'))

    def test_row_without_device_lines_has_no_disk_dev(self):
        out = self.probe_out().replace('OT_SCRATCH_DEV', 'X')
        row = m.scratch_disk({'disk_gb': 2200}, '/srv/opentallas-scratch3/claude/l/r', out + '\nOT_DIR_ONROOT 1')
        self.assertIsNone(row.get('disk_dev'))

    def test_real_shell_emits_devices(self):
        root = Path(self.tmp.name)
        for name, body in [('systemctl', 'case "$*" in\n*list-units*) echo "oth-a.scope active";;\n*show*) echo /a;;\nesac\n'),
                           ('pgrep', 'printf "10\\n11\\n"\n')]:
            (root / name).write_text('#!/bin/sh\n' + body)
            (root / name).chmod(0o755)
        cg = root / 'cgroup' / 'a'
        cg.mkdir(parents=True)
        (cg / 'cgroup.procs').write_text('9')
        scr = root / 'scr'
        (scr / 'x').mkdir(parents=True)
        for pid, target in [(9, scr / 'x'), (10, scr / 'gone'), (11, Path('/usr'))]:
            proc = root / 'proc' / str(pid)
            proc.mkdir(parents=True)
            (proc / 'environ').write_bytes(b'OT_HEAVY_PRIO=die\0OT_HEAVY_DISK_GB=20\0')
            (proc / 'cwd').symlink_to(target)
        script = m.DIE_DISK_UNITS_SH.replace('/sys/fs/cgroup', str(root / 'cgroup')).replace('/proc/', str(root / 'proc') + '/') \
            .replace('/srv/opentallas-scratch*)', str(scr) + '*)')
        r = subprocess.run(['bash', '-c', script], env=dict(os.environ, PATH=str(root) + ':' + os.environ['PATH']), text=True, capture_output=True, check=True)
        dev = str(os.stat(scr / 'x').st_dev)
        self.assertIn(f'DIEDEV oth-a.scope {dev}', r.stdout.splitlines())
        self.assertIn('DIEDEV waiter-10 unknown', r.stdout.splitlines())
        self.assertIn('DIEDEV waiter-11 unknown', r.stdout.splitlines())
        self.assertEqual(self.reserved(r.stdout, dev), 60)
        self.assertEqual(self.reserved(r.stdout, 'other'), 40)

    def test_real_shell_scratch_free_lines_parse(self):
        base = Path(self.tmp.name)
        (base / 'r' / 'claude').mkdir(parents=True)
        script = 't=' + str(base) + '; ' + m.SCRATCH_FREE_SH.replace('/srv/opentallas-scratch2', str(base / 'r')).replace('/srv/opentallas-scratch ', str(base / 'none') + ' ')
        r = subprocess.run(['bash', '-c', script], text=True, capture_output=True, check=True)
        dev = str(os.stat(base).st_dev)
        self.assertIn(f"OT_SCRATCH_DEV {base / 'r'} {dev}", r.stdout.splitlines())
        self.assertIn(f'OT_DIR_DEV {dev}', r.stdout.splitlines())


class RunningCharge(unittest.TestCase):
    """FLOW-32: a running scope past the young window is charged 1/4; queued launchers in full; real-free floor."""
    # epyc2 scratch2, 09:45: 8 scopes x 20 GB, 121 GB free
    EPYC2 = ''.join(f'DIEDISK oth-{i}.scope 20\nDIEDEV oth-{i}.scope 66\nDIEAGE oth-{i}.scope 3600\n' for i in range(8))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch = mock.patch.object(m, 'DAEMON_JOBS', self.tmp.name)
        patch.start()
        self.addCleanup(patch.stop)

    def stub(self, output):
        return mock.patch.object(m.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0, stdout=output))

    def reserved(self, output, dev='66'):
        with self.stub(output):
            return m.die_disk_reserved('epyc2', dev)

    def test_blocked_case_admits(self):
        rows = {'epyc2': dict(disk_gb=121, disk_dev='66')}
        self.assertEqual(self.reserved(self.EPYC2 + 'DIEDISK_DONE\n'), 40)
        with self.stub(self.EPYC2 + 'DIEDISK_DONE\n'):
            self.assertEqual(m.drop_low_disk(rows, True, 20), rows)

    def test_age_boundary_and_round_up(self):
        for age, want in [(0, 60), (899, 60), (900, 15), (86400, 15)]:
            self.assertEqual(self.reserved(f'DIEDISK oth-a.scope 60\nDIEAGE oth-a.scope {age}\nDIEDISK_DONE\n'), want, age)
        self.assertEqual(self.reserved('DIEDISK oth-a.scope 21\nDIEAGE oth-a.scope 900\nDIEDISK_DONE\n'), 6)
        self.assertEqual(self.reserved('DIEDISK oth-a.scope 1\nDIEAGE oth-a.scope 900\nDIEDISK_DONE\n'), 1)

    def test_no_age_or_bad_age_stays_full(self):
        self.assertEqual(self.reserved('DIEDISK oth-a.scope 20\nDIEDISK_DONE\n'), 20)
        for bad in ('-5', 'x', ''):
            self.assertEqual(self.reserved(f'DIEDISK oth-a.scope 20\nDIEAGE oth-a.scope {bad}\nDIEDISK_DONE\n'), 20, bad)

    def test_queued_waiter_stays_full_and_unknown_is_60_then_15(self):
        self.assertEqual(self.reserved('DIEDISK waiter-9 40\nDIEDISK_DONE\n'), 40)
        self.assertEqual(self.reserved('DIEDISK oth-a.scope unknown\nDIEAGE oth-a.scope 3600\nDIEDISK_DONE\n'), 15)

    def test_other_root_still_not_charged(self):
        self.assertEqual(self.reserved('DIEDISK oth-a.scope 20\nDIEDEV oth-a.scope 77\nDIEAGE oth-a.scope 3600\nDIEDISK_DONE\n'), 0)

    def test_young_scopes_still_hold_the_root(self):
        out = ''.join(f'DIEDISK oth-{i}.scope 20\nDIEAGE oth-{i}.scope 60\n' for i in range(8)) + 'DIEDISK_DONE\n'
        said = []
        with self.stub(out):
            self.assertEqual(m.drop_low_disk({'epyc2': dict(disk_gb=121, disk_dev='66')}, True, 20, said.append), {})
        self.assertIn('121 GB free - 160 GB running/queued', said[0])

    def test_real_free_floor(self):
        said = []
        with self.stub('DIEDISK_DONE\n'):
            self.assertEqual(m.drop_low_disk({'h': dict(disk_gb=79)}, True, 20, said.append), {})
            rows = {'h': dict(disk_gb=80)}
            self.assertEqual(m.drop_low_disk(rows, True, 20, said.append), rows)
        self.assertEqual(len(said), 1)
        self.assertIn('79 GB free - 20 GB this job < 60 GB real-free floor', said[0])
        # tile jobs are not die admission: unchanged
        self.assertEqual(m.drop_low_disk({'h': dict(disk_gb=10)}, False, 20), {'h': dict(disk_gb=10)})

    def test_floor_also_holds_when_the_reservation_query_is_skipped(self):
        with mock.patch.object(m, 'die_disk_reserved', side_effect=AssertionError('unexpected query')):
            self.assertEqual(m.drop_low_disk({'h': dict(disk_gb=100)}, True, 60), {})

    def test_real_shell_emits_age_for_scopes_only(self):
        root = Path(self.tmp.name)
        (root / 'systemctl').write_text('#!/bin/sh\ncase "$*" in\n*list-units*) printf "oth-a.scope active\\noth-b.scope active\\n";;\n'
                                        '*Monotonic*oth-a*) echo 5000000000;;\n*Monotonic*oth-b*) echo 0;;\n'
                                        '*oth-a*) echo /a;;\n*oth-b*) echo /b;;\nesac\n')
        (root / 'pgrep').write_text('#!/bin/sh\necho 20\n')
        for tool in ('systemctl', 'pgrep'):
            (root / tool).chmod(0o755)
        for key, pid in (('a', 10), ('b', 11)):
            (root / 'cgroup' / key).mkdir(parents=True)
            (root / 'cgroup' / key / 'cgroup.procs').write_text(str(pid))
        for pid in (10, 11, 20):
            (root / 'proc' / str(pid)).mkdir(parents=True)
            (root / 'proc' / str(pid) / 'environ').write_bytes(b'OT_HEAVY_PRIO=die\0OT_HEAVY_DISK_GB=20\0')
        (root / 'proc' / 'uptime').write_text('8600.25 1.0\n')
        script = m.DIE_DISK_UNITS_SH.replace('/sys/fs/cgroup', str(root / 'cgroup')).replace('/proc/', str(root / 'proc') + '/')
        r = subprocess.run(['bash', '-c', script], env=dict(os.environ, PATH=str(root) + ':' + os.environ['PATH']),
                           text=True, capture_output=True, check=True)
        lines = r.stdout.splitlines()
        self.assertIn('DIEAGE oth-a.scope 3600', lines)
        self.assertFalse([x for x in lines if x.startswith('DIEAGE') and 'oth-a' not in x], lines)
        # a 5 + b 20 + waiter 20
        self.assertEqual(self.reserved(r.stdout, None), 45)


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
