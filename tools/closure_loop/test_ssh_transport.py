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

    def test_explicit_refusal_retries_once_with_lease_and_payload(self):
        from contextlib import contextmanager
        refused = subprocess.CompletedProcess([], 255, '',
            'mux_client_request_session: session request failed: Session open refused by peer\n')
        for payload in (None, 'stdin payload'):
            held = []
            @contextmanager
            def lease(host):
                held.append(True)
                try:
                    yield ['ssh', '-o', 'ControlMaster=auto', host]
                finally:
                    held.clear()
            calls = []
            def run(cmd, **kwargs):
                self.assertTrue(held)
                calls.append((cmd, kwargs))
                return refused if len(calls) == 1 else subprocess.CompletedProcess(cmd, 0, 'done', '')
            with patch.object(C, 'transport_command', side_effect=lease), patch.object(C, 'sh', side_effect=run):
                self.assertEqual(C.ssh('host', 'side_effect', input=payload, timeout=77, check=True).stdout, 'done')
            self.assertEqual(len(calls), 2)
            self.assertIn('ControlMaster=no', calls[1][0])
            self.assertIn('ControlPath=none', calls[1][0])
            self.assertNotIn('ProxyCommand=false', calls[1][0])
            self.assertEqual(calls[0][1]['input'], calls[1][1]['input'])
            self.assertEqual(calls[1][1]['timeout'], 77)
            self.assertFalse(held)

    def test_fallback_failure_is_not_retried(self):
        refused = subprocess.CompletedProcess([], 255, '',
            'mux_client_request_session: session request failed: Session open refused by peer')
        with patch.object(T, '_ensure_master', return_value=['ssh', 'host']), patch.object(C, 'sh', return_value=refused) as call:
            self.assertEqual(C.ssh('host', 'side_effect').returncode, 255)
            self.assertEqual(call.call_count, 2)

    def test_timeout_and_nonmux_errors_never_replay(self):
        refusal = 'mux_client_request_session: session request failed: Session open refused by peer'
        cases = [subprocess.TimeoutExpired('ssh', 77), OSError('unavailable'),
                 subprocess.CompletedProcess([], 255, '', 'Connection timed out'),
                 subprocess.CompletedProcess([], 255, '', 'Connection reset by peer'),
                 subprocess.CompletedProcess([], 255, 'remote began', refusal),
                 subprocess.CompletedProcess([], 1, '', refusal),
                 subprocess.CompletedProcess([], 255, '', refusal + '\nConnection closed')]
        for result in cases:
            with self.subTest(result=result):
                with patch.object(T, '_ensure_master', return_value=['ssh', 'host']), patch.object(C, 'sh') as call:
                    if isinstance(result, Exception):
                        call.side_effect = result
                        with self.assertRaises(type(result)):
                            C.ssh('host', 'side_effect')
                    else:
                        call.return_value = result
                        self.assertIs(C.ssh('host', 'side_effect'), result)
                    self.assertEqual(call.call_count, 1)

    def test_checked_fallback_preserves_remote_error(self):
        refused = subprocess.CompletedProcess([], 255, '',
            'mux_client_request_session: session request failed: Session open refused by peer')
        failed = subprocess.CompletedProcess([], 17, '', 'remote command failed')
        with patch.object(T, '_ensure_master', return_value=['ssh', 'host']), patch.object(C, 'sh', side_effect=[refused, failed]) as call:
            with self.assertRaisesRegex(RuntimeError, 'rc=17'):
                C.ssh('host', 'side_effect', check=True)
            self.assertEqual(call.call_count, 2)

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

    def test_socket_epoch_preserves_old_master_socket_and_host_leases(self):
        key = hashlib.sha256(b'host').hexdigest()[:20]
        old_socket = self.root / (key + '.sock')
        old_socket.write_text('old transfer still owns this generation')
        seen = []
        def run(cmd, **kwargs):
            seen.append(cmd)
            return subprocess.CompletedProcess(cmd, 255 if '-O' in cmd else 0, b'', b'')
        with patch.dict(os.environ, CL_SSH_SOCKET_EPOCH='runtime-41cee'), patch.object(T.subprocess, 'run', side_effect=run):
            with T.command('host') as cmd:
                control = next(x for x in cmd if x.startswith('ControlPath='))
                self.assertNotEqual(control, 'ControlPath=' + str(old_socket))
                self.assertIn(str(self.root), control)
                self.assertTrue((self.root / (key + '.0.lease')).exists())
                self.assertIn((str(self.root), 'host'), T._SEMAPHORES)
        self.assertEqual(old_socket.read_text(), 'old transfer still owns this generation')
        self.assertEqual(len(seen), 2)
        self.assertFalse(any('exit' in cmd or 'stop' in cmd for cmd in seen))

    def test_new_epoch_cannot_bypass_old_generation_channel_leases(self):
        key = hashlib.sha256(b'host').hexdigest()[:20]
        leases = [(self.root / f'{key}.{n}.lease').open('a') for n in range(T.CHANNELS)]
        for lease in leases:
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        entered = threading.Event()
        def task():
            with T.command('host'):
                entered.set()
        try:
            with patch.dict(os.environ, CL_SSH_SOCKET_EPOCH='new'), patch.object(T, '_ensure_master', return_value=['ssh', 'host']):
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

if __name__ == '__main__':
    unittest.main()
