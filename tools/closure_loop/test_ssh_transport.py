import concurrent.futures
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import ssh_transport as T
import closure_loop as C


class TransportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, CL_STATE=self.tmp.name)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.root = T._directory()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))

    def test_local_and_localhost_never_contact_ssh(self):
        with patch.object(T, '_ensure_master', side_effect=AssertionError('SSH used')):
            for host in ['local', 'localhost']:
                self.assertEqual(C.ssh(host, 'printf live').stdout, 'live')
                self.assertEqual(C.ssh(host, 'cat', input='payload').stdout, 'payload')

    def test_concurrent_threads_single_master_and_eight_sessions(self):
        active = peak = starts = 0
        live = False
        lock = threading.Lock()
        def run(cmd, **kwargs):
            nonlocal starts, live
            if '-O' in cmd:
                return subprocess.CompletedProcess(cmd, 0 if live else 255, b'', b'')
            self.assertIn('ControlMaster=yes', cmd)
            starts += 1
            time.sleep(.01)
            live = True
            return subprocess.CompletedProcess(cmd, 0, b'', b'')
        def task(n):
            nonlocal active, peak
            with T.command('test-host') as cmd:
                self.assertIn('ProxyCommand=false', cmd)
                with lock:
                    active += 1
                    peak = max(peak, active)
                time.sleep(.03)
                with lock:
                    active -= 1
        with patch.object(T.subprocess, 'run', side_effect=run):
            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
                list(pool.map(task, range(40)))
        self.assertEqual(starts, 1)
        self.assertEqual(peak, 8)
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)

    def test_failure_releases_channel_and_reconnects_next_operation(self):
        with patch.object(T, '_ensure_master', side_effect=RuntimeError('ssh: failed')):
            for _ in range(12):
                with self.assertRaises(RuntimeError):
                    with T.command('host'):
                        self.fail('must not execute')
        with patch.object(T, '_ensure_master', return_value=['ssh', 'host']):
            with T.command('host'):
                pass

    def test_remote_command_failure_is_never_replayed(self):
        with patch.object(C, 'transport_command', wraps=T.command), patch.object(T, '_ensure_master', return_value=['ssh', 'host']), patch.object(C, 'sh', return_value=subprocess.CompletedProcess([], 255, '', 'lost')) as call:
            self.assertEqual(C.ssh('host', 'side_effect').returncode, 255)
            self.assertEqual(call.call_count, 1)

    def test_external_process_leases_block_ninth_channel(self):
        key = hashlib.sha256(b'host').hexdigest()[:20]
        leases = [(self.root / f'{key}.{n}.lease').open('a') for n in range(8)]
        for lease in leases:
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        entered = threading.Event()
        def task():
            with T.command('host'):
                entered.set()
        try:
            with patch.object(T, '_ensure_master', return_value=['ssh', 'host']):
                worker = threading.Thread(target=task)
                worker.start()
                self.assertFalse(entered.wait(.1))
                leases[0].close()
                self.assertTrue(entered.wait(2))
                worker.join(2)
                self.assertFalse(worker.is_alive())
        finally:
            for lease in leases:
                lease.close()

    def test_private_directory_rejects_shared_permissions(self):
        self.root.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, 'unsafe'):
            T._directory()

    def test_stale_socket_reconnect_is_serialized(self):
        seen = []
        def run(cmd, **kwargs):
            seen.append(cmd)
            return subprocess.CompletedProcess(cmd, 255 if '-O' in cmd else 0, b'', b'')
        with patch.object(T.subprocess, 'run', side_effect=run):
            with T.command('host') as cmd:
                self.assertIn('ControlMaster=auto', cmd)
        self.assertEqual(len(seen), 2)
        self.assertIn('-O', seen[0])
        self.assertIn('-N', seen[1])

if __name__ == '__main__':
    unittest.main()
