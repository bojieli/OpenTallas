"""Exercise real probe/placement shell semantics with isolated fake host filesystems."""
import base64
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent


def load():
    loader = importlib.machinery.SourceFileLoader('ot_run_locality', str(HERE / 'ot-run'))
    spec = importlib.util.spec_from_loader('ot_run_locality', loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class ProbeLocality(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='otlocality-')
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        self.m = load()
        self.m.SCRATCH_FREE_SH = ''
        self.real_run = subprocess.run
        stub = self.base / 'reconcile.py'
        stub.write_text('import json,sys\nprint(json.dumps(dict(disk_gb=80, probed=sys.argv[2])))\n')
        self.stub = stub
        self.root = '/srv/opentallas-scratch/claude/tok-func-hbm'
        self.nested = self.root + '/sm14/work_smb/obj_base_tools=a54'

    def host_path(self, host, path):
        return self.base / host / path.lstrip('/')

    def probe(self, host, path, spill_ok=False):
        def ssh(args, **kwargs):
            self.assertEqual(args[0], 'ssh')
            self.assertEqual(args[-2], host)
            cmd = args[-1].replace('/usr/local/bin/ot-heavy-reconcile',
                                   shlex.quote(sys.executable) + ' ' + shlex.quote(str(self.stub)))
            cmd = cmd.replace('/srv/', str(self.base / host) + '/srv/')
            return self.real_run(['bash', '-c', cmd], **kwargs)
        with mock.patch.object(self.m.subprocess, 'run', side_effect=ssh):
            return self.m.probe(host, path, spill_ok=spill_ok)[1]

    def test_broad_lane_root_and_sibling_do_not_supply_missing_nested_source(self):
        root = self.host_path('wrong-host', self.root)
        (root / 'att14/src/tools').mkdir(parents=True)
        self.assertIsNone(self.probe('wrong-host', self.nested))
        self.assertFalse(self.host_path('wrong-host', self.nested).exists())

    def test_exact_source_directory_is_probed_instead_of_parent(self):
        path = self.host_path('source-host', self.nested)
        path.mkdir(parents=True)
        row = self.probe('source-host', self.nested)
        self.assertEqual(row['probed'], str(path))

    def test_source_on_twin_root_needs_actual_staged_alias_not_guessed_rebase(self):
        path = self.host_path('source-host', self.nested.replace('scratch/', 'scratch2/', 1))
        path.mkdir(parents=True)
        self.host_path('source-host', self.root).mkdir(parents=True)
        self.assertIsNone(self.probe('source-host', self.nested))
        alias = self.host_path('source-host', self.nested)
        alias.parent.mkdir(parents=True)
        alias.symlink_to(path)
        self.assertIsNotNone(self.probe('source-host', self.nested))

    def test_unique_lane_root_symlink_workaround_still_qualifies(self):
        source = self.base / 'actual-objects'
        source.mkdir()
        alias = self.host_path('gold2', '/srv/opentallas-scratch/claude/tok-hbm-smb-staticready-1021')
        alias.parent.mkdir(parents=True)
        alias.symlink_to(source)
        self.assertIsNotNone(self.probe('gold2', '/srv/opentallas-scratch/claude/tok-hbm-smb-staticready-1021'))

    def test_spill_copy_remains_ineligible_unless_explicitly_allowed(self):
        path = self.host_path('spill-host', self.nested)
        path.mkdir(parents=True)
        (self.host_path('spill-host', self.root) / self.m.SPILL_MARK).write_text('stale spill')
        self.assertIsNone(self.probe('spill-host', self.nested))
        self.assertIsNotNone(self.probe('spill-host', self.nested, spill_ok=True))


class PlacementLocality(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='otplacement-')
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        self.m = load()
        self.roots = [self.base / 'srv/opentallas-scratch', self.base / 'srv/opentallas-scratch2']
        for root in self.roots:
            (root / 'claude').mkdir(parents=True)
        self.lane = self.roots[0] / 'claude/known-source'
        self.cwd = self.lane / 'src/tools'
        self.cwd.mkdir(parents=True)
        (self.cwd / 'source.py').write_text('source unchanged')

    def place(self, cwd, command):
        code = self.m.SCRATCH_PLACE_PY.replace('/srv/opentallas-scratch', str(self.base) + '/srv/opentallas-scratch')
        real_stat = os.stat
        def stat(path, *args, **kwargs):
            p = pathlib.Path(path)
            p = p.parent if p.name == 'claude' else p        # v13 measures <root>/claude
            if p in self.roots:
                return types.SimpleNamespace(st_dev=1 + self.roots.index(p), st_mode=0o40755)
            return real_stat(path, *args, **kwargs)
        def statvfs(path):
            p = pathlib.Path(path)
            p = p.parent if p.name == 'claude' else p
            return types.SimpleNamespace(f_bavail=(100 if p == self.roots[0] else 800) << 30,
                                         f_frsize=1)
        argv = ['scratch-place', str(cwd), base64.b64encode(json.dumps(command).encode()).decode()]
        with mock.patch.object(os, 'stat', side_effect=stat), mock.patch.object(os, 'statvfs', side_effect=statvfs), \
                mock.patch.object(sys, 'argv', argv), contextlib.redirect_stderr(io.StringIO()):
            exec(compile(code, 'scratch-place', 'exec'), {})

    def test_new_explicit_output_run_still_balances_without_moving_source(self):
        run = self.lane / 'fresh-run'
        inode = self.cwd.stat().st_ino
        self.place(self.cwd, ['bash', '-c', 'mkdir -p ' + str(run / 'out')])
        self.assertTrue(run.is_symlink())
        self.assertEqual(os.readlink(run), str(self.roots[1] / 'claude/known-source/fresh-run'))
        self.assertEqual(self.cwd.stat().st_ino, inode)
        self.assertEqual((self.cwd / 'source.py').read_text(), 'source unchanged')

    def test_existing_run_and_objects_stay_in_place(self):
        run = self.lane / 'existing-run'
        run.mkdir()
        (run / 'checkpoint').write_text('preserve')
        self.place(self.cwd, ['bash', '-c', 'mkdir -p ' + str(run / 'out')])
        self.assertFalse(run.is_symlink())
        self.assertEqual((run / 'checkpoint').read_text(), 'preserve')

    def test_output_helper_never_fabricates_missing_input_workdir(self):
        missing = self.lane / 'sm14/missing-objects'
        self.place(missing, ['/bin/true'])
        self.assertFalse(missing.exists())

    def test_runtime_guard_refuses_disappeared_workdir_before_output_placement(self):
        missing = self.base / 'missing input'
        marker = self.base / 'placement-ran'
        captured = []
        class Captured(Exception):
            pass
        def popen(args, **kwargs):
            captured.append(args[-1])
            raise Captured()
        with mock.patch.object(self.m, 'SCRATCH_ENV', ''), \
                mock.patch.object(self.m, 'scratch_place_sh', return_value='touch ' + shlex.quote(str(marker)) + '; '), \
                mock.patch.object(self.m.subprocess, 'Popen', side_effect=popen):
            with self.assertRaises(Captured):
                self.m.run('source-host', 8, ['/bin/true'], d=str(missing))
        result = subprocess.run(['bash', '-c', captured[0]], capture_output=True, text=True)
        self.assertEqual(result.returncode, 96)
        self.assertIn('OT_RUN_NOCD', result.stderr)
        self.assertFalse(marker.exists())

    def test_scratch_capacity_selection_still_uses_available_twin_root(self):
        out = 'OT_SCRATCH_FREE /srv/opentallas-scratch 100\nOT_SCRATCH_FREE /srv/opentallas-scratch2 800\n'
        row = self.m.scratch_disk({'disk_gb': 100}, '/srv/opentallas-scratch/claude/known-source/src/tools', out)
        self.assertEqual(row['disk_gb'], 800)
        self.assertEqual(row['disk_own_gb'], 100)


if __name__ == '__main__':
    unittest.main()
