"""Control-plane tests only: no SSH, provider requests, cancellations, or EDA jobs."""
import datetime
import hashlib
import sys
import fcntl
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import types
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class DeadlineTests(unittest.TestCase):
    def setUp(self):
        self.m = module('epyc6_retire')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.m.STATE = self.tmp.name
        self.m.LOG = str(pathlib.Path(self.tmp.name) / 'watch.log')
        self.st = {'hostname': 'ot-epyc6', 'units': [], 'docker': [], 'procs': [], 'stale': []}
        self.patches = [
            mock.patch.object(self.m, 'deadline_due', return_value=True),
            mock.patch.object(self.m, 'verify_identity', return_value=(True, 'exact identity')),
            mock.patch.object(self.m, 'host_py', return_value=self.st),
            mock.patch.object(self.m, 'daemon_jobs', return_value={'job1': {'status': 'RUNNING'}}),
            mock.patch.object(self.m, 'work_dirs', return_value={'/srv/opentallas-scratch/claude/live-job'}),
            mock.patch.object(self.m, 'deadline_kill', side_effect=lambda jobs: self.mocks[3].configure_mock(return_value={})),
            mock.patch.object(self.m, 'terminate'),
        ]
        self.mocks = [p.start() for p in self.patches]
        for p in self.patches:
            self.addCleanup(p.stop)

    def test_before_deadline_and_dry_run_never_cancel(self):
        self.mocks[0].return_value = False
        self.assertFalse(self.m.enforce_deadline())
        self.mocks[0].return_value = True
        self.assertFalse(self.m.enforce_deadline(dry_run=True))
        self.mocks[1].assert_not_called()
        self.mocks[5].assert_not_called()

    def test_due_while_archive_pass_holds_lock_is_independent_and_idempotent(self):
        with open(pathlib.Path(self.tmp.name) / 'watch.lock', 'a') as archive_lock:
            fcntl.flock(archive_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertTrue(self.m.enforce_deadline())
        self.assertTrue(self.m.enforce_deadline())
        self.mocks[5].assert_called_once()
        self.mocks[6].assert_not_called()
        snap = json.loads((pathlib.Path(self.tmp.name) / 'deadline_partial_snapshot.json').read_text())
        self.assertEqual(snap['observed_dirs'], ['/srv/opentallas-scratch/claude/live-job'])
        done = json.loads((pathlib.Path(self.tmp.name) / 'deadline_complete.json').read_text())
        self.assertFalse(done['delete_attempted'])

    def test_concurrent_deadline_enforcer_does_not_duplicate_cancel(self):
        with open(pathlib.Path(self.tmp.name) / 'deadline.lock', 'a') as lk:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertFalse(self.m.enforce_deadline())
        self.mocks[5].assert_not_called()

    def test_wrong_identity_and_unknown_docker_refuse_cancellation(self):
        self.mocks[1].return_value = (False, 'wrong server')
        self.assertFalse(self.m.enforce_deadline())
        self.mocks[1].return_value = (True, 'exact identity')
        self.st['docker_error'] = 'inventory unavailable'
        self.assertFalse(self.m.enforce_deadline())
        self.mocks[5].assert_not_called()
        self.mocks[6].assert_not_called()

    def test_incomplete_cancellation_retries_without_complete_marker(self):
        self.mocks[5].side_effect = [RuntimeError('temporary controller error'), None]
        self.mocks[3].return_value = {}
        with self.assertRaises(RuntimeError):
            self.m.enforce_deadline()
        self.assertFalse((pathlib.Path(self.tmp.name) / 'deadline_complete.json').exists())
        self.assertTrue(self.m.enforce_deadline())

    def test_remaining_job_prevents_complete_receipt(self):
        after = dict(self.st, units=[{'unit': 'still-live'}])
        self.mocks[2].side_effect = [self.st, after]
        self.assertFalse(self.m.enforce_deadline())
        self.assertFalse((pathlib.Path(self.tmp.name) / 'deadline_complete.json').exists())

    def test_c3_merges_deadline_snapshot_roots_before_final_verification(self):
        root = '/srv/opentallas-scratch/claude/late-job'
        self.m.jsave(self.tmp.name + '/deadline_partial_snapshot.json', {'observed_dirs': [root]})
        args = types.SimpleNamespace(no_copy=True)
        with mock.patch.object(self.m, 'pending_roots', return_value=[]), \
                mock.patch.object(self.m, 'resolve', return_value={}) as resolve:
            self.m.check_pending(False, self.st, args)
        self.assertIn(root, resolve.call_args.args[0])

    def test_deadline_only_main_bypasses_archive_pass(self):
        with mock.patch('sys.argv', ['epyc6_retire.py', '--deadline-only']), \
                mock.patch.object(self.m, 'enforce_deadline') as enforce, \
                mock.patch.object(self.m, 'check_pending') as copy:
            self.m.main()
        enforce.assert_called_once_with(dry_run=False)
        copy.assert_not_called()


class PollAndClockTests(unittest.TestCase):
    def test_clock_transition_at_exact_owner_deadline(self):
        m = module('epyc6_retire')
        real_datetime = datetime.datetime
        at = m.DEADLINE
        class Clock(real_datetime):
            value = at - datetime.timedelta(seconds=1)
            @classmethod
            def now(cls):
                return cls.value
        with mock.patch.object(m.dt, 'datetime', Clock):
            self.assertFalse(m.deadline_due())
            Clock.value = at
            self.assertTrue(m.deadline_due())

    def test_running_copy_checks_deadline_without_stopping_transport(self):
        m = module('epyc6_retire')
        proc = mock.Mock(returncode=0)
        proc.communicate.side_effect = [subprocess.TimeoutExpired(['ssh'], 15), ('copied', '')]
        with mock.patch.object(m.subprocess, 'Popen', return_value=proc), \
                mock.patch.object(m, 'deadline_checkpoint') as checkpoint:
            result = m.run_copy_poll(['ssh', 'exact-host'], env={}, timeout=3600)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, 'copied')
        self.assertEqual(checkpoint.call_count, 2)
        proc.kill.assert_not_called()

    def test_archive_rsync_excluded_but_active_build_is_visible(self):
        m = module('remote_host_state')
        self.assertIsNotNone(m.SKIP_ARGS.search('rsync -a /source/ ubuntu@host:/archive/epyc6-retire-1021/source/'))
        self.assertIsNone(m.SKIP_ARGS.search('openroad /srv/opentallas-scratch/claude/live-job/run.tcl'))


class FinalArchiveHashTests(unittest.TestCase):
    def verify(self, root, items):
        result = subprocess.run([sys.executable, str(HERE / 'remote_verify.py'), 'list'],
                                input=json.dumps({str(root): items}), capture_output=True, text=True, check=True)
        return json.loads(result.stdout)[str(root)]

    def test_same_size_corruption_cannot_approve_delete(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / 'evidence.log').write_bytes(b'abce')
            result = self.verify(root, [['evidence.log', 4, hashlib.sha256(b'abcd').hexdigest()]])
            self.assertFalse(result['ok'])
            self.assertEqual(result['size_mismatch'], 0)
            self.assertEqual(result['hash_mismatch'], 1)

    def test_symlink_identity_and_regular_hash_match(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / 'evidence.log').write_bytes(b'abcd')
            (root / 'link').symlink_to('evidence.log')
            items = [['evidence.log', 4, hashlib.sha256(b'abcd').hexdigest()],
                     ['link', 'L', hashlib.sha256(b'evidence.log').hexdigest()]]
            self.assertTrue(self.verify(root, items)['ok'])
            items[1][2] = hashlib.sha256(b'wrong-target').hexdigest()
            self.assertFalse(self.verify(root, items)['ok'])

    def test_final_source_walk_emits_hashes_for_actual_preserved_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / 'evidence.log').write_bytes(b'abcd')
            (root / 'link').symlink_to('evidence.log')
            result = subprocess.run([sys.executable, str(HERE / 'remote_walk.py')],
                                    input=json.dumps({'roots': [str(root)], 'hash': True}),
                                    capture_output=True, text=True, check=True)
            record = json.loads(result.stdout)[str(root)]
            manifest = pathlib.Path('/tmp/e6r/lists') / (record['id'] + '.lst')
            self.addCleanup(manifest.unlink, missing_ok=True)
            lines = [line.split('\t') for line in manifest.read_text().splitlines()]
            self.assertTrue(all(len(row) == 3 for row in lines))
            self.assertEqual(next(row[2] for row in lines if row[0] == 'evidence.log'), hashlib.sha256(b'abcd').hexdigest())
            self.assertEqual(next(row[2] for row in lines if row[0] == 'link'), hashlib.sha256(b'evidence.log').hexdigest())


if __name__ == '__main__':
    unittest.main()
